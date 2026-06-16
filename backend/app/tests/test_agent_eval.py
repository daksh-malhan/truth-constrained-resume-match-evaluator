from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app import database
from app.agent.context import clear_context_cache
from app.agent.eval.harness import EvalCase, run_eval, tool_call_recall, to_markdown


def test_tool_call_recall_counts_covered_expected_tools():
    assert tool_call_recall({"score_resume", "find_gaps"}, ["score_resume", "find_gaps", "check_truth"]) == 1.0
    assert tool_call_recall({"score_resume", "find_gaps"}, ["score_resume"]) == 0.5
    assert tool_call_recall(set(), ["score_resume"]) == 1.0  # nothing required -> trivially covered


class _ScoreThenFinish(BaseChatModel):
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "score-then-finish"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        idx = self.calls
        self.calls += 1
        if idx == 0:
            msg = AIMessage(content="", tool_calls=[{"name": "score_resume", "args": {}, "id": f"c{idx}", "type": "tool_call"}])
        else:
            msg = AIMessage(content="Done coaching.")
        return ChatResult(generations=[ChatGeneration(message=msg)])


def test_run_eval_produces_real_measured_metrics():
    database.init_db()
    clear_context_cache()
    cases = [
        EvalCase(
            name="python_intern",
            resume="SKILLS\nPython, FastAPI, Docker",
            job_description="Required: Python and REST API. Preferred: Kubernetes.",
            target_role="Backend Intern",
            expected_tools={"score_resume"},
        )
    ]
    report = run_eval(cases, chat_model=_ScoreThenFinish(), max_iterations=4)

    assert len(report.results) == 1
    case = report.results[0]
    assert case.called_tools == ["score_resume"]
    assert case.tool_call_recall == 1.0
    assert case.iterations == 2
    assert case.latency_ms >= 0  # measured from a real run, not hardcoded
    # Aggregate numbers are computed from the runs.
    assert report.aggregate["cases"] == 1
    assert report.aggregate["mean_tool_call_recall"] == 1.0
    assert "mean_latency_ms" in report.aggregate
    assert isinstance(to_markdown(report), str) and "python_intern" in to_markdown(report)
