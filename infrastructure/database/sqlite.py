import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_PATH = Path("contentpilot.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS content_tasks (
            task_id TEXT PRIMARY KEY,
            user_id TEXT,
            platform TEXT,
            content_type TEXT,
            raw_content TEXT,
            risk_level TEXT,
            score INTEGER,
            final_report TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS content_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            version_type TEXT,
            title TEXT,
            body TEXT,
            score INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            user_id TEXT,
            rating INTEGER,
            comment TEXT,
            preferred_version_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            preference_text TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection TEXT,
            title TEXT,
            body TEXT,
            platform TEXT,
            content_type TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            task_id TEXT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.commit()
    conn.close()


def fetch_task(task_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_conn()
    row = conn.execute("SELECT * FROM content_tasks WHERE task_id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_task_versions(task_id: str) -> List[Dict[str, Any]]:
    init_db()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM content_versions WHERE task_id = ? ORDER BY id ASC",
        (task_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_task(task_id: str) -> bool:
    init_db()
    conn = get_conn()
    row = conn.execute("SELECT task_id FROM content_tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        return False

    conn.execute("DELETE FROM content_versions WHERE task_id = ?", (task_id,))
    conn.execute("DELETE FROM user_feedback WHERE task_id = ?", (task_id,))
    conn.execute("DELETE FROM conversation_messages WHERE task_id = ?", (task_id,))
    conn.execute("DELETE FROM content_tasks WHERE task_id = ?", (task_id,))
    conn.commit()
    conn.close()
    return True


def delete_all_tasks(user_id: Optional[str] = None) -> int:
    init_db()
    conn = get_conn()
    if user_id:
        rows = conn.execute("SELECT task_id FROM content_tasks WHERE user_id = ?", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT task_id FROM content_tasks").fetchall()

    task_ids = [str(row["task_id"]) for row in rows]
    for task_id in task_ids:
        conn.execute("DELETE FROM content_versions WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM user_feedback WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM conversation_messages WHERE task_id = ?", (task_id,))

    if user_id:
        conn.execute("DELETE FROM content_tasks WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM conversation_messages WHERE user_id = ?", (user_id,))
    else:
        conn.execute("DELETE FROM content_tasks")
        conn.execute("DELETE FROM conversation_messages")

    conn.commit()
    conn.close()
    return len(task_ids)


def append_conversation_message(
    conversation_id: str,
    task_id: str,
    user_id: str,
    role: str,
    content: str,
) -> Dict[str, Any]:
    init_db()
    conn = get_conn()
    cur = conn.execute(
        '''
        INSERT INTO conversation_messages(conversation_id, task_id, user_id, role, content)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (conversation_id, task_id, user_id, role, content),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM conversation_messages WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def fetch_conversation_messages(conversation_id: str) -> List[Dict[str, Any]]:
    init_db()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM conversation_messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_preference(user_id: str) -> str:
    init_db()
    conn = get_conn()
    row = conn.execute(
        "SELECT preference_text FROM user_preferences WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return str(row["preference_text"]) if row and row["preference_text"] else ""


def upsert_user_preference(user_id: str, preference_text: str) -> Dict[str, Any]:
    init_db()
    conn = get_conn()
    conn.execute(
        '''
        INSERT INTO user_preferences(user_id, preference_text, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            preference_text = excluded.preference_text,
            updated_at = CURRENT_TIMESTAMP
        ''',
        (user_id, preference_text.strip()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT user_id, preference_text, updated_at FROM user_preferences WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {"user_id": user_id, "preference_text": preference_text}


def append_user_feedback(
    task_id: str,
    user_id: str,
    rating: Optional[int],
    comment: str,
    preferred_version_type: Optional[str],
) -> Dict[str, Any]:
    init_db()
    conn = get_conn()
    cur = conn.execute(
        '''
        INSERT INTO user_feedback(task_id, user_id, rating, comment, preferred_version_type)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (task_id, user_id, rating, comment.strip(), preferred_version_type),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_feedback WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)
