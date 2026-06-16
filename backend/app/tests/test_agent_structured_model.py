"""Tests for the structured-output tool-call fallback (models without native tools)."""
from typing import List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool

from app import database
from app.agent.context import clear_context_cache
from app.agent.loop import run_coach
from app.agent.schemas import CoachRequest
from app.agent.structured_model import StructuredToolCallingModel


class JsonBase(BaseChatModel):
    """Fake base model that returns scripted JSON strings (as a tools-less model would)."""

    outputs: List[str] = []
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "json-base"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        idx = self.calls
        self.calls += 1
        content = self.outputs[idx] if idx < len(self.outputs) else '{"final": "done"}'
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


@tool
def score_resume(resume: str = "", job_description: str = "") -> dict:
    """Score the resume."""
    return {}


def test_structured_model_parses_tool_call_json():
    model = StructuredToolCallingModel(base=JsonBase(outputs=['{"tool": "score_resume", "args": {}}'])).bind_tools([score_resume])
    msg = model.invoke([HumanMessage(content="coach me")])
    assert msg.tool_calls
    assert msg.tool_calls[0]["name"] == "score_resume"


def test_structured_model_parses_openai_style_tool_call():
    # Many models emit {"name": ..., "arguments": ...} instead of {"tool": ..., "args": ...}.
    model = StructuredToolCallingModel(base=JsonBase(outputs=['{"name": "score_resume", "arguments": {"resume": "x"}}'])).bind_tools([score_resume])
    msg = model.invoke([HumanMessage(content="coach me")])
    assert msg.tool_calls
    assert msg.tool_calls[0]["name"] == "score_resume"
    assert msg.tool_calls[0]["args"] == {"resume": "x"}


def test_structured_model_parses_final_json():
    model = StructuredToolCallingModel(base=JsonBase(outputs=['{"final": "All set."}'])).bind_tools([score_resume])
    msg = model.invoke([HumanMessage(content="coach me")])
    assert not msg.tool_calls
    assert "All set." in msg.content


def test_structured_model_drives_the_real_loop():
    database.init_db()
    clear_context_cache()
    base = JsonBase(outputs=['{"tool": "score_resume", "args": {}}', '{"final": "Summary done."}'])
    model = StructuredToolCallingModel(base=base)
    request = CoachRequest(resume="SKILLS\nPython", job_description="Required: Python", target_role="Dev")
    response = run_coach(request, chat_model=model, max_iterations=4)
    assert [t.tool for t in response.tool_call_trace] == ["score_resume"]
    assert "Summary done." in response.final_summary
