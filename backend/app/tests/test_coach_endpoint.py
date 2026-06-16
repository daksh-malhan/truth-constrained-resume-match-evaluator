from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from starlette.testclient import TestClient

from app.agent.context import clear_context_cache
from app.main import app
from app.routers.coach import get_agent_model


class FinalOnlyModel(BaseChatModel):
    """Chat model that immediately returns a final summary with no tool calls."""

    @property
    def _llm_type(self) -> str:
        return "final-only"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Coaching summary ready."))])


def test_coach_endpoint_returns_coached_result_and_trace():
    clear_context_cache()
    app.dependency_overrides[get_agent_model] = lambda: FinalOnlyModel()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/coach",
                json={
                    "resume": "SKILLS\nPython, FastAPI, Docker",
                    "job_description": "Backend Engineer Intern\nRequired: Python and REST API. Preferred: Kubernetes.",
                    "target_role": "Backend Engineer Intern",
                },
            )
    finally:
        app.dependency_overrides.pop(get_agent_model, None)

    assert response.status_code == 200
    body = response.json()
    assert body["initial_score"] is not None
    assert body["gaps"] is not None
    assert "tool_call_trace" in body
    assert body["iterations"] == 1
    assert body["stop_reason"] == "completed"
    assert "coaching summary" in body["final_summary"].lower()
