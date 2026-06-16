from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app import database
from app.agent.context import clear_context_cache
from app.agent.loop import run_coach
from app.agent.schemas import CoachRequest


RESUME = """PROJECTS
Built a FastAPI service in Python with pytest coverage and a SQLite backend.

SKILLS
Python, FastAPI, Docker, SQL, Git
"""

JOB = """Backend Engineer Intern
Required: strong Python and REST API development.
Preferred: Kubernetes orchestration and AWS deployment.
"""


class ScriptedModel(BaseChatModel):
    """Deterministic chat model that replays a fixed list of AIMessages."""

    responses: List[AIMessage] = []
    loop_last: bool = False
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):  # noqa: D401 - fake binding
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        idx = self.calls
        self.calls += 1
        if idx < len(self.responses):
            template = self.responses[idx]
        elif self.loop_last and self.responses:
            template = self.responses[-1]
        else:
            template = AIMessage(content="done")
        # Return a fresh message instance each call (unique id) so add_messages appends
        # rather than merging, exactly like a real chat model.
        if template.tool_calls:
            msg = AIMessage(
                content=template.content,
                tool_calls=[{**tc, "id": f"{tc['id']}_{idx}"} for tc in template.tool_calls],
            )
        else:
            msg = AIMessage(content=template.content)
        return ChatResult(generations=[ChatGeneration(message=msg)])


def _request():
    database.init_db()
    clear_context_cache()
    return CoachRequest(resume=RESUME, job_description=JOB, target_role="Backend Engineer Intern")


def _tool_call(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def test_loop_executes_tools_records_trace_and_summarizes():
    model = ScriptedModel(
        responses=[
            _tool_call("score_resume", {}, "c1"),
            _tool_call("find_gaps", {}, "c2"),
            AIMessage(content="Here is your coaching summary."),
        ]
    )
    response = run_coach(_request(), chat_model=model, max_iterations=6)

    tools_called = [t.tool for t in response.tool_call_trace]
    assert tools_called == ["score_resume", "find_gaps"]
    assert all(t.duration_ms >= 0 for t in response.tool_call_trace)
    assert "coaching summary" in response.final_summary.lower()
    assert response.iterations == 3
    assert response.stop_reason == "completed"
    # Deterministic enrichment is always present regardless of tool choice.
    assert response.initial_score is not None
    assert response.gaps is not None


def test_loop_respects_max_iteration_cap():
    # Model never stops asking for a tool.
    model = ScriptedModel(responses=[_tool_call("score_resume", {}, "c")], loop_last=True)
    response = run_coach(_request(), chat_model=model, max_iterations=3)
    assert response.iterations == 3
    assert response.stop_reason == "max_iterations"


def test_loop_flags_unsafe_rewrite_in_response():
    model = ScriptedModel(
        responses=[
            _tool_call("rewrite_bullet", {"bullet": "Improved latency by 50% in production."}, "c1"),
            AIMessage(content="Summary with one flagged rewrite."),
        ]
    )
    response = run_coach(_request(), chat_model=model, max_iterations=6)
    assert len(response.bullet_rewrites) == 1
    assert response.bullet_rewrites[0].flagged is True
    assert response.truth_constraint_notes  # the flagged rewrite is surfaced, not asserted
