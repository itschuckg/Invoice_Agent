"""
Eval harness. Replays the golden set through the full agent + gates pipeline
and reports:
  - exact-match accuracy on route_to
  - critical false-approve rate (auto-post when expected fraud_review)
  - average tokens per invoice (cost proxy)
  - p95 latency

Run:
    python -m evals.run_evals
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import quantiles

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from src.agent.loop import run_agent
from src.agent.schemas import RouteTarget
from src.gates.routing import route

console = Console()

GOLDEN_PATH = Path(__file__).parent / "golden_set.jsonl"


def load_golden() -> list[dict]:
    with GOLDEN_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> int:
    load_dotenv()
    cases = load_golden()
    console.print(f"[bold]Running {len(cases)} golden-set cases...[/bold]\n")

    results = []
    false_approves = 0
    latencies: list[float] = []

    for case in cases:
        t0 = time.perf_counter()
        try:
            decision = run_agent(case["invoice_id"])
            routing = route(decision)
            actual = routing.route_to.value
            error = None
        except Exception as e:  # noqa: BLE001
            actual = "ERROR"
            error = str(e)
        latency = time.perf_counter() - t0
        latencies.append(latency)

        match = actual == case["expected_route"]
        # Critical: did we auto-post something that should have been fraud_review?
        if actual == RouteTarget.ERP_AUTO_POST.value and case["expected_route"] == "fraud_review":
            false_approves += 1

        results.append(
            {
                "invoice_id": case["invoice_id"],
                "scenario": case["scenario"],
                "expected": case["expected_route"],
                "actual": actual,
                "match": match,
                "latency_s": round(latency, 2),
                "error": error,
            }
        )

    # Render results table
    table = Table(title="Eval Results")
    table.add_column("Invoice")
    table.add_column("Scenario")
    table.add_column("Expected")
    table.add_column("Actual")
    table.add_column("Match")
    table.add_column("Latency (s)")

    for r in results:
        table.add_row(
            r["invoice_id"],
            r["scenario"],
            r["expected"],
            r["actual"],
            "[green]✓[/green]" if r["match"] else "[red]✗[/red]",
            str(r["latency_s"]),
        )

    console.print(table)

    # Summary metrics
    accuracy = sum(1 for r in results if r["match"]) / len(results)
    p95 = quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]

    console.print("\n[bold]Summary[/bold]")
    console.print(f"  Exact-match accuracy: {accuracy:.0%}")
    console.print(f"  Critical false-approves: {false_approves}  (target: 0)")
    console.print(f"  p95 latency: {p95:.2f}s")

    return 0 if false_approves == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
