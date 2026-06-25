from typing import Any, Dict, List

from application.harness.trace_logger import TraceLogger
from infrastructure.tools.risk_matcher import match_risks


def _analyze_structure(content: str, platform: str) -> Dict[str, Any]:
    problems: List[str] = []

    text = content.strip()

    if len(text) < 30:
        problems.append("正文较短，缺少使用场景或具体说明。")

    if "。" not in text and "\n" not in text and len(text) > 40:
        problems.append("句子结构较单一，可以拆分为开头、正文、结尾。")

    if platform == "xiaohongshu":
        if not any(word in text for word in ["我", "体验", "使用", "场景", "适合", "建议"]):
            problems.append("小红书文案缺少个人体验或场景化表达。")

    if platform == "zhihu":
        if not any(word in text for word in ["原因", "因为", "适合", "不适合", "因素", "分析"]):
            problems.append("知乎内容缺少分析依据或判断边界。")

    if platform == "wechat":
        if len(text) < 80:
            problems.append("公众号内容偏短，可以补充背景、分点说明和总结建议。")

    if platform == "short_video":
        if len(text) > 260:
            problems.append("短视频文案偏长，可以压缩为更适合口播的表达。")

    return {
        "problems": problems,
        "problem_count": len(problems),
    }


def _score_risks(risk_items: List[Dict[str, Any]], structure_report: Dict[str, Any]) -> int:
    score = 100

    for item in risk_items:
        severity = item.get("severity", "low")

        if severity == "high":
            score -= 20
        elif severity == "medium":
            score -= 10
        else:
            score -= 5

    score -= int(structure_report.get("problem_count", 0)) * 4

    return max(0, min(100, score))


def _risk_level(risk_items: List[Dict[str, Any]], score: int) -> str:
    has_high = any(item.get("severity") == "high" for item in risk_items)
    medium_count = sum(1 for item in risk_items if item.get("severity") == "medium")

    if has_high or score < 60:
        return "high"

    if medium_count >= 2 or score < 80:
        return "medium"

    return "low"


def risk_node(state: Dict[str, Any]) -> Dict[str, Any]:
    content = state.get("raw_content", "")
    platform = state.get("detected_platform") or state.get("platform") or "xiaohongshu"

    risk_items = match_risks(content)
    structure_report = _analyze_structure(content, platform)

    score = _score_risks(risk_items, structure_report)
    risk_level = _risk_level(risk_items, score)

    state["risk_report"] = {
        "items": risk_items,
        "risk_count": len(risk_items),
    }
    state["structure_report"] = structure_report
    state["score"] = score
    state["risk_level"] = risk_level

    TraceLogger.add_trace(
        state,
        "risk_node",
        "风险检测完成",
        risk_count=len(risk_items),
        risk_level=risk_level,
        score=score,
    )

    return state