import json
from typing import Any, Dict


def safe_json_loads(text: str, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    default = default or {}
    try:
        return json.loads(text)
    except Exception:
        return default
