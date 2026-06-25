from typing import Any, Dict, List

from application.harness.trace_logger import TraceLogger


def route_node(state: Dict[str, Any]) -> Dict[str, Any]:
    task_type = state.get("task_type") or "review_and_rewrite"
    risk_sensitive = bool(state.get("risk_sensitive"))
    need_history = bool(state.get("need_history"))

    routes: List[str] = []

    # 平台规则是所有任务都需要的基础依据
    routes.append("platform_rules")

    # 风险表达库：风险敏感内容、质检任务、完整改写任务都需要
    if risk_sensitive or task_type in ["review_only", "review_and_rewrite"]:
        routes.append("risk_expressions")

    # 案例库：标题生成和改写任务需要参考案例
    if task_type in ["title_generation", "review_and_rewrite"]:
        routes.append("content_cases")

    # 历史库：用户明确要求风格复用时才检索
    if need_history:
        routes.append("user_history")

    # 兜底：至少保留三路核心召回
    if "risk_expressions" not in routes:
        routes.append("risk_expressions")

    if "content_cases" not in routes and task_type != "review_only":
        routes.append("content_cases")

    state["retrieval_routes"] = routes

    TraceLogger.add_trace(
        state,
        "route_node",
        "查询路由完成",
        routes=routes,
        task_type=task_type,
    )

    return state