"""
Demo: run the agent on a single invoice and show the full decision + routing.

Usage:
    python -m src.agent.demo            # uses INV-001 by default
    python -m src.agent.demo INV-002    # specify invoice
"""

from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

from src.agent.loop import run_agent
from src.gates.routing import route

console = Console()


def main() -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    invoice_id = sys.argv[1] if len(sys.argv) > 1 else "INV-001"
    console.print(Panel.fit(f"[bold cyan]Processing invoice: {invoice_id}[/bold cyan]"))

    try:
        decision = run_agent(invoice_id)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Agent failed: {e}[/red]")
        return 1

    console.print(Panel(Pretty(decision.model_dump()), title="Agent Decision"))

    routing = route(decision)
    console.print(Panel(Pretty(routing.model_dump(exclude={"decision"})), title="Final Routing"))

    console.print(f"\n[bold green]→ Route to: {routing.route_to.value}[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
