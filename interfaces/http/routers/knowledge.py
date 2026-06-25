from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from application.agents.nodes.retrieve_node import reset_retriever_cache
from domain.models.schemas import KnowledgeItemRequest
from infrastructure.database.sqlite import get_conn, init_db
from infrastructure.retrieval.hybrid_retriever import HybridRetriever


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _row_to_item(row):
    item = dict(row)
    try:
        item["tags"] = json.loads(item.get("tags") or "[]")
    except Exception:
        item["tags"] = []
    return item


def _invalidate_retriever() -> None:
    try:
        reset_retriever_cache()
    except Exception:
        pass


@router.get("/items")
def list_items(
    collection: Optional[str] = None,
    platform: Optional[str] = None,
    content_type: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    init_db()
    conn = get_conn()

    where = []
    params = []

    if collection:
        where.append("collection = ?")
        params.append(collection)
    if platform:
        where.append("platform = ?")
        params.append(platform)
    if content_type:
        where.append("content_type = ?")
        params.append(content_type)
    if keyword:
        where.append("(title LIKE ? OR body LIKE ? OR tags LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like])

    sql = "SELECT * FROM knowledge_items"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return {"items": [_row_to_item(row) for row in rows]}


@router.post("/items")
def create_item(req: KnowledgeItemRequest):
    init_db()
    conn = get_conn()
    cur = conn.execute(
        '''
        INSERT INTO knowledge_items(collection, title, body, platform, content_type, tags)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (
            req.collection,
            req.title,
            req.body,
            req.platform,
            req.content_type,
            json.dumps(req.tags, ensure_ascii=False),
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM knowledge_items WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    _invalidate_retriever()
    return _row_to_item(row)


@router.put("/items/{item_id}")
def update_item(item_id: int, req: KnowledgeItemRequest):
    init_db()
    conn = get_conn()
    conn.execute(
        '''
        UPDATE knowledge_items
        SET collection = ?, title = ?, body = ?, platform = ?, content_type = ?,
            tags = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''',
        (
            req.collection,
            req.title,
            req.body,
            req.platform,
            req.content_type,
            json.dumps(req.tags, ensure_ascii=False),
            item_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM knowledge_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="knowledge item not found")

    _invalidate_retriever()
    return _row_to_item(row)


@router.delete("/items/{item_id}")
def delete_item(item_id: int):
    init_db()
    conn = get_conn()
    row = conn.execute("SELECT id FROM knowledge_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="knowledge item not found")

    conn.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    _invalidate_retriever()
    return {"deleted": True, "id": item_id}


@router.post("/reindex")
def rebuild_vector_index(force: bool = True):
    retriever = HybridRetriever(data_dir="data")
    result = retriever.reset_vector_indexes(force=force)
    _invalidate_retriever()
    return {
        "message": "vector index rebuilt",
        "force": force,
        "result": result,
    }
