from typing import Any, Dict, List, Optional

from application.harness.trace_logger import TraceLogger
from config.settings import get_settings
from infrastructure.llm.llm_client import LLMClient
from infrastructure.prompting.prompt_store import get_prompt_template_text
from infrastructure.tools.title_scorer import score_title


PLATFORM_NAME_MAP = {
    "xiaohongshu": "小红书",
    "wechat": "公众号",
    "zhihu": "知乎",
    "short_video": "短视频",
}

CONTENT_TYPE_NAME_MAP = {
    "product_review": "产品种草",
    "knowledge_post": "知识科普",
    "course_promotion": "课程宣传",
    "activity_promotion": "活动推广",
    "general": "通用内容",
}

REWRITE_INTENSITY_LABELS = {
    "light": "轻度优化：尽量保留原文，只做风险弱化和表达润色",
    "medium": "中度改写：优化表达和结构，保留核心信息",
    "deep": "深度重写：重新组织语言，更贴合平台风格",
}

EXPRESSION_STRENGTH_LABELS = {
    "restrained": "克制自然：表达稳妥、不过度营销",
    "moderate": "适度营销：增强吸引力，但保持边界清晰",
    "strong": "强吸引但合规：更有转化感，避免绝对化和虚假承诺",
}

VERSION_DESCRIPTIONS = {
    "safe_compliance": "适合直接发布，风险最低。",
    "conversion_enhanced": "更有吸引力，保留营销感，但避免绝对化表达。",
}

RISK_REPLACEMENTS = {
    "绝对安全": "使用体验相对温和",
    "绝对": "相对",
    "无副作用": "使用感受因人而异，建议结合自身情况判断",
    "7天见效": "坚持使用后可能逐步感受到变化",
    "100%": "较大程度",
    "稳赚": "存在不确定性，需要理性判断",
    "保过": "有助于提升准备效率",
    "全网最低": "价格相对有优势",
    "大家快冲": "可以根据自己的需求理性选择",
    "快冲": "可以根据自己的需求理性选择",
    "错过后悔": "感兴趣可以进一步了解",
}


def _safe_rewrite(content: str) -> str:
    new = content
    for source, target in RISK_REPLACEMENTS.items():
        new = new.replace(source, target)
    return new.strip()


def _generate_titles(platform: str, strength: str) -> List[str]:
    if platform == "zhihu":
        return [
            "如何理性看待这类产品的使用体验？",
            "这类产品是否值得尝试？先看适用场景和边界",
            "从真实需求出发，聊聊这类产品怎么选",
        ]
    if platform == "wechat":
        return [
            "使用前先了解：体验、适用场景与注意事项",
            "理性选择这类产品，需要关注哪些细节？",
            "一篇讲清：适用人群、体验反馈与选择建议",
        ]
    if platform == "short_video":
        return [
            "先别急着下单，看看这几个真实体验点",
            "适合谁、不适合谁？这类产品先看场景",
            "想尝试这类产品，先把需求想清楚",
        ]

    if strength == "strong":
        return [
            "想试这类产品？先看真实体验和适用边界",
            "被种草前先看这几点，选择更稳妥",
            "这份体验分享，适合正在犹豫的你",
        ]
    if strength == "restrained":
        return [
            "这类产品的真实体验和注意事项",
            "使用前先了解：适合谁、怎么选",
            "一次相对克制的体验分享",
        ]
    return [
        "这份体验分享，适合正在犹豫的你",
        "使用前先看看：真实体验和注意事项",
        "别急着下单，先了解这些细节",
    ]


def _format_control_note(state: Dict[str, Any]) -> str:
    intensity = state.get("rewrite_intensity") or "medium"
    strength = state.get("expression_strength") or "moderate"
    return (
        f"{REWRITE_INTENSITY_LABELS.get(intensity, REWRITE_INTENSITY_LABELS['medium'])}；"
        f"{EXPRESSION_STRENGTH_LABELS.get(strength, EXPRESSION_STRENGTH_LABELS['moderate'])}"
    )


