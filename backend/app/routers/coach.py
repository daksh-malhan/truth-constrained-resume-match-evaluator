from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.language_models.chat_models import BaseChatModel
from starlette.concurrency import run_in_threadpool

from ..agent.loop import run_coach
from ..agent.schemas import CoachRequest, CoachResponse

router = APIRouter(tags=["coach"])


def get_agent_model() -> Optional[BaseChatModel]:
    """Chat-model dependency. Returns None so run_coach uses the default Ollama model.

    Tests override this to inject a deterministic model.
    """
    return None


@router.post("/coach", response_model=CoachResponse)
async def coach(request: CoachRequest, chat_model: Optional[BaseChatModel] = Depends(get_agent_model)):
    try:
        return await run_in_threadpool(run_coach, request, chat_model=chat_model)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)})
