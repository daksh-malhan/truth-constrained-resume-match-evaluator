from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from langchain_core.language_models.chat_models import BaseChatModel

from .. import context as agent_context
from ..loop import run_coach
from ..schemas import CoachRequest


@dataclass
class EvalCase:
    name: str
    resume: str
    job_description: str
    target_role: str
    expected_tools: Set[str] = field(default_factory=set)


@dataclass
class EvalCaseResult:
    name: str
    expected_tools: List[str]
    called_tools: List[str]
    tool_call_recall: float
    fully_covered: bool
    iterations: int
    latency_ms: int
    stop_reason: str
    initial_score: Optional[float]
    flagged_rewrites: int


@dataclass
class EvalReport:
    results: List[EvalCaseResult]
    aggregate: Dict[str, float]


def tool_call_recall(expected: Set[str], called: List[str]) -> float:
    """Fraction of expected tools the agent actually called (1.0 if none expected)."""
    if not expected:
        return 1.0
    called_set = set(called)
    return round(len(expected & called_set) / len(expected), 4)


def run_eval(
    cases: List[EvalCase],
    *,
    chat_model: Optional[BaseChatModel] = None,
    max_iterations: int = 6,
) -> EvalReport:
    """Run every case through the real agent loop and measure behavior + latency."""
    results: List[EvalCaseResult] = []
    for case in cases:
        agent_context.clear_context_cache()
        request = CoachRequest(resume=case.resume, job_description=case.job_description, target_role=case.target_role)
        started = time.perf_counter()
        response = run_coach(request, chat_model=chat_model, max_iterations=max_iterations)
        latency_ms = int((time.perf_counter() - started) * 1000)

        called = [t.tool for t in response.tool_call_trace]
        recall = tool_call_recall(case.expected_tools, called)
        results.append(
            EvalCaseResult(
                name=case.name,
                expected_tools=sorted(case.expected_tools),
                called_tools=called,
                tool_call_recall=recall,
                fully_covered=recall == 1.0,
                iterations=response.iterations,
                latency_ms=latency_ms,
                stop_reason=response.stop_reason,
                initial_score=response.initial_score,
                flagged_rewrites=sum(1 for r in response.bullet_rewrites if r.flagged),
            )
        )

    return EvalReport(results=results, aggregate=_aggregate(results))


def _aggregate(results: List[EvalCaseResult]) -> Dict[str, float]:
    if not results:
        return {"cases": 0}
    recalls = [r.tool_call_recall for r in results]
    iters = [r.iterations for r in results]
    latencies = [r.latency_ms for r in results]
    return {
        "cases": len(results),
        "mean_tool_call_recall": round(statistics.mean(recalls), 4),
        "fully_covered_cases": sum(1 for r in results if r.fully_covered),
        "mean_iterations": round(statistics.mean(iters), 2),
        "mean_latency_ms": int(statistics.mean(latencies)),
        "p50_latency_ms": int(statistics.median(latencies)),
        "max_latency_ms": max(latencies),
    }


def to_markdown(report: EvalReport) -> str:
    lines = [
        "| Case | Expected tools | Called tools | Recall | Iters | Latency (ms) | Stop |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report.results:
        lines.append(
            f"| {r.name} | {', '.join(r.expected_tools) or '-'} | {', '.join(r.called_tools) or '-'} | "
            f"{r.tool_call_recall:.2f} | {r.iterations} | {r.latency_ms} | {r.stop_reason} |"
        )
    agg = report.aggregate
    lines.append("")
    lines.append(
        f"**Aggregate** — cases: {agg.get('cases')}, "
        f"mean tool-call recall: {agg.get('mean_tool_call_recall')}, "
        f"fully covered: {agg.get('fully_covered_cases')}/{agg.get('cases')}, "
        f"mean iters: {agg.get('mean_iterations')}, "
        f"mean latency: {agg.get('mean_latency_ms')} ms (p50 {agg.get('p50_latency_ms')}, max {agg.get('max_latency_ms')})."
    )
    return "\n".join(lines)
