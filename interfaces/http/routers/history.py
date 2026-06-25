from fastapi import APIRouter, HTTPException, Query
from infrastructure.database.sqlite import (
    delete_all_tasks,
    delete_task,
    fetch_conversation_messages,
    get_conn,
    init_db,
)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/tasks")
def list_tasks(limit: int = 20):
    init_db()
    conn = get_conn()
    rows = conn.execute(
        "SELECT task_id, platform, content_type, risk_level, score, created_at FROM content_tasks ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}


@router.delete("/tasks")
def clear_tasks(user_id: str | None = Query(default=None)):
    deleted = delete_all_tasks(user_id=user_id)
    return {"deleted": deleted, "user_id": user_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    init_db()
    conn = get_conn()
    task = conn.execute("SELECT * FROM content_tasks WHERE task_id = ?", (task_id,)).fetchone()
    versions = conn.execute("SELECT * FROM content_versions WHERE task_id = ?", (task_id,)).fetchall()
    conn.close()
    return {
        "task": dict(task) if task else None,
        "versions": [dict(v) for v in versions],
    }


@router.delete("/tasks/{task_id}")
def remove_task(task_id: str):
    if not delete_task(task_id):
        raise HTTPException(status_code=404, detail="task not found")
    return {"deleted": True, "task_id": task_id}


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str):
    return {"items": fetch_conversation_messages(conversation_id)}


@router.get("/tasks/{task_id}/reuse")
def reuse_task(task_id: str, version_id: int | None = None):
    init_db()
    conn = get_conn()
    task = conn.execute("SELECT * FROM content_tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not task:
        conn.close()
        return {"payload": None}

    raw_content = task["raw_content"]
    if version_id is not None:
        version = conn.execute(
            "SELECT body FROM content_versions WHERE id = ? AND task_id = ?",
            (version_id, task_id),
        ).fetchone()
        if version and version["body"]:
            raw_content = version["body"]

    conn.close()
    return {
        "payload": {
            "raw_content": raw_content,
            "platform": task["platform"],
            "content_type": task["content_type"],
            "task_type": "review_and_rewrite",
            "user_id": task["user_id"] or "default_user",
            "parent_task_id": task_id,
        }
    }
