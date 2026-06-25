from typing import Any, Dict

from application.harness.trace_logger import TraceLogger
from infrastructure.strategy.content_strategy import build_query_plan
from infrastructure.tools.keyword_extractor import extract_keywords


def rewrite_node(state: Dict[str, Any]) -> Dict[str, Any]:
    content = state.get("raw_content", "")
    platform = state.get("detected_platform") or state.get("platform") or "xiaohongshu"
    content_type = state.get("detected_content_type") or state.get("content_type") or "general"
    task_type = state.get("task_type") or "review_and_rewrite"
    target_audience = state.get("target_audience") or ""

    keywords = extract_keywords(content)

    queries = build_query_plan(
        content=content,
        platform=platform,
        content_type=content_type,
        task_type=task_type,
        target_audience=target_audience,
        keywords=keywords,
    )

    state["keywords"] = keywords
    state["rewritten_queries"] = queries

    TraceLogger.add_trace(
        state,
        "rewrite_node",
        "查询改写完成",
        query_count=len(queries),
        keywords=keywords[:8],
    )

    return state