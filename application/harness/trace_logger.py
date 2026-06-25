import time
from typing import Any, Dict


class TraceLogger:
    @staticmethod
    def add_trace(state: Dict[str, Any], node: str, message: str, **extra: Any) -> Dict[str, Any]:
        trace = state.setdefault("trace", [])
        trace.append({
            "node": node,
            "message": message,
            "timestamp": round(time.time(), 3),
            **extra,
        })
        return state
