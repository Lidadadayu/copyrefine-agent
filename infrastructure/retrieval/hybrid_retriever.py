from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .bm25_store import BM25Store
from .document_loader import load_jsonl
from .reranker import simple_rerank
from .vector_store import ChromaVectorStore
from infrastructure.database.sqlite import get_conn, init_db


class HybridRetriever:
    def __init__(self, data_dir: str | Path = "data"):
        base_dir = Path(data_dir)

        self.rules = load_jsonl(base_dir / "platform_rules.jsonl")
        self.risks = load_jsonl(base_dir / "risk_expressions.jsonl")
        self.cases = load_jsonl(base_dir / "content_cases.jsonl")
        self.history = load_jsonl(base_dir / "seed_history.jsonl")

        self.rule_store = BM25Store(self.rules, text_field="text")
        self.risk_store = BM25Store(self.risks, text_field="text")

        # 案例库没有 text 字段，主要字段是 title/body/reason。
        self.case_store = BM25Store(self.cases, text_field="body")
        self.history_store = BM25Store(self.history, text_field="body")

        self.case_vector_store = ChromaVectorStore("content_cases")
        self.history_vector_store = ChromaVectorStore("seed_history")
        self.knowledge_vector_store = ChromaVectorStore("knowledge_items")
        self.db_history_vector_store = ChromaVectorStore("content_task_history")

        self.reset_vector_indexes(force=False)

    def reset_vector_indexes(self, force: bool = False) -> Dict[str, int | bool]:
        """
        Rebuild Chroma indexes for file-based cases/history and DB knowledge/history.

        The vector store internally skips unchanged corpora unless force=True.
        """

        knowledge = self._db_knowledge()
        db_history = self._db_history()

        self.case_vector_store.reset(self.cases, "body", force=force)
        self.history_vector_store.reset(self.history, "body", force=force)
        self.knowledge_vector_store.reset(knowledge, "body", force=force)
        self.db_history_vector_store.reset(db_history, "body", force=force)

        return {
            "ok": True,
            "content_cases": len(self.cases),
            "seed_history": len(self.history),
            "knowledge_items": len(knowledge),
            "content_task_history": len(db_history),
        }

    def _db_knowledge(self) -> List[Dict]:
        init_db()
        conn = get_conn()
        rows = conn.execute("SELECT * FROM knowledge_items ORDER BY updated_at DESC").fetchall()
        conn.close()
        items = []
        for row in rows:
            item = dict(row)
            try:
                item["tags"] = json.loads(item.get("tags") or "[]")
            except Exception:
                item["tags"] = []
            items.append(item)
        return items

    def _db_history(self) -> List[Dict]:
        init_db()
        conn = get_conn()
        rows = conn.execute(
            '''
            SELECT task_id, platform, content_type, raw_content AS body, final_report AS reason
            FROM content_tasks
            ORDER BY created_at DESC
            LIMIT 100
            '''
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def _merge(self, *groups: List[Dict]) -> List[Dict]:
        seen = set()
        merged = []
        for group in groups:
            for item in group:
                key = (
                    item.get("id"),
                    item.get("task_id"),
                    item.get("title"),
                    item.get("body"),
                    item.get("text"),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        return merged

    def retrieve(
        self,
        queries: List[str],
        routes: List[str],
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, List[Dict]]:
        query_text = " ".join(queries)

        result: Dict[str, List[Dict]] = {
            "rules": [],
            "risks": [],
            "cases": [],
            "history": [],
        }

        if "platform_rules" in routes:
            filters = {"platform": platform} if platform else None
            docs = self.rule_store.search(query_text, top_k=6, filters=filters)
            result["rules"] = simple_rerank(docs, platform, content_type)

        if "risk_expressions" in routes:
            docs = self.risk_store.search(query_text, top_k=8)
            result["risks"] = simple_rerank(docs, platform, content_type)

        if "content_cases" in routes:
            filters = {"platform": platform} if platform else None
            knowledge = self._db_knowledge()
            knowledge_store = BM25Store(knowledge, text_field="body")
            self.knowledge_vector_store.reset(knowledge, "body", force=False)

            docs = self._merge(
                self.case_store.search(query_text, top_k=5, filters=filters),
                knowledge_store.search(query_text, top_k=5, filters=filters),
                self.case_vector_store.search(query_text, self.cases, top_k=5, filters=filters),
                self.knowledge_vector_store.search(query_text, knowledge, top_k=5, filters=filters),
            )
            result["cases"] = simple_rerank(docs, platform, content_type)

        if "user_history" in routes:
            db_history = self._db_history()
            history_store = BM25Store(db_history, text_field="body")
            self.db_history_vector_store.reset(db_history, "body", force=False)

            docs = self._merge(
                self.history_store.search(query_text, top_k=4),
                history_store.search(query_text, top_k=4),
                self.history_vector_store.search(query_text, self.history, top_k=4),
                self.db_history_vector_store.search(query_text, db_history, top_k=4),
            )
            result["history"] = simple_rerank(docs, platform, content_type)

        return result