def _body_by_intensity(base: str, title: str, version_type: str, state: Dict[str, Any]) -> str:
    intensity = state.get("rewrite_intensity") or "medium"
    strength = state.get("expression_strength") or "moderate"
    refine = state.get("refine_instruction") or ""
    previous = state.get("previous_output") or ""

    if version_type == "safe_compliance":
        if intensity == "light":
            body = (
                f"{base}\n\n"
                "补充说明：以上内容更适合作为个人体验参考，实际感受会因使用场景和个人情况不同而变化。"
            )
        elif intensity == "deep":
            body = (
                f"{title}\n\n"
                "这类产品更适合已经有明确需求、愿意结合自身情况做判断的人。我的体验重点不是承诺效果，"
                "而是把适用场景、使用感受和需要注意的地方说清楚。\n\n"
                f"{base}\n\n"
                "建议大家先明确自己的需求，再结合预算、使用频率和实际反馈做选择。"
            )
        else:
            body = (
                f"先说结论：这类产品可以作为一个参考选择，但不建议只看单一宣传点就下判断。\n\n"
                f"{base}\n\n"
                "更稳妥的做法是结合自己的实际情况、使用场景和可接受范围，再决定是否尝试。"
            )
    else:
        hook = "如果你也在考虑这类产品，可以先看这几个真实体验点。"
        if strength == "strong":
            hook = "被种草前先别急，真正值得看的其实是这几个细节。"
        elif strength == "restrained":
            hook = "这里整理几个相对客观的体验点，供你做参考。"

        if intensity == "light":
            body = f"{hook}\n\n{base}\n\n整体建议：感兴趣可以进一步了解，但选择前仍要看自身需求。"
        elif intensity == "deep":
            body = (
                f"{hook}\n\n"
                "1. 先看适用场景：它更适合有明确需求的人，而不是所有人都必须入手。\n"
                "2. 再看体验边界：不同人的使用感受会有差异，不建议把它理解成确定承诺。\n"
                "3. 最后看决策成本：如果预算和需求都匹配，可以把它作为一个备选。\n\n"
                f"{base}"
            )
        else:
            body = (
                f"{hook}\n\n"
                f"{base}\n\n"
                "我会更建议把它当作一个可参考的选择：有需求可以了解，没必要被单一卖点带着走。"
            )

    if refine:
        body += f"\n\n本轮已按你的要求调整：{refine}"
    if previous:
        body += "\n\n本轮是在上一轮输出基础上继续优化。"
    return body.strip()


def _fallback_optimize(state: Dict[str, Any]) -> Dict[str, Any]:
    content = state.get("raw_content", "")
    platform = state.get("detected_platform") or state.get("platform") or "xiaohongshu"
    task_type = state.get("task_type") or "review_and_rewrite"
    preference_note = state.get("user_preference") or ""
    refine_note = state.get("refine_instruction") or ""
    strength = state.get("expression_strength") or "moderate"

    titles = _generate_titles(platform, strength)
    state["title_score_details"] = [score_title(t, platform)["score"] for t in titles]
    state["title_suggestions"] = titles[:3]

    if task_type == "title_generation":
        state["rewritten_versions"] = []
        TraceLogger.add_trace(
            state,
            "optimize_node",
            "标题生成完成：使用规则兜底",
            title_count=len(titles),
            llm_used=False,
        )
        return state

    safe_body = _safe_rewrite(content)
    control_note = _format_control_note(state)
    base_score = int(state.get("score", 75) or 75)

    versions = [
        {
            "version_type": "safe_compliance",
            "title": titles[0],
            "body": _body_by_intensity(safe_body, titles[0], "safe_compliance", state),
            "score": min(96, max(base_score + 16, 82)),
            "notes": (
                f"{VERSION_DESCRIPTIONS['safe_compliance']} {control_note}"
                + (f" 偏好：{preference_note}" if preference_note else "")
                + (f" 修改要求：{refine_note}" if refine_note else "")
            ),
        },
        {
            "version_type": "conversion_enhanced",
            "title": titles[1],
            "body": _body_by_intensity(safe_body, titles[1], "conversion_enhanced", state),
            "score": min(95, max(base_score + 12, 80)),
            "notes": (
                f"{VERSION_DESCRIPTIONS['conversion_enhanced']} {control_note}"
                + (f" 偏好：{preference_note}" if preference_note else "")
                + (f" 修改要求：{refine_note}" if refine_note else "")
            ),
        },
    ]

    state["rewritten_versions"] = versions

    TraceLogger.add_trace(
        state,
        "optimize_node",
        "内容优化完成：生成两个推荐版本",
        version_count=len(versions),
        rewrite_intensity=state.get("rewrite_intensity"),
        expression_strength=state.get("expression_strength"),
        llm_used=False,
    )

    return state


