from __future__ import annotations

import json
import uuid
from typing import Any, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult


_INSTRUCTION = (
    "You can call tools by replying with ONLY a single JSON object, no prose.\n"
    'To call a tool: {{"tool": "<name>", "args": {{...}}}}\n'
    'When you are finished, reply: {{"final": "<your coaching summary>"}}\n'
    "Available tools:\n{catalog}"
)


def _extract_json(text: str) -> str:
    """Best-effort: isolate the first JSON object in the text."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


# Different models name the fields differently; accept the common conventions.
_TOOL_NAME_KEYS = ("tool", "name", "function", "action")
_ARGS_KEYS = ("args", "arguments", "parameters", "action_input", "input")
_FINAL_KEYS = ("final", "answer", "response", "output", "summary")


def _first(data: dict, keys) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _parse(content: str, tool_names: set[str]) -> AIMessage:
    try:
        data = json.loads(_extract_json(content))
    except Exception:
        return AIMessage(content=content)
    if isinstance(data, dict):
        name = _first(data, _TOOL_NAME_KEYS)
        if name in tool_names:
            args = _first(data, _ARGS_KEYS)
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": name,
                        "args": args if isinstance(args, dict) else {},
                        "id": f"struct_{uuid.uuid4().hex[:8]}",
                        "type": "tool_call",
                    }
                ],
            )
        final = _first(data, _FINAL_KEYS)
        if final is not None:
            return AIMessage(content=str(final))
    # Unrecognized JSON: treat the raw content as a final answer.
    return AIMessage(content=content)


class StructuredToolCallingModel(BaseChatModel):
    """Tool-calling via structured JSON output, for models without native tool support.

    Wraps any BaseChatModel: it injects a tool catalog + JSON protocol into the prompt,
    then parses the model's JSON reply into either tool calls or a final answer. This is
    the spec's fallback for when Ollama function-calling is unavailable for the model.
    """

    base: BaseChatModel
    tools: List[Any] = []

    @property
    def _llm_type(self) -> str:
        return "structured-tool-calling"

    def bind_tools(self, tools, **kwargs) -> "StructuredToolCallingModel":
        return self.model_copy(update={"tools": list(tools)})

    def _tool_catalog(self) -> str:
        lines = []
        for tool in self.tools:
            args = ", ".join(getattr(tool, "args", {}).keys())
            description = (getattr(tool, "description", "") or "").split("\n")[0]
            lines.append(f"- {tool.name}({args}): {description}")
        return "\n".join(lines)

    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        instruction = SystemMessage(content=_INSTRUCTION.format(catalog=self._tool_catalog()))
        raw = self.base.invoke([instruction, *messages])
        content = raw.content if isinstance(raw, AIMessage) else str(raw)
        message = _parse(content if isinstance(content, str) else str(content), {t.name for t in self.tools})
        return ChatResult(generations=[ChatGeneration(message=message)])
