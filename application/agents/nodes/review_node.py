from typing import Any, Dict

from application.harness.trace_logger import TraceLogger
from infrastructure.tools.quality_scorer import compute_quality_scores
from infrastructure.tools.version_decider import decide_versions


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
    "recruitment": "招聘文案",
    "brand_story": "品牌介绍",
    "video_script": "短视频脚本",
    "live_script": "直播口播",
    "user_case": "用户案例",
    "general": "通用内容",
}

TASK_TYPE_NAME_MAP = {
    "review_and_rewrite": "发布前质检 + 改写",
    "review_only": "只做风险质检",
    "title_generation": "标题生成",
}

RISK_LEVEL_NAME_MAP = {
    "high": "高风险",
    "medium": "中风险",
    "low": "低风险",
    "unknown": "未知",
}


def _zh_platform(value: str) -> str:
    return PLATFORM_NAME_MAP.get(value, value or "未知平台")


def _zh_content_type(value: str) -> str:
    return CONTENT_TYPE_NAME_MAP.get(value, value or "未知类型")


def _zh_task_type(value: str) -> str:
    return TASK_TYPE_NAME_MAP.get(value, value or "未知任务")


def _zh_risk_level(value: str) -> str:
    return RISK_LEVEL_NAME_MAP.get(value, value or "未知")


def _format_list(items: list[str]) -> str:
    if not items:
        return "无"
    return "、".join(items)


def review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    task_type = state.get("task_type") or "review_and_rewrite"

    platform = state.get("detected_platform") or state.get("platform") or ""
    content_type = state.get("detected_content_type") or state.get("content_type") or ""
    risk_level = state.get("risk_level") or "unknown"

    versions = state.get("rewritten_versions", []) or []

    processed_versions, rewrite_comparison, version_decision_pack = decide_versions(
        original_content=state.get("raw_content", ""),
        versions=versions,
        platform=platform,
        content_type=content_type,
        target_audience=state.get("target_audience"),
    )

    state["rewritten_versions"] = processed_versions
    state["rewrite_comparison"] = rewrite_comparison
    state["version_decision_pack"] = version_decision_pack
    state["recommended_version"] = version_decision_pack.get("recommended_version")

    quality_scores = compute_quality_scores(state)
    state["quality_scores"] = quality_scores

    evidence_pack = state.get("evidence_pack", {})
    evidence_pack["quality_scores"] = quality_scores
    evidence_pack["rewrite_comparison"] = rewrite_comparison
    evidence_pack["version_decision_pack"] = version_decision_pack
    evidence_pack["recommended_version"] = version_decision_pack.get("recommended_version")
    state["evidence_pack"] = evidence_pack

    risk_items = state.get("risk_report", {}).get("items", [])
    problem_lines = []

    for r in risk_items:
        problem_lines.append(f"- 命中「{r['text']}」：{r['suggestion']}")

    if not problem_lines:
        problem_lines.append("- 未发现明显高风险表达。")

    top_rules = evidence_pack.get("top_rules", [])[:3]
    rules_text = "\n".join("- " + r for r in top_rules) if top_rules else "- 暂无匹配规则"

    structure_problems = state.get("structure_report", {}).get("problems", [])
    structure_text = "\n".join("- " + p for p in structure_problems) if structure_problems else "- 结构完整性基本正常。"

    title_suggestions = state.get("title_suggestions", [])
    title_text = "\n".join(f"- {t}" for t in title_suggestions) if title_suggestions else "- 本次未生成标题建议。"

    dimensions = quality_scores.get("dimensions", {})
    quality_suggestions = quality_scores.get("suggestions", [])

    quality_text = f"""
### 多维质量评分
- 风险安全分：{dimensions.get("risk_safety", 0)}/100
- 平台适配分：{dimensions.get("platform_fit", 0)}/100
- 结构完整分：{dimensions.get("structure", 0)}/100
- 证据充分分：{dimensions.get("evidence", 0)}/100
- 标题质量分：{dimensions.get("title", 0)}/100
- 可读性分：{dimensions.get("readability", 0)}/100

### 优化建议
{chr(10).join("- " + s for s in quality_suggestions)}
""".strip()

    if rewrite_comparison:
        comparison_lines = []

        for item in rewrite_comparison:
            comparison_lines.append(
                f"- {item.get('version_type')}：移除风险词 {_format_list(item.get('removed_risk_terms', []))}；"
                f"残留风险词 {_format_list(item.get('remaining_risk_terms', []))}；"
                f"新增风险词 {_format_list(item.get('new_risk_terms', []))}；"
                f"发布建议：{item.get('publish_suggestion')}"
            )

        comparison_text = "\n".join(comparison_lines)
    else:
        comparison_text = "- 本次没有正文改写版本，因此不生成改写对比。"

    recommended = version_decision_pack.get("recommended_version")

    if recommended:
        recommended_text = f"""
### 推荐版本
- 推荐版本：{recommended.get("version_type")}
- 决策分：{recommended.get("decision_score")}/100
- 发布状态：{recommended.get("publish_status")}
- 是否自动修复：{"是" if recommended.get("auto_repaired") else "否"}
- 推荐理由：{recommended.get("publish_suggestion")}
""".strip()
    else:
        recommended_text = """
### 推荐版本
- 本次没有正文改写版本，因此不生成推荐版本。
""".strip()

    if version_decision_pack.get("auto_repair_records"):
        repair_lines = []
        for record in version_decision_pack.get("auto_repair_records", []):
            repair_lines.append(
                f"- {record.get('version_type')}：自动弱化 {_format_list(record.get('changed_terms', []))}"
            )

        repair_text = f"""
### 自动安全修复
{chr(10).join(repair_lines)}
""".strip()
    else:
        repair_text = """
### 自动安全修复
- 未触发自动安全修复。
""".strip()

    comparison_report = f"""
### 改写版本对比
{comparison_text}

{recommended_text}

{repair_text}
""".strip()

    if task_type == "review_only":
        action_text = """
### 处理说明
- 本次任务类型为“只做风险质检”。
- 系统已跳过内容改写节点，仅输出风险诊断、结构建议和检索依据。
""".strip()

    elif task_type == "title_generation":
        action_text = f"""
### 标题建议
{title_text}

### 处理说明
- 本次任务类型为“标题生成”。
- 系统重点生成标题建议，不生成完整正文改写版本。
- 标题仍需避免绝对化承诺、强诱导和夸大表达。
""".strip()

    else:
        action_text = """
### 改写策略
- 弱化绝对化表达、效果承诺和强诱导表述。
- 增加真实体验、适用场景、使用边界和理性选择提示。
- 保持平台语气，但不做违规绕审。
""".strip()

    final_report = f"""
## 发布前质检报告

**平台**：{_zh_platform(platform)}
**内容类型**：{_zh_content_type(content_type)}
**任务类型**：{_zh_task_type(task_type)}
**风险等级**：{_zh_risk_level(risk_level)}
**综合评分**：{state.get('score')}/100

### 主要风险
{chr(10).join(problem_lines)}

### 结构建议
{structure_text}

### 检索依据
{rules_text}

{quality_text}

{comparison_report}

{action_text}
""".strip()

    state["final_report"] = final_report

    TraceLogger.add_trace(
        state,
        "review_node",
        "审核保护完成",
        task_type=task_type,
        overall_quality=quality_scores.get("overall"),
        comparison_count=len(rewrite_comparison),
        recommended_version=recommended.get("version_type") if recommended else None,
        auto_repair_count=len(version_decision_pack.get("auto_repair_records", [])),
    )

    return state