DEFAULT_CONTENT_OPTIMIZER_SYSTEM_PROMPT = """
你是一个发布前内容质检与改写助手。你必须输出安全、自然、适合平台的中文文案。
要求：
1. 只生成两个改写版本：稳妥合规版、转化增强版。
2. 不保留绝对化承诺、健康功效承诺、虚假保障、强诱导购买或焦虑营销表达。
3. 转化增强版可以更吸引人，但必须合规，不能使用极限词或确定性承诺。
4. 如果用户偏好或修改意见与合规要求冲突，优先满足合规要求。
5. 必须只输出 JSON，不要输出 Markdown 或解释文字。
""".strip()


def _build_llm_prompt(state: Dict[str, Any]) -> List[Dict[str, str]]:
    raw_content = state.get("raw_content", "")
    original_content = state.get("original_content") or raw_content
    platform = state.get("detected_platform") or state.get("platform") or "xiaohongshu"
    content_type = state.get("detected_content_type") or state.get("content_type") or "general"
    task_type = state.get("task_type") or "review_and_rewrite"
    target_audience = state.get("target_audience") or "普通用户"
    intensity = state.get("rewrite_intensity") or "medium"
    strength = state.get("expression_strength") or "moderate"

    risk_items = state.get("risk_report", {}).get("items", [])
    risk_text = "\n".join(
        f"- 命中「{item.get('text')}」：{item.get('suggestion')}"
        for item in risk_items
    )

    evidence = state.get("evidence_pack", {})
    style_profile = evidence.get("style_profile", {}) or state.get("style_profile", {}) or {}
    style_summary = style_profile.get("style_summary", "暂无历史风格画像")
    style_constraints = style_profile.get("style_constraints", [])
    style_constraints_text = "\n".join(f"- {c}" for c in style_constraints) if style_constraints else "无"
    user_preference = state.get("user_preference") or evidence.get("user_preference") or "无"
    refine_instruction = state.get("refine_instruction") or evidence.get("refine_instruction") or "无"
    previous_output = state.get("previous_output") or "无"
    rules = evidence.get("top_rules", [])
    cases = evidence.get("similar_cases", [])
    managed_prompt_text = get_prompt_template_text("content_optimizer", "")

    rules_text = "\n".join(f"- {r}" for r in rules[:5]) if rules else "无"
    cases_text = "\n".join(
        f"- 标题：{c.get('title', '')}；原因：{c.get('reason', '')}"
        for c in cases[:3]
    ) if cases else "无"

    system_prompt = get_prompt_template_text(
        "content_optimizer_system",
        DEFAULT_CONTENT_OPTIMIZER_SYSTEM_PROMPT,
    )

    user_prompt = f"""
原始文案：
{original_content}

当前要继续修改的文案：
{raw_content}

任务信息：
- 平台：{PLATFORM_NAME_MAP.get(platform, platform)}
- 内容类型：{CONTENT_TYPE_NAME_MAP.get(content_type, content_type)}
- 任务类型：{task_type}
- 目标受众：{target_audience}
- 改写强度：{REWRITE_INTENSITY_LABELS.get(intensity, REWRITE_INTENSITY_LABELS['medium'])}
- 表达力度：{EXPRESSION_STRENGTH_LABELS.get(strength, EXPRESSION_STRENGTH_LABELS['moderate'])}
- 当前风险等级：{state.get("risk_level")}
- 当前综合评分：{state.get("score")}/100

已识别风险：
{risk_text or "无"}

平台规则：
{rules_text}

相似案例：
{cases_text}

历史风格画像：
{style_summary}

风格复用约束：
{style_constraints_text}

用户偏好记忆：
{user_preference}

上一轮输出摘要：
{previous_output}

本轮继续修改意见：
{refine_instruction}

Prompt 管理模板补充要求：
{managed_prompt_text or '无'}

请输出 JSON，格式必须如下：
{{
  "title_suggestions": ["标题1", "标题2", "标题3"],
  "rewritten_versions": [
    {{
      "version_type": "safe_compliance",
      "title": "稳妥合规版标题",
      "body": "稳妥合规版正文",
      "score": 85,
      "notes": "适合直接发布，风险最低。"
    }},
    {{
      "version_type": "conversion_enhanced",
      "title": "转化增强版标题",
      "body": "转化增强版正文",
      "score": 88,
      "notes": "更有吸引力，保留营销感，但避免绝对化表达。"
    }}
  ]
}}

特殊要求：
- 如果 task_type 是 title_generation，则 rewritten_versions 返回空数组。
- 如果 task_type 是 review_and_rewrite，则必须只生成 2 个 rewritten_versions。
- 标题和正文必须是中文。
- score 必须是 0 到 100 的整数。
""".strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _normalize_version_type(raw_type: str, index: int) -> str:
    if raw_type in {"safe_compliance", "稳妥合规版", "safe_version"} or index == 0:
        return "safe_compliance"
    return "conversion_enhanced"


