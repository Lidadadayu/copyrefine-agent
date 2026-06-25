from typing import Any, Dict
from application.harness.trace_logger import TraceLogger


def intake_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("trace", [])
    state.setdefault("errors", [])
    state["raw_content"] = state.get("raw_content", "").strip()
    if not state["raw_content"]:
        state["errors"].append("原始文案为空")
    TraceLogger.add_trace(state, "intake_node", "输入标准化完成")
    return state
