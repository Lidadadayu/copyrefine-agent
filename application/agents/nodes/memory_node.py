from typing import Any, Dict
from application.harness.trace_logger import TraceLogger
from infrastructure.database.sqlite import get_conn, init_db


def memory_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        init_db()
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO content_tasks(task_id, user_id, platform, content_type, raw_content, risk_level, score, final_report) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                state.get("task_id"),
                state.get("user_id"),
                state.get("detected_platform"),
                state.get("detected_content_type"),
                state.get("raw_content"),
                state.get("risk_level"),
                int(state.get("score", 0)),
                state.get("final_report"),
            ),
        )
        for v in state.get("rewritten_versions", []):
            conn.execute(
                "INSERT INTO content_versions(task_id, version_type, title, body, score, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    state.get("task_id"),
                    v.get("version_type"),
                    v.get("title"),
                    v.get("body"),
                    int(v.get("score", 0)),
                    v.get("notes"),
                ),
            )
        conn.commit()
        conn.close()
        TraceLogger.add_trace(state, "memory_node", "历史写入完成")
    except Exception as e:
        state.setdefault("errors", []).append(str(e))
        TraceLogger.add_trace(state, "memory_node", "历史写入失败", error=str(e))
    return state
