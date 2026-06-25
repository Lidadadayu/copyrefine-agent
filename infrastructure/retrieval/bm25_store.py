from typing import Dict, List
import jieba
from rank_bm25 import BM25Okapi


class BM25Store:
    def __init__(self, docs: List[Dict], text_field: str = "text"):
        self.docs = docs
        self.text_field = text_field

        corpus = [self._tokenize(self._get_doc_text(d)) for d in docs]

        # 防止所有文档都是空文本，导致 BM25 内部 division by zero
        if not corpus or all(len(tokens) == 0 for tokens in corpus):
            self.bm25 = None
        else:
            self.bm25 = BM25Okapi(corpus)

    def _get_doc_text(self, doc: Dict) -> str:
        # 优先使用指定字段
        text = doc.get(self.text_field, "")
        if text:
            return str(text)

        # 兜底：如果指定字段不存在，则拼接常见文本字段
        fallback_fields = ["title", "body", "reason", "suggestion", "description"]
        parts = [str(doc.get(field, "")) for field in fallback_fields if doc.get(field)]
        return " ".join(parts)

    def _tokenize(self, text: str) -> List[str]:
        return [w for w in jieba.cut(text) if w.strip()]

    def search(self, query: str, top_k: int = 5, filters: Dict | None = None) -> List[Dict]:
        if not self.docs or not self.bm25:
            return []

        filters = filters or {}
        scores = self.bm25.get_scores(self._tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in ranked:
            doc = self.docs[idx]

            ok = True
            for k, v in filters.items():
                if v is not None and doc.get(k) != v:
                    ok = False
                    break

            if ok:
                item = dict(doc)
                item["score"] = float(score)
                results.append(item)

            if len(results) >= top_k:
                break

        return results