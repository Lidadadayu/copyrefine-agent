from typing import Dict


def score_title(title: str, platform: str = "xiaohongshu") -> Dict:
    length = len(title)
    score = 80
    notes = []

    if platform == "xiaohongshu":
        if length < 8:
            score -= 10
            notes.append("标题略短，缺少具体场景。")
        if length > 28:
            score -= 10
            notes.append("标题偏长，小红书场景下可以更轻量。")
    else:
        if length > 40:
            score -= 10
            notes.append("标题偏长。")

    risky_words = ["绝对", "100%", "必看", "震惊", "无副作用"]
    if any(w in title for w in risky_words):
        score -= 20
        notes.append("标题含高风险或过度刺激表达。")

    if not notes:
        notes.append("标题长度和表达较为稳妥。")

    return {"score": max(0, min(100, score)), "notes": notes}
