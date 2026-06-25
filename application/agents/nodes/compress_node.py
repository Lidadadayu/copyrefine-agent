from typing import Any, Dict

from application.harness.trace_logger import TraceLogger
from infrastructure.tools.style_profiler import build_style_profile


def compress_node(state: Dict[str, Any]) -> Dict[str, Any]:
    profile = state.get("content_profile", {})
    strategy = state.get("platform_strategy", {})

    top_rules = [d.get("text", "") for d in state.get("retrieved_rules", [])[:5]]
    top_risks = [d.get("text", "") for d in state.get("retrieved_risks", [])[:8]]

    similar_cases = [
        {
            "title": d.get("title", ""),
            "reason": d.get("reason", ""),
            "body": d.get("body", "")[:160],
            "platform": d.get("platform", ""),
            "content_type": d.get("content_type", ""),
        }
        for d in state.get("retrieved_cases", [])[:4]
    ]

    history_style = [
        {
            "title": d.get("title", ""),
            "body": d.get("body", "")[:160],
            "style": d.get("style", ""),
            "platform": d.get("platform", ""),
            "content_type": d.get("content_type", ""),
        }
        for d in state.get("retrieved_history", [])[:4]
    ]

    style_profile = build_style_profile(
        history_docs=history_style,
        current_content=state.get("raw_content", ""),
    )

    decision_notes = []

    if profile.get("has_strong_marketing"):
        decision_notes.append("原文存在较强营销倾向，改写时需要弱化催促购买语气。")

    if not profile.get("has_scene"):
        decision_notes.append("原文缺少具体使用场景，建议补充场景化表达。")

    if not profile.get("has_audience"):
        decision_notes.append("原文缺少目标人群说明，建议补充适用人群和边界。")

    if not profile.get("has_evidence"):
        decision_notes.append("原文缺少依据或原因说明，建议补充可信支撑。")

    if style_profile.get("has_history"):
        decision_notes.append("系统已检索用户历史内容，并生成历史风格画像用于个性化改写。")
    else:
        decision_notes.append("历史内容不足，系统将使用平台默认风格策略。")

    if state.get("user_preference"):
        decision_notes.append(f"User preference memory: {state.get('user_preference')}")

    if state.get("refine_instruction"):
        decision_notes.append(f"Refine instruction: {state.get('refine_instruction')}")

    if not decision_notes:
        decision_notes.append("原文结构基础较完整，重点进行平台风格和风险表达优化。")

    evidence_pack = {
        "task_summary": (
            f"面向{strategy.get('platform_name', state.get('detected_platform'))}平台的"
            f"{strategy.get('content_type_name', state.get('detected_content_type'))}内容"
            f"执行{strategy.get('task_type_name', state.get('task_type'))}。"
        ),
        "content_profile": profile,
        "style_profile": style_profile,
        "strategy_pack": {
            "tone": strategy.get("tone", ""),
            "title_style": strategy.get("title_style", ""),
            "recommended_structure": strategy.get("recommended_structure", []),
            "platform_avoid": strategy.get("platform_avoid", []),
            "platform_rewrite_focus": strategy.get("platform_rewrite_focus", []),
            "content_core_goal": strategy.get("content_core_goal", ""),
            "content_must_have": strategy.get("content_must_have", []),
            "content_risk_focus": strategy.get("content_risk_focus", []),
            "output_focus": strategy.get("output_focus", ""),
        },
        "top_rules": top_rules,
        "top_risk_expressions": top_risks,
        "similar_cases": similar_cases,
        "history_style": history_style,
        "rewrite_constraints": state.get("rewrite_constraints", []),
        "style_constraints": style_profile.get("style_constraints", []),
        "user_preference": state.get("user_preference", ""),
        "refine_instruction": state.get("refine_instruction", ""),
        "decision_notes": decision_notes,
    }

    state["style_profile"] = style_profile
    state["evidence_pack"] = evidence_pack

    TraceLogger.add_trace(
        state,
        "compress_node",
        "上下文压缩完成",
        rule_count=len(top_rules),
        risk_rule_count=len(top_risks),
        case_count=len(similar_cases),
        history_count=len(history_style),
        style_history_used=style_profile.get("has_history", False),
    )

    return state
