from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from loguru import logger

from .embedding_client import HashEmbeddingFunction, get_embedding_function


class ChromaVectorStore:
    def __init__(self, name: str, persist_dir: str | Path = "data/chroma") -> None:
        self.enabled = False
        self.collection: Any = None
        self.raw_name = name
        self.embedding_function: Any = get_embedding_function()
        self.collection_name = _safe_collection_name(name, self.embedding_function.name())

        try:
            import chromadb
        except Exception as exc:
            logger.warning("Chroma is unavailable, vector retrieval disabled: {}", exc)
            return

        try:
            client = chromadb.PersistentClient(path=str(persist_dir))
            self.collection = client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=cast(Any, self.embedding_function),
                metadata={"hnsw:space": "cosine", "embedding": self.embedding_function.name()},
            )
            self.enabled = True
        except Exception as exc:
            # Vector retrieval is only an enhancement. If Chroma initialization
            # fails, keep the main workflow usable through BM25 retrieval.
            logger.warning("Chroma collection init failed, vector retrieval disabled: {}", exc)
            self.enabled = False
            self.collection = None

    def reset(self, docs: List[Dict[str, Any]], text_field: str, force: bool = False) -> None:
        if not self.enabled or self.collection is None:
            return

        try:
            ids = [str(i) for i in range(len(docs))]
            texts = [_doc_text(doc, text_field) for doc in docs]
            metadatas = [_metadata(doc, i, text_field) for i, doc in enumerate(docs)]

            existing = self.collection.get(include=["metadatas"])
            existing_ids = (existing or {}).get("ids") or []
            existing_metas = (existing or {}).get("metadatas") or []

            if not force and _is_same_index(existing_ids, existing_metas, ids, metadatas):
                return

            if existing_ids:
                self.collection.delete(ids=cast(Any, existing_ids))

            if not docs:
                return

            self.collection.add(
                ids=cast(Any, ids),
                documents=cast(Any, texts),
                metadatas=cast(Any, metadatas),
            )
        except Exception as exc:
            # External embeddings can fail due to network/API problems. Do not
            # break the main workflow; BM25 retrieval still works.
            logger.warning("Vector index reset failed for {}: {}", self.collection_name, exc)
            self.enabled = False
            self.collection = None

    def search(
        self,
        query: str,
        docs: List[Dict[str, Any]],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.enabled or self.collection is None or not query.strip():
            return []

        try:
            result = self.collection.query(query_texts=[query], n_results=max(top_k * 3, 1))
        except Exception as exc:
            logger.warning("Vector search failed for {}: {}", self.collection_name, exc)
            return []

        if not isinstance(result, dict):
            return []

        ids_groups = result.get("ids") or [[]]
        distance_groups = result.get("distances") or [[]]

        if not ids_groups or not ids_groups[0]:
            return []

        ids = ids_groups[0]
        distances = distance_groups[0] if distance_groups and distance_groups[0] else [0.0] * len(ids)

        items: List[Dict[str, Any]] = []

        for raw_id, distance in zip(ids, distances):
            try:
                idx = int(raw_id)
            except Exception:
                continue

            if idx < 0 or idx >= len(docs):
                continue

            doc = docs[idx]
            if not _match_filters(doc, filters or {}):
                continue

            item = dict(doc)
            item["vector_score"] = 1.0 / (1.0 + float(distance or 0.0))
            item["vector_collection"] = self.collection_name
            items.append(item)

            if len(items) >= top_k:
                break

        return items


def _safe_collection_name(name: str, embedding_name: str) -> str:
    raw = f"{name}_{embedding_name}".lower()
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in raw).strip("_-")
    if len(safe) < 3:
        safe = f"cp_{safe}"
    if len(safe) > 63:
        digest = hashlib.md5(safe.encode("utf-8")).hexdigest()[:8]
        safe = f"{safe[:54].rstrip('_-')}_{digest}"
    return safe


def _doc_text(doc: Dict[str, Any], text_field: str) -> str:
    fields = [text_field, "title", "body", "text", "reason", "suggestion", "tags"]
    parts = []
    for field in fields:
        value = doc.get(field)
        if isinstance(value, list):
            parts.append(" ".join(str(item) for item in value if item))
        elif value:
            parts.append(str(value))
    return " ".join(parts).strip()


def _metadata(doc: Dict[str, Any], idx: int, text_field: str) -> Dict[str, str | int | float | bool | None]:
    text = _doc_text(doc, text_field)
    source_payload = {
        "idx": idx,
        "id": doc.get("id"),
        "task_id": doc.get("task_id"),
        "title": doc.get("title"),
        "body": doc.get("body"),
        "text": doc.get("text"),
        "platform": doc.get("platform"),
        "content_type": doc.get("content_type"),
        "collection": doc.get("collection"),
    }
    source_hash = hashlib.md5(
        json.dumps(source_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "idx": int(idx),
        "source_hash": source_hash,
        "text_hash": hashlib.md5(text.encode("utf-8")).hexdigest(),
        "platform": str(doc.get("platform") or ""),
        "content_type": str(doc.get("content_type") or ""),
        "collection": str(doc.get("collection") or ""),
    }


def _is_same_index(
    existing_ids: List[Any],
    existing_metas: List[Any],
    ids: List[str],
    metadatas: List[Dict[str, Any]],
) -> bool:
    if len(existing_ids) != len(ids) or len(existing_metas) != len(metadatas):
        return False

    existing_hashes = {
        str(raw_id): str(meta.get("source_hash", ""))
        for raw_id, meta in zip(existing_ids, existing_metas)
        if isinstance(meta, dict)
    }
    expected_hashes = {str(raw_id): str(meta.get("source_hash", "")) for raw_id, meta in zip(ids, metadatas)}
    return existing_hashes == expected_hashes


def _match_filters(doc: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    for key, value in filters.items():
        if value is not None and doc.get(key) != value:
            return False
    return True


__all__ = ["ChromaVectorStore", "HashEmbeddingFunction"]
