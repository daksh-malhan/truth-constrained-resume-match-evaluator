"""Run the Resume Coach eval benchmark against the real agent and report measured results.

Usage (from backend/):
    LLM_PROVIDER=ollama EMBEDDING_PROVIDER=ollama OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest \
    OLLAMA_AGENT_MODEL=qwen2.5:7b-instruct \
    python -m app.agent.eval.run_eval --out app/agent/eval/results.json

All numbers are measured from live runs; nothing is hardcoded.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
from datetime import datetime, timezone

from ... import database
from ..model import agent_model_name, agent_provider
from .cases import BENCHMARK_CASES
from .harness import run_eval, to_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Resume Coach eval benchmark.")
    parser.add_argument("--out", default="app/agent/eval/results.json", help="Where to write the JSON results.")
    parser.add_argument("--max-iterations", type=int, default=6, help="Per-case agent iteration cap.")
    args = parser.parse_args()

    database.init_db()
    report = run_eval(BENCHMARK_CASES, max_iterations=args.max_iterations)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": agent_provider(),
        "model": agent_model_name(),
        "max_iterations": args.max_iterations,
        "aggregate": report.aggregate,
        "results": [dataclasses.asdict(r) for r in report.results],
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"\nResume Coach eval — provider={agent_provider()} model={agent_model_name()}\n")
    print(to_markdown(report))
    print(f"\nWrote JSON results to {args.out}")


if __name__ == "__main__":
    main()
