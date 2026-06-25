from __future__ import annotations

from typing import Any, Dict, List


def _clamp(value: int | float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def _risk_safety_score(risk_items: List[Dict[str, Any]]) -> int:
    score = 100

    for item in risk_items:
        severity = item.get("severity", "low")
        if severity == "high":
            score -= 22
        elif severity == "medium":
            score -= 12
        else:
            score -= 6

    return _clamp(score)


def _platform_fit_score(profile: Dict[str, Any], strategy: Dict[str, Any]) -> int:
    score = 70

    if profile.get("has_scene"):
        score += 8
    if profile.get("has_audience"):
        score += 8
    if profile.get("has_evidence"):
        score += 8
    if not profile.get("has_strong_marketing"):
        score += 6

    platform = profile.get("platform")

    if platform == "xiaohongshu":
        if profile.get("has_scene"):
            score += 5
        if profile.get("length_level") in ["short", "medium"]:
            score += 3

    elif platform == "wechat":
        if profile.get("length_level") in ["medium", "long"]:
            score += 5
        if profile.get("has_evidence"):
            score += 5

    elif platform == "zhihu":
        if profile.get("has_evidence"):
            score += 8

    elif platform == "short_video":
        if profile.get("length_level") in ["short", "medium"]:
            score += 8

    return _clamp(score)


def _structure_score(profile: Dict[str, Any], structure_report: Dict[str, Any]) -> int:
    score = 100

    problem_count = int(structure_report.get("problem_count", 0))
    score -= problem_count * 12

    if not profile.get("has_scene"):
        score -= 8
    if not profile.get("has_audience"):
        score -= 8
    if not profile.get("has_evidence"):
        score -= 8

    if profile.get("length_level") == "short":
        score -= 8

    return _clamp(score)


def _evidence_score(evidence_pack: Dict[str, Any]) -> int:
    top_rules = evidence_pack.get("top_rules", [])
    top_risks = evidence_pack.get("top_risk_expressions", [])
    similar_cases = evidence_pack.get("similar_cases", [])
    decision_notes = evidence_pack.get("decision_notes", [])

    score = 40

    score += min(len(top_rules), 5) * 6
    score += min(len(top_risks), 5) * 5
    score += min(len(similar_cases), 4) * 6
    score += min(len(decision_notes), 4) * 4

    return _clamp(score)


def _title_score(title_suggestions: List[str]) -> int:
    if not title_suggestions:
        return 0

    score = 60

    count = len(title_suggestions)
    score += min(count, 3) * 8

    good_titles = 0
    for title in title_suggestions:
        title = str(title).strip()
        if 8 <= len(title) <= 32:
            good_titles += 1
        if any(mark in title for mark in ["？", "?", "：", ":", "怎么", "如何", "为什么"]):
            good_titles += 1

    score += min(good_titles, 5) * 4

    return _clamp(score)


def _readability_score(content: str) -> int:
    text = content.strip()

    if not text:
        return 0

    score = 80

    length = len(text)

    if length < 20:
        score -= 15
    elif length > 600:
        score -= 10

    long_sentence_count = 0
    sentences = [s for s in text.replace("！", "。").replace("？", "。").split("。") if s.strip()]

    for sentence in sentences:
        if len(sentence) > 60:
            long_sentence_count += 1

    score -= long_sentence_count * 6

    if "\n" in text:
        score += 5

    if any(mark in text for mark in ["首先", "其次", "最后", "第一", "第二", "总结"]):
        score += 5

    return _clamp(score)


def _generate_quality_suggestions(
    dimension_scores: Dict[str, int],
    profile: Dict[str, Any],
    risk_items: List[Dict[str, Any]],
) -> List[str]:
    suggestions: List[str] = []

    if dimension_scores["risk_safety"] < 80:
        suggestions.append("风险安全分偏低，建议优先处理绝对化承诺、效果承诺和强诱导表达。")

    if dimension_scores["platform_fit"] < 80:
        suggestions.append("平台适配分仍有提升空间，建议根据目标平台调整语气、结构和表达方式。")

    if dimension_scores["structure"] < 80:
        suggestions.append("结构完整度不足，建议补充使用场景、适用人群、原因依据和结尾建议。")

    if dimension_scores["evidence"] < 80:
        suggestions.append("检索证据支撑不足，建议扩充平台规则库、风险表达库和相似案例库。")

    if dimension_scores["title"] < 75:
        suggestions.append("标题质量偏弱，建议生成更贴近平台风格、信息明确且不过度夸张的标题。")

    if dimension_scores["readability"] < 80:
        suggestions.append("可读性有待提升，建议拆分长句、增加分段，并减少口号式表达。")

    if profile.get("has_strong_marketing"):
        suggestions.append("原文营销感较强，建议把直接催促购买改成理性选择建议。")

    if risk_items and not suggestions:
        suggestions.append("整体质量尚可，但仍建议复查风险词是否已经在改写版本中被充分弱化。")

    if not suggestions:
        suggestions.append("内容整体质量较好，可进一步根据平台风格微调标题和表达节奏。")

    return suggestions


def compute_quality_scores(state: Dict[str, Any]) -> Dict[str, Any]:
    risk_items = state.get("risk_report", {}).get("items", [])
    structure_report = state.get("structure_report", {})
    profile = state.get("content_profile", {})
    strategy = state.get("platform_strategy", {})
    evidence_pack = state.get("evidence_pack", {})
    title_suggestions = state.get("title_suggestions", [])
    raw_content = state.get("raw_content", "")

    dimension_scores = {
        "risk_safety": _risk_safety_score(risk_items),
        "platform_fit": _platform_fit_score(profile, strategy),
        "structure": _structure_score(profile, structure_report),
        "evidence": _evidence_score(evidence_pack),
        "title": _title_score(title_suggestions),
        "readability": _readability_score(raw_content),
    }

    weights = {
        "risk_safety": 0.30,
        "platform_fit": 0.18,
        "structure": 0.16,
        "evidence": 0.14,
        "title": 0.10,
        "readability": 0.12,
    }

    total = 0.0
    for key, weight in weights.items():
        total += dimension_scores[key] * weight

    suggestions = _generate_quality_suggestions(
        dimension_scores=dimension_scores,
        profile=profile,
        risk_items=risk_items,
    )

    return {
        "overall": _clamp(total),
        "dimensions": dimension_scores,
        "weights": weights,
        "suggestions": suggestions,
    }