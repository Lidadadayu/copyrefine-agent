from typing import Dict, List


def simple_rerank(docs: List[Dict], platform: str | None = None, content_type: str | None = None) -> List[Dict]:
    reranked = []
    for d in docs:
        score = float(d.get("score", 0)) + float(d.get("vector_score", 0)) * 3.0
        if platform and d.get("platform") == platform:
            score += 2.0
        if content_type and d.get("content_type") == content_type:
            score += 1.5
        item = dict(d)
        item["rerank_score"] = score
        reranked.append(item)
    return sorted(reranked, key=lambda x: x.get("rerank_score", 0), reverse=True)
