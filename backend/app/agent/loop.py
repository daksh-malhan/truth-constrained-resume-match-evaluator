from __future__ import annotations

import json
import os
import time
from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, MessagesState, StateGraph

from . import tools as tool_logic
from .context import build_coach_context
from .model import agent_model_name, agent_provider, get_chat_model
from .registry import build_coach_tools
from .schemas import CoachRequest, CoachResponse, RewriteResult, ToolCallTrace


SYSTEM_PROMPT = (
    "You are Resume Coach, an agent that coaches a resume toward a target job.\n"
    "You have tools: score_resume, find_gaps, rewrite_bullet, check_truth.\n"
    "Work in a ReAct loop: call score_resume and find_gaps to understand the fit, then "
    "rewrite_bullet on weak bullets using only facts already in the resume.\n"
    "TRUTH CONSTRAINT: never invent metrics, numbers, employers, seniority, or "
    "deployment/production claims. If a rewrite would add an unverifiable claim, the "
    "tool flags it; report it as a suggestion to verify, never as fact.\n"
    "When finished, stop calling tools and write a short coaching summary."
)


def _task_prompt(request: CoachRequest) -> str:
    role = request.target_role or "the target role"
    return (
        f"Coach this resume toward {role}. First score it and find gaps, then suggest "
        f"truth-constrained bullet rewrites, then summarize the top actions.\n\n"
        f"TARGET ROLE: {role}\n\nRESUME:\n{request.resume}\n\nJOB DESCRIPTION:\n{request.job_description}"
    )


def run_coach(
    request: CoachRequest,
    *,
    chat_model: Optional[BaseChatModel] = None,
    max_iterations: Optional[int] = None,
) -> CoachResponse:
    """Run the ReAct coaching loop and return the coached result plus the full trace."""
    max_iterations = max_iterations or int(os.getenv("COACH_MAX_ITERATIONS", "6"))
    ctx = build_coach_context(request.resume, request.job_description, request.target_role)
    lc_tools = build_coach_tools(ctx)
    tool_by_name = {t.name: t for t in lc_tools}

    model = chat_model or get_chat_model()
    bound = model.bind_tools(lc_tools)

    trace: List[ToolCallTrace] = []
    rewrites: List[RewriteResult] = []
    step_counter = {"n": 0}

    def agent_node(state: MessagesState) -> dict:
        step_counter["n"] += 1
        response = bound.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: MessagesState) -> dict:
        last = state["messages"][-1]
        out_messages = []
        for call in getattr(last, "tool_calls", []) or []:
            name = call["name"]
            args = call.get("args", {}) or {}
            call_id = call.get("id")
            started = time.perf_counter()
            error: Optional[str] = None
            result: dict = {}
            tool = tool_by_name.get(name)
            try:
                if tool is None:
                    raise KeyError(f"unknown tool '{name}'")
                invoked = tool.invoke(args)
                result = invoked if isinstance(invoked, dict) else {"value": invoked}
            except Exception as exc:  # keep the loop alive; record the failure
                error = str(exc)
                result = {"error": error}
            duration_ms = int((time.perf_counter() - started) * 1000)
            trace.append(
                ToolCallTrace(step=step_counter["n"], tool=name, args=args, result=result, duration_ms=duration_ms, error=error)
            )
            if name == "rewrite_bullet" and "rewrite" in result:
                rewrites.append(RewriteResult.model_validate(result))
            out_messages.append(ToolMessage(content=json.dumps(result, default=str), tool_call_id=call_id, name=name))
        return {"messages": out_messages}

    def should_continue(state: MessagesState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None) and step_counter["n"] < max_iterations:
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    compiled = graph.compile()

    seed = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=_task_prompt(request))]
    final_state = compiled.invoke({"messages": seed}, config={"recursion_limit": max_iterations * 2 + 5})

    final_message = final_state["messages"][-1]
    hit_cap = step_counter["n"] >= max_iterations and bool(getattr(final_message, "tool_calls", None))
    final_summary = final_message.content if isinstance(final_message, AIMessage) else ""
    if hit_cap and not final_summary:
        final_summary = "Coaching stopped at the iteration cap before a final summary was produced."

    # Deterministic enrichment so the response is always complete and grounded,
    # independent of which tools the model happened to call.
    score_result = tool_logic.score_resume(ctx)
    gaps_result = tool_logic.find_gaps(ctx)
    notes = [
        f"Flagged rewrite (verify before using, do not assert): {r.rewrite} -> {'; '.join(r.unsupported_claims)}"
        for r in rewrites
        if r.flagged
    ]

    return CoachResponse(
        target_role=request.target_role,
        initial_score=score_result.score,
        score_breakdown=score_result.breakdown,
        gaps=gaps_result,
        bullet_rewrites=rewrites,
        truth_constraint_notes=notes,
        final_summary=final_summary or "",
        iterations=step_counter["n"],
        stop_reason="max_iterations" if hit_cap else "completed",
        tool_call_trace=trace,
        llm_provider=agent_provider() if chat_model is None else "injected",
        model=agent_model_name() if chat_model is None else type(chat_model).__name__,
    )
