"""
The agent loop.

Responsibilities (and only these):
- Dispatch tool calls
- Manage the message history
- Enforce max iterations
- Coerce the final model output into an AgentDecision

Things the loop does NOT do:
- Policy decisions (gates do that)
- Persistence (orchestrator does that)
- Retries on transient failures (orchestrator does that)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from src.agent.schemas import AgentDecision
from src.agent.tools_registry import TOOLS, get_tool, to_openai_tools

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"


class AgentLoopError(Exception):
    """Raised when the loop cannot produce a valid decision."""


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text()


def _dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    """Call a registered tool. Returns JSON string for the model to read."""
    spec = get_tool(name)
    if spec is None:
        return json.dumps({"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": name}})

    try:
        parsed_input = spec.input_schema.model_validate(arguments)
    except ValidationError as e:
        return json.dumps(
            {"ok": False, "error": {"code": "BAD_INPUT", "message": str(e), "retryable": False}}
        )

    try:
        result = spec.handler(parsed_input)
    except NotImplementedError:
        return json.dumps(
            {
                "ok": False,
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": f"Tool '{name}' is a stub. Implement it in src/tools/.",
                    "retryable": False,
                },
            }
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Tool %s raised unexpectedly", name)
        return json.dumps(
            {
                "ok": False,
                "error": {"code": "TOOL_EXCEPTION", "message": str(e), "retryable": True},
            }
        )

    return result.model_dump_json()


def run_agent(invoice_id: str, *, client: OpenAI | None = None, model: str | None = None) -> AgentDecision:
    """
    Run the agent for one invoice. Returns a validated AgentDecision.

    The agent is told the invoice_id and must call extract_invoice itself —
    we don't pre-extract because we want the loop to be observable end-to-end.
    """
    client = client or OpenAI()
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _load_system_prompt()},
        {
            "role": "user",
            "content": (
                f"Process invoice with id '{invoice_id}'. Call extract_invoice first, "
                f"then perform your standard checks, then return your AgentDecision."
            ),
        },
    ]

    tools_for_api = to_openai_tools()

    final_decision: AgentDecision | None = None

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d", iteration + 1)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools_for_api,
            tool_choice="auto",
            # When we want structured output on the final turn:
            response_format={"type": "json_object"} if iteration >= 2 else None,
        )

        message = response.choices[0].message
        messages.append(message.model_dump(exclude_unset=True))

        # If the model called tools, dispatch them and continue.
        if message.tool_calls:
            for call in message.tool_calls:
                args = json.loads(call.function.arguments)
                logger.info("→ Tool: %s args=%s", call.function.name, args)
                result_json = _dispatch_tool(call.function.name, args)
                logger.info("← Result: %s", result_json[:200])
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result_json,
                    }
                )
            continue

        # No tool calls — model is producing its final answer.
        content = message.content or ""
        try:
            final_decision = AgentDecision.model_validate_json(content)
            break
        except ValidationError as e:
            # Push it back with the validation error and let it correct.
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Your last response was not valid AgentDecision JSON: {e}\n"
                        f"Return ONLY a JSON object matching the AgentDecision schema."
                    ),
                }
            )
            continue

    if final_decision is None:
        raise AgentLoopError(
            f"Agent did not produce a valid decision within {MAX_ITERATIONS} iterations"
        )

    return final_decision