def _validate_llm_result(data: Optional[Dict[str, Any]], task_type: str) -> Optional[Dict[str, Any]]:
    if not data:
        return None

    titles = data.get("title_suggestions")
    versions = data.get("rewritten_versions")

    if not isinstance(titles, list) or not titles:
        return None

    clean_titles = [str(t).strip() for t in titles if str(t).strip()]
    if not clean_titles:
        return None

    clean_versions = []

    if task_type != "title_generation":
        if not isinstance(versions, list) or not versions:
            return None

        for index, item in enumerate(versions[:2]):
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()
            body = str(item.get("body", "")).strip()

            if not title or not body:
                continue

            try:
                score = int(item.get("score", 80))
            except Exception:
                score = 80

            version_type = _normalize_version_type(str(item.get("version_type", "")), index)
            clean_versions.append(
                {
                    "version_type": version_type,
                    "title": title,
                    "body": body,
                    "score": max(0, min(100, score)),
                    "notes": str(item.get("notes") or VERSION_DESCRIPTIONS[version_type]),
                }
            )

        if len(clean_versions) != 2:
            return None

    return {
        "title_suggestions": clean_titles[:3],
        "rewritten_versions": clean_versions,
    }


def _llm_optimize(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    task_type = state.get("task_type") or "review_and_rewrite"

    client = LLMClient()
    messages = _build_llm_prompt(state)

    text = client.chat(messages)
    data = client.extract_json(text)

    validated = _validate_llm_result(data, task_type)
    if not validated:
        return None

    state["title_suggestions"] = validated["title_suggestions"]
    state["title_score_details"] = [
        score_title(t, state.get("platform") or "xiaohongshu")["score"]
        for t in state["title_suggestions"]
    ]
    state["rewritten_versions"] = validated["rewritten_versions"]

    TraceLogger.add_trace(
        state,
        "optimize_node",
        "内容优化完成：使用 LLM 生成两个推荐版本",
        version_count=len(state["rewritten_versions"]),
        title_count=len(state["title_suggestions"]),
        rewrite_intensity=state.get("rewrite_intensity"),
        expression_strength=state.get("expression_strength"),
        llm_used=True,
    )

    return state


def optimize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()

    if not settings.enable_llm_optimize:
        return _fallback_optimize(state)

    try:
        llm_state = _llm_optimize(state)
        if llm_state is not None:
            return llm_state

        TraceLogger.add_trace(
            state,
            "optimize_node",
            "LLM 输出格式不符合要求，已回退到规则优化",
            llm_used=False,
        )
        return _fallback_optimize(state)

    except Exception as exc:
        TraceLogger.add_trace(
            state,
            "optimize_node",
            "LLM 调用失败，已回退到规则优化",
            error=str(exc),
            llm_used=False,
        )
        return _fallback_optimize(state)
