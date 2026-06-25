from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


STYLE_MARKERS = {
    "体验分享型": ["我", "体验", "使用", "感受", "分享", "最近", "试了"],
    "理性分析型": ["原因", "因为", "适合", "不适合", "因素", "分析", "判断", "边界"],
    "种草推荐型": ["推荐", "入手", "适合", "值得", "选择", "需求"],
    "知识科普型": ["方法", "步骤", "误区", "原理", "建议", "总结", "首先", "其次"],
    "弱营销型": ["可以考虑", "按需选择", "理性", "结合实际", "不一定适合所有人"],
    "强营销型": ["快冲", "必买", "闭眼入", "错过后悔", "必须入手"],
}


TONE_MARKERS = {
    "克制": ["理性", "建议", "可能", "不一定", "结合实际", "因人而异"],
    "口语": ["真的", "其实", "先说", "我觉得", "看下来", "简单说"],
    "专业": ["因素", "结构", "场景", "边界", "依据", "分析"],
    "营销": ["福利", "下单", "入手", "冲", "限时", "名额"],
}


def _safe_text(doc: Dict[str, Any]) -> str:
    parts = [
        str(doc.get("title", "")),
        str(doc.get("body", "")),
        str(doc.get("text", "")),
        str(doc.get("reason", "")),
    ]
    return " ".join(p for p in parts if p.strip())


def _avg_length(texts: List[str]) -> int:
    if not texts:
        return 0
    return int(sum(len(t) for t in texts) / len(texts))


def _count_markers(text: str, marker_map: Dict[str, List[str]]) -> Dict[str, int]:
    scores: Dict[str, int] = {}

    for name, words in marker_map.items():
        scores[name] = sum(text.count(w) for w in words)

    return scores


def build_style_profile(history_docs: List[Dict[str, Any]], current_content: str = "") -> Dict[str, Any]:
    """
    根据用户历史内容生成风格画像。

    输入来自 retrieved_history，也可以为空。
    即使没有历史内容，也会返回可用的默认风格约束。
    """
    texts = [_safe_text(doc) for doc in history_docs if _safe_text(doc).strip()]
    merged_text = "\n".join(texts)

    if not texts:
        return {
            "has_history": False,
            "history_count": 0,
            "dominant_styles": ["平台适配型", "风险克制型"],
            "dominant_tones": ["克制", "专业"],
            "avg_length": 0,
            "style_summary": "暂无足够历史内容，系统将采用平台默认风格和安全表达策略。",
            "style_constraints": [
                "保持表达自然，不使用强营销或夸大承诺。",
                "优先补充适用场景、适用人群和理性选择建议。",
                "保留原文核心意思，但弱化风险表达。",
            ],
        }

    style_scores = _count_markers(merged_text, STYLE_MARKERS)
    tone_scores = _count_markers(merged_text, TONE_MARKERS)

    dominant_styles = [
        name for name, score in sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
        if score > 0
    ][:3]

    dominant_tones = [
        name for name, score in sorted(tone_scores.items(), key=lambda x: x[1], reverse=True)
        if score > 0
    ][:3]

    if not dominant_styles:
        dominant_styles = ["平台适配型"]

    if not dominant_tones:
        dominant_tones = ["克制"]

    word_counter = Counter()
    for text in texts:
        for token in ["理性", "适合", "体验", "建议", "场景", "选择", "注意", "边界", "需求"]:
            if token in text:
                word_counter[token] += text.count(token)

    common_terms = [w for w, _ in word_counter.most_common(6)]

    constraints = [
        f"尽量延续用户历史中的{dominant_tones[0]}表达语气。",
        f"内容风格优先贴近：{'、'.join(dominant_styles)}。",
        "不要为了模仿风格而保留违规风险表达。",
        "改写后仍需满足平台规则和风险控制要求。",
    ]

    if common_terms:
        constraints.append(f"可适度保留用户常用表达倾向：{'、'.join(common_terms)}。")

    avg_len = _avg_length(texts)

    return {
        "has_history": True,
        "history_count": len(texts),
        "dominant_styles": dominant_styles,
        "dominant_tones": dominant_tones,
        "avg_length": avg_len,
        "common_terms": common_terms,
        "style_summary": (
            f"基于 {len(texts)} 条历史内容，用户倾向于"
            f"{'、'.join(dominant_styles)}，语气偏{'、'.join(dominant_tones)}，"
            f"历史内容平均长度约 {avg_len} 字。"
        ),
        "style_constraints": constraints,
    }