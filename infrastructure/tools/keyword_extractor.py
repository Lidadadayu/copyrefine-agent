from typing import List
import jieba


STOPWORDS = {"这个", "那个", "大家", "一个", "可以", "真的", "非常", "就是", "已经"}


def extract_keywords(text: str, top_k: int = 8) -> List[str]:
    words = [w.strip() for w in jieba.cut(text) if len(w.strip()) > 1 and w.strip() not in STOPWORDS]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_k]]
