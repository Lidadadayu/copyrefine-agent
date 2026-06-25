from typing import Any, Dict

from application.harness.trace_logger import TraceLogger
from infrastructure.strategy.content_strategy import (
    build_content_profile,
    get_platform_strategy,
    infer_content_type,
    infer_task_type,
    normalize_platform,
)


STYLE_SIGNALS = [
    "我的风格",
    "历史风格",
    "像之前一样",
    "保持风格",
    "参考之前",
    "延续风格",
    "按照我之前",
]


def intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    content = state.get("raw_content", "")

    platform = normalize_platform(state.get("platform"))
    content_type = infer_content_type(content, state.get("content_type"))
    task_type = infer_task_type(content, state.get("task_type"))

    target_audience = state.get("target_audience")

    content_profile = build_content_profile(
        content=content,
        platform=platform,
        content_type=content_type,
        target_audience=target_audience,
    )

    platform_strategy = get_platform_strategy(
        platform=platform,
        content_type=content_type,
        task_type=task_type,
        profile=content_profile,
    )

    risk_sensitive = any(
        w in content
        for w in [
            "绝对",
            "无副作用",
            "7天",
            "稳赚",
            "保过",
            "全网最低",
            "闭眼入",
            "必须入手",
            "错过后悔",
            "100%",
            "没有风险",
        ]
    )

    explicit_style_request = any(signal in content for signal in STYLE_SIGNALS)

    # 改写和标题生成默认需要历史风格参考。
    # review_only 只有用户明确要求时才检索历史风格。
    need_history = explicit_style_request or task_type in ["review_and_rewrite", "title_generation"]

    state.update(
        {
            "intent": task_type,
            "detected_platform": platform,
            "detected_content_type": content_type,
            "task_type": task_type,
            "risk_sensitive": risk_sensitive,
            "need_retrieval": True,
            "need_rewrite": task_type != "review_only",
            "need_history": need_history,
            "explicit_style_request": explicit_style_request,
            "content_profile": content_profile,
            "platform_strategy": platform_strategy,
            "rewrite_constraints": platform_strategy.get("rewrite_constraints", []),
        }
    )

    TraceLogger.add_trace(
        state,
        "intent_node",
        "意图识别完成",
        intent=task_type,
        platform=platform,
        content_type=content_type,
        risk_sensitive=risk_sensitive,
        need_history=need_history,
        explicit_style_request=explicit_style_request,
    )

    return state