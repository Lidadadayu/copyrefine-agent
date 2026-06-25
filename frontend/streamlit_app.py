from __future__ import annotations

import html
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st


# =============================
# 基础配置
# =============================

st.set_page_config(
    page_title="ContentPilot 文案改写工作台",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


API_PREFIX = "/api/v1"
DEFAULT_API_BASE = os.getenv("CONTENTPILOT_API_BASE_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 90

PLATFORM_OPTIONS: Dict[str, str] = {
    "xiaohongshu": "小红书",
    "wechat": "公众号",
    "zhihu": "知乎",
    "short_video": "短视频",
}

CONTENT_TYPE_OPTIONS: Dict[str, str] = {
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

TASK_TYPE_OPTIONS: Dict[str, str] = {
    "review_and_rewrite": "发布前质检 + 改写",
    "review_only": "只做风险质检",
    "title_generation": "标题生成",
}

REWRITE_INTENSITY_OPTIONS: Dict[str, str] = {
    "light": "轻度优化：尽量保留原文",
    "medium": "中度改写：优化表达和结构",
    "deep": "深度重写：重新组织语言",
}

EXPRESSION_STRENGTH_OPTIONS: Dict[str, str] = {
    "restrained": "克制自然",
    "moderate": "适度营销",
    "strong": "强吸引但合规",
}

VERSION_TYPE_LABELS: Dict[str, str] = {
    "safe_compliance": "稳妥合规版",
    "conversion_enhanced": "转化增强版",
    "safe_version": "稳妥合规版",
    "platform_style_version": "转化增强版",
}

VERSION_TYPE_DESCRIPTIONS: Dict[str, str] = {
    "safe_compliance": "适合直接发布，风险最低。",
    "conversion_enhanced": "更有吸引力，保留营销感，但避免绝对化表达。",
    "safe_version": "适合直接发布，风险最低。",
    "platform_style_version": "更有吸引力，保留营销感，但避免绝对化表达。",
}

RISK_LEVEL_LABELS: Dict[str, str] = {
    "high": "高风险",
    "medium": "中风险",
    "low": "低风险",
    "unknown": "未知",
}

RISK_BADGE_CLASS: Dict[str, str] = {
    "high": "risk-high",
    "medium": "risk-medium",
    "low": "risk-low",
    "unknown": "risk-unknown",
}

SAMPLE_CONTENTS: Dict[str, str] = {
    "高风险种草": "这款产品7天见效，绝对安全，无副作用，大家快冲，错过真的会后悔。",
    "知识科普": "很多人不知道为什么熬夜后皮肤状态会变差，今天用简单的话讲清楚几个常见原因和改善建议。",
    "课程宣传": "零基础也能快速逆袭，跟着老师学，7天掌握核心技巧，考试保过，名额有限赶紧报名。",
}


# =============================
# 样式
# =============================

st.markdown(
    """
    <style>
    :root {
        --cp-bg: #f7f8fb;
        --cp-card: #ffffff;
        --cp-card-strong: #eef7f5;
        --cp-line: #d9e2ec;
        --cp-text: #1f2937;
        --cp-muted: #64748b;
        --cp-accent: #0f766e;
        --cp-accent-dark: #134e4a;
        --cp-success: #15803d;
        --cp-warning: #b45309;
        --cp-danger: #be123c;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #f7f8fb 0%, #eef7f5 100%);
        color: var(--cp-text);
    }

    .block-container {
        max-width: 100% !important;
        padding: 0.9rem 1.05rem 0.8rem 1.05rem !important;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"], footer {
        visibility: hidden;
        height: 0;
    }

    div[data-testid="stVerticalBlock"] { gap: 0.62rem; }
    div[data-testid="column"] { padding-left: 0.25rem; padding-right: 0.25rem; }

    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.72rem 1rem;
        border: 1px solid var(--cp-line);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
        margin-bottom: 0.35rem;
    }

    .brand-title {
        font-size: 1.42rem;
        font-weight: 800;
        color: var(--cp-accent-dark);
        letter-spacing: 0.02rem;
        line-height: 1.2;
    }

    .brand-subtitle {
        font-size: 0.9rem;
        color: var(--cp-muted);
        margin-top: 0.12rem;
    }

    .topbar-tags {
        display: flex;
        gap: 0.45rem;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .tag, .soft-tag {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 0.22rem 0.55rem;
        font-size: 0.76rem;
        white-space: nowrap;
    }

    .tag {
        background: #ccfbf1;
        color: #134e4a;
        border: 1px solid #99f6e4;
        font-weight: 700;
    }

    .soft-tag {
        background: #f8fafc;
        color: #475569;
        border: 1px solid #d9e2ec;
    }

    .section-title {
        font-size: 1.02rem;
        font-weight: 800;
        color: var(--cp-accent-dark);
        margin: 0.15rem 0 0.35rem 0;
    }

    .section-hint {
        color: var(--cp-muted);
        font-size: 0.78rem;
        margin: -0.2rem 0 0.35rem 0;
    }

    .mini-card {
        border: 1px solid var(--cp-line);
        border-radius: 8px;
        padding: 0.72rem 0.82rem;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.045);
    }

    .result-card {
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        padding: 0.75rem 0.85rem;
        background: #ffffff;
        margin-bottom: 0.55rem;
    }

    .version-title {
        font-weight: 800;
        color: #134e4a;
        margin-bottom: 0.2rem;
    }

    .version-body {
        white-space: pre-wrap;
        line-height: 1.62;
        color: #1f2937;
        background: #f8fafc;
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        padding: 0.7rem;
        margin-top: 0.45rem;
    }

    .badge {
        display: inline-block;
        padding: 0.18rem 0.52rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 800;
        margin-right: 0.3rem;
        border: 1px solid transparent;
    }

    .risk-high { background: #ffe4e6; color: var(--cp-danger); border-color: #fda4af; }
    .risk-medium { background: #fef3c7; color: var(--cp-warning); border-color: #fcd34d; }
    .risk-low { background: #dcfce7; color: var(--cp-success); border-color: #86efac; }
    .risk-unknown { background: #f1f5f9; color: #475569; border-color: #cbd5e1; }

    .metric-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.42rem;
        margin-bottom: 0.55rem;
    }

    .metric-box {
        border: 1px solid var(--cp-line);
        background: #f8fafc;
        border-radius: 8px;
        padding: 0.55rem 0.6rem;
    }

    .metric-label {
        color: var(--cp-muted);
        font-size: 0.72rem;
        margin-bottom: 0.12rem;
    }

    .metric-value {
        color: var(--cp-accent-dark);
        font-size: 1.02rem;
        font-weight: 900;
    }

    .chat-bubble-user, .chat-bubble-assistant {
        border-radius: 13px;
        padding: 0.58rem 0.68rem;
        margin-bottom: 0.45rem;
        border: 1px solid var(--cp-line);
        line-height: 1.5;
        font-size: 0.88rem;
    }

    .chat-bubble-user {
        background: #ecfeff;
        border-color: #a5f3fc;
    }

    .chat-bubble-assistant {
        background: #ffffff;
    }

    .small-muted {
        color: var(--cp-muted);
        font-size: 0.78rem;
    }

    .stButton>button, .stDownloadButton>button, button[kind="primary"] {
        border-radius: 999px !important;
        font-weight: 800 !important;
    }

    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {
        border-radius: 8px !important;
    }

    div[data-testid="stExpander"] {
        border: 1px solid var(--cp-line) !important;
        border-radius: 8px !important;
        background: rgba(255, 255, 255, 0.78) !important;
    }

    div[data-testid="stTabs"] button {
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================
# Session State
# =============================


def init_session_state() -> None:
    defaults: Dict[str, Any] = {
        "api_base_url": DEFAULT_API_BASE,
        "user_id": "default_user",
        "raw_content": SAMPLE_CONTENTS["高风险种草"],
        "raw_content_input": SAMPLE_CONTENTS["高风险种草"],
        "clear_input_next": False,
        "target_audience": "",
        "platform": "xiaohongshu",
        "content_type": "product_review",
        "task_type": "review_and_rewrite",
        "rewrite_intensity": "medium",
        "expression_strength": "moderate",
        "platforms": ["xiaohongshu", "wechat"],
        "messages": [],
        "selected_version_index": 0,
        "current_result": None,
        "batch_results": [],
        "selected_batch_index": 0,
        "history_items": [],
        "health": None,
        "preference_text": "",
        "preference_editor": "",
        "last_payload": None,
        "last_error": "",
        "last_notice": "",
        "confirm_clear_history": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_session_state()

if st.session_state.get("clear_input_next"):
    st.session_state.raw_content = ""
    st.session_state.raw_content_input = ""
    st.session_state.clear_input_next = False


# =============================
# 工具函数
# =============================


def label_of(options: Dict[str, str], value: Optional[str]) -> str:
    if not value:
        return "-"
    return options.get(value, value)



def option_index(options: Dict[str, str], value: str) -> int:
    keys = list(options.keys())
    return keys.index(value) if value in keys else 0



def normalize_base_url(url: Any) -> str:
    text = str(url or DEFAULT_API_BASE).strip().rstrip("/")
    return text or DEFAULT_API_BASE



def api_url(path: str) -> str:
    base = normalize_base_url(st.session_state.api_base_url)
    return f"{base}{path}"



def parse_error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except Exception:
        return response.text[:500] or f"HTTP {response.status_code}"

    if isinstance(body, dict):
        detail = body.get("detail") or body.get("message") or body.get("error")
        if isinstance(detail, (dict, list)):
            return json.dumps(detail, ensure_ascii=False, indent=2)
        if detail:
            return str(detail)
        return json.dumps(body, ensure_ascii=False, indent=2)[:800]

    return str(body)[:800]



def request_json(method: str, path: str, payload: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any]:
    try:
        response = requests.request(
            method=method,
            url=api_url(path),
            json=payload,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return False, f"无法连接后端：{exc}"

    if not response.ok:
        return False, f"{response.status_code} {parse_error_message(response)}"

    try:
        return True, response.json()
    except ValueError:
        return True, response.text



def build_analyze_payload(raw_content: str, use_batch: bool) -> Dict[str, Any]:
    selected_platforms = list(st.session_state.get("platforms") or [])
    platform = str(st.session_state.get("platform") or "xiaohongshu")

    if use_batch and selected_platforms:
        platforms = selected_platforms
        platform = selected_platforms[0]
    else:
        platforms = []

    return {
        "raw_content": raw_content.strip(),
        "platform": platform,
        "platforms": platforms,
        "content_type": str(st.session_state.get("content_type") or "general"),
        "task_type": str(st.session_state.get("task_type") or "review_and_rewrite"),
        "target_audience": str(st.session_state.get("target_audience") or "").strip() or None,
        "rewrite_intensity": str(st.session_state.get("rewrite_intensity") or "medium"),
        "expression_strength": str(st.session_state.get("expression_strength") or "moderate"),
        "user_id": str(st.session_state.get("user_id") or "default_user").strip() or "default_user",
        "original_content": raw_content.strip(),
    }



def set_result_from_response(data: Dict[str, Any], source: str = "analyze") -> None:
    if "items" in data and isinstance(data.get("items"), list):
        items = data.get("items") or []
        st.session_state.batch_results = items
        st.session_state.selected_batch_index = 0
        st.session_state.current_result = items[0] if items else None
    else:
        st.session_state.batch_results = []
        st.session_state.selected_batch_index = 0
        st.session_state.current_result = data

    st.session_state.selected_version_index = 0
    result = st.session_state.current_result or {}
    versions = result.get("rewritten_versions") or []
    version_lines = []
    for version in versions[:2]:
        version_type = str(version.get("version_type") or "")
        label = VERSION_TYPE_LABELS.get(version_type, version_type or "推荐版本")
        version_lines.append(f"{label}：{version.get('title') or '未命名'}")

    prefix = "已按修改要求重新生成" if source == "refine" else "分析完成"
    assistant_text = (
        f"{prefix}：{label_of(PLATFORM_OPTIONS, result.get('platform'))}，"
        f"风险等级 {label_of(RISK_LEVEL_LABELS, result.get('risk_level'))}，"
        f"评分 {result.get('score', '-')}。\n"
        + ("\n".join(version_lines) if version_lines else "本轮未生成正文改写版本。")
    )
    st.session_state.messages.append({"role": "assistant", "content": assistant_text})



def load_history(limit: int = 10) -> None:
    ok, data = request_json("GET", f"{API_PREFIX}/history/tasks", params={"limit": limit})
    if ok and isinstance(data, dict):
        st.session_state.history_items = data.get("items") or []
        st.session_state.last_notice = "历史记录已刷新。"
    else:
        st.session_state.last_error = str(data)



def load_preference() -> None:
    user_id = str(st.session_state.get("user_id") or "default_user").strip() or "default_user"
    ok, data = request_json("GET", f"{API_PREFIX}/feedback/preferences/{user_id}")
    if ok and isinstance(data, dict):
        st.session_state.preference_text = str(data.get("preference_text") or "")
        st.session_state.preference_editor = st.session_state.preference_text
        st.session_state.last_notice = "用户偏好已读取。"
    else:
        st.session_state.last_error = str(data)



def save_preference(text: str) -> None:
    user_id = str(st.session_state.get("user_id") or "default_user").strip() or "default_user"
    ok, data = request_json(
        "PUT",
        f"{API_PREFIX}/feedback/preferences/{user_id}",
        payload={"user_id": user_id, "preference_text": text.strip()},
    )
    if ok:
        st.session_state.preference_text = text.strip()
        st.session_state.preference_editor = st.session_state.preference_text
        st.session_state.last_notice = "用户偏好已保存。"
    else:
        st.session_state.last_error = str(data)



def reuse_task(task_id: str) -> None:
    ok, data = request_json("GET", f"{API_PREFIX}/history/tasks/{task_id}/reuse")
    if ok and isinstance(data, dict) and data.get("payload"):
        payload = data["payload"]
        st.session_state.raw_content = payload.get("raw_content") or ""
        st.session_state.raw_content_input = st.session_state.raw_content
        st.session_state.platform = payload.get("platform") or st.session_state.platform
        st.session_state.content_type = payload.get("content_type") or st.session_state.content_type
        st.session_state.task_type = payload.get("task_type") or st.session_state.task_type
        st.session_state.user_id = payload.get("user_id") or st.session_state.user_id
        st.session_state.last_notice = "已将历史任务内容带入输入区，可直接重新分析。"
    else:
        st.session_state.last_error = str(data)


def delete_history_task(task_id: str) -> None:
    ok, data = request_json("DELETE", f"{API_PREFIX}/history/tasks/{task_id}")
    if ok:
        st.session_state.history_items = [
            item for item in st.session_state.history_items
            if item.get("task_id") != task_id
        ]
        if (st.session_state.current_result or {}).get("task_id") == task_id:
            clear_current_session()
        st.session_state.last_notice = "选中历史已删除。"
    else:
        st.session_state.last_error = str(data)


def clear_all_history() -> None:
    user_id = str(st.session_state.get("user_id") or "default_user").strip() or "default_user"
    ok, data = request_json("DELETE", f"{API_PREFIX}/history/tasks", params={"user_id": user_id})
    if ok:
        deleted = data.get("deleted", 0) if isinstance(data, dict) else 0
        st.session_state.history_items = []
        clear_current_session()
        st.session_state.last_notice = f"已清空 {deleted} 条历史记录。"
    else:
        st.session_state.last_error = str(data)


def clear_current_session() -> None:
    st.session_state.current_result = None
    st.session_state.batch_results = []
    st.session_state.selected_batch_index = 0
    st.session_state.selected_version_index = 0
    st.session_state.messages = []


def current_versions() -> List[Dict[str, Any]]:
    result = st.session_state.current_result or {}
    versions = result.get("rewritten_versions") or []
    return [v for v in versions if isinstance(v, dict)][:2]


def selected_version() -> Optional[Dict[str, Any]]:
    versions = current_versions()
    if not versions:
        return None
    index = min(int(st.session_state.get("selected_version_index") or 0), len(versions) - 1)
    return versions[index]


def version_label(version: Dict[str, Any]) -> str:
    version_type = str(version.get("version_type") or "")
    return VERSION_TYPE_LABELS.get(version_type, version_type or "推荐版本")



def render_markdown_block(markdown_text: str, height: int = 430) -> None:
    with st.container(height=height, border=False):
        st.markdown(markdown_text or "暂无报告。")



def safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)



def render_title_suggestions(titles: List[str]) -> None:
    if not titles:
        st.caption("暂无标题建议。")
        return
    for idx, title in enumerate(titles, start=1):
        st.markdown(
            f"<span class='soft-tag'>标题 {idx}</span> {title}",
            unsafe_allow_html=True,
        )



def render_version(version: Dict[str, Any], index: int) -> None:
    raw_type = str(version.get("version_type") or f"version_{index}")
    version_type = html.escape(VERSION_TYPE_LABELS.get(raw_type, raw_type))
    description = html.escape(VERSION_TYPE_DESCRIPTIONS.get(raw_type, str(version.get("notes") or "")))
    title = html.escape(str(version.get("title") or "未命名版本"))
    score = html.escape(str(version.get("score", "-")))
    notes = html.escape(str(version.get("notes") or ""))
    body = html.escape(str(version.get("body") or ""))

    st.markdown(
        f"""
        <div class="result-card">
            <div class="version-title">【{version_type}】</div>
            <div class="small-muted">{description}</div>
            <span class="soft-tag">评分 {score}</span>
            <span class="soft-tag">{title}</span>
            <div class="small-muted" style="margin-top: .35rem;">{notes}</div>
            <div class="version-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_risk_items(items: List[Dict[str, Any]]) -> None:
    if not items:
        st.success("未检测到明显风险表达。")
        return

    rows = []
    for item in items:
        rows.append(
            {
                "命中文本": item.get("text", ""),
                "风险类型": item.get("risk_type", ""),
                "严重程度": item.get("severity", ""),
                "修改建议": item.get("suggestion", ""),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True, height=min(260, 48 + 38 * len(rows)))



def render_evidence(evidence: Dict[str, Any]) -> None:
    if not evidence:
        st.info("暂无检索依据。")
        return

    strategy = evidence.get("strategy_pack") or {}
    decision_notes = evidence.get("decision_notes") or []
    top_rules = evidence.get("top_rules") or []
    top_risks = evidence.get("top_risk_expressions") or []
    similar_cases = evidence.get("similar_cases") or []
    quality_scores = evidence.get("quality_scores") or {}

    with st.expander("策略摘要", expanded=True):
        st.write(evidence.get("task_summary") or "-")
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("平台语气")
            st.write(strategy.get("tone") or "-")
            st.caption("标题风格")
            st.write(strategy.get("title_style") or "-")
        with col_b:
            st.caption("核心目标")
            st.write(strategy.get("content_core_goal") or "-")
            st.caption("输出重点")
            st.write(strategy.get("output_focus") or "-")

    with st.expander("决策说明", expanded=False):
        if decision_notes:
            for note in decision_notes:
                st.markdown(f"- {note}")
        else:
            st.write("-")

    with st.expander("平台规则 / 风险表达", expanded=False):
        st.markdown("**平台规则**")
        for rule in top_rules[:6]:
            st.markdown(f"- {rule}")
        if not top_rules:
            st.caption("暂无平台规则召回。")

        st.markdown("**风险表达**")
        for risk in top_risks[:8]:
            st.markdown(f"- {risk}")
        if not top_risks:
            st.caption("暂无风险表达召回。")

    with st.expander("相似案例", expanded=False):
        if similar_cases:
            for case in similar_cases[:4]:
                st.markdown(f"**{case.get('title', '未命名案例')}**")
                st.caption(case.get("reason", ""))
                st.write(case.get("body", ""))
                st.divider()
        else:
            st.caption("暂无相似案例。")

    with st.expander("质量评分明细", expanded=False):
        if quality_scores:
            st.json(quality_scores, expanded=False)
        else:
            st.caption("暂无质量评分明细。")



def render_trace(trace: List[Dict[str, Any]]) -> None:
    if not trace:
        st.caption("暂无流程轨迹。")
        return

    for item in trace:
        node = item.get("node") or item.get("name") or "node"
        message = item.get("message") or item.get("desc") or "完成"
        meta = {k: v for k, v in item.items() if k not in {"node", "name", "message", "desc"}}
        with st.expander(f"{node} · {message}", expanded=False):
            if meta:
                st.json(meta, expanded=False)
            else:
                st.caption("无额外信息。")



def render_result(result: Optional[Dict[str, Any]]) -> None:
    if not result:
        st.markdown(
            """
            <div class="mini-card">
                <div class="section-title">输出结果</div>
                <div class="section-hint">提交文案后，这里会展示评分、风险项、标题建议、改写版本、检索依据和工作流轨迹。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    risk_level = str(result.get("risk_level") or "unknown")
    risk_label = html.escape(RISK_LEVEL_LABELS.get(risk_level, risk_level))
    risk_class = RISK_BADGE_CLASS.get(risk_level, "risk-unknown")
    score = result.get("score", "-")
    platform = html.escape(label_of(PLATFORM_OPTIONS, result.get("platform")))
    content_type = html.escape(label_of(CONTENT_TYPE_OPTIONS, result.get("content_type")))
    task_id = html.escape(str(result.get("task_id") or "-"))

    if st.session_state.batch_results:
        items = st.session_state.batch_results
        labels = [f"{idx + 1}. {label_of(PLATFORM_OPTIONS, item.get('platform'))} · {item.get('score', '-')}分" for idx, item in enumerate(items)]
        selected = st.selectbox(
            "多平台结果",
            options=list(range(len(items))),
            format_func=lambda i: labels[i],
            index=min(int(st.session_state.selected_batch_index), len(items) - 1),
            key="batch_result_selector",
        )
        st.session_state.selected_batch_index = selected
        st.session_state.current_result = items[selected]
        result = items[selected]
        risk_level = str(result.get("risk_level") or "unknown")
        risk_label = html.escape(RISK_LEVEL_LABELS.get(risk_level, risk_level))
        risk_class = RISK_BADGE_CLASS.get(risk_level, "risk-unknown")
        score = result.get("score", "-")
        platform = html.escape(label_of(PLATFORM_OPTIONS, result.get("platform")))
        content_type = html.escape(label_of(CONTENT_TYPE_OPTIONS, result.get("content_type")))
        task_id = html.escape(str(result.get("task_id") or "-"))

    st.markdown(
        f"""
        <div class="metric-strip">
            <div class="metric-box"><div class="metric-label">综合评分</div><div class="metric-value">{score}/100</div></div>
            <div class="metric-box"><div class="metric-label">风险等级</div><div class="metric-value"><span class="badge {risk_class}">{risk_label}</span></div></div>
            <div class="metric-box"><div class="metric-label">任务 ID</div><div class="metric-value" style="font-size:.82rem;">{task_id}</div></div>
        </div>
        <div class="small-muted">平台：{platform}　｜　类型：{content_type}</div>
        """,
        unsafe_allow_html=True,
    )

    versions = result.get("rewritten_versions") or []
    titles = result.get("title_suggestions") or []
    risk_items = result.get("risk_items") or []
    evidence = result.get("evidence_pack") or {}
    final_report = result.get("final_report") or ""
    trace = result.get("trace") or []

    tab_versions, tab_report, tab_risk, tab_evidence, tab_trace = st.tabs(
        ["推荐文案", "质检报告", "风险诊断", "检索依据", "流程轨迹"]
    )

    with tab_versions:
        st.markdown("<div class='section-title'>标题建议</div>", unsafe_allow_html=True)
        render_title_suggestions(titles)
        st.divider()
        st.markdown("<div class='section-title'>推荐文案</div>", unsafe_allow_html=True)
        if versions:
            version_options = list(range(min(len(versions), 2)))
            st.radio(
                "继续修改基于",
                options=version_options,
                format_func=lambda i: version_label(versions[i]),
                horizontal=True,
                key="selected_version_index",
            )
            with st.container(height=470, border=False):
                for idx, version in enumerate(versions[:2], start=1):
                    render_version(version, idx)
        else:
            st.info("当前任务没有生成正文改写版本。")

    with tab_report:
        render_markdown_block(final_report, height=545)

    with tab_risk:
        render_risk_items(risk_items)
        with st.expander("原始响应中的风险字段", expanded=False):
            st.json(risk_items, expanded=False)

    with tab_evidence:
        with st.container(height=545, border=False):
            render_evidence(evidence)

    with tab_trace:
        with st.container(height=545, border=False):
            render_trace(trace)
        with st.expander("完整 JSON", expanded=False):
            st.code(safe_json(result), language="json")


# =============================
# 顶部栏
# =============================

st.markdown(
    """
    <div class="topbar">
        <div>
            <div class="brand-title">文案改写工作台</div>
            <div class="brand-subtitle">这是一个多功能文案改写智能助手，可完成发布前质检、风险表达识别、多平台改写、标题生成与二次优化。</div>
        </div>
        <div class="topbar-tags">
            <span class="tag">ContentPilot</span>
            <span class="soft-tag">LangGraph 工作流</span>
            <span class="soft-tag">RAG 规则召回</span>
            <span class="soft-tag">三栏工作台</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================
# 三栏主界面
# =============================

left_col, middle_col, right_col = st.columns([0.95, 1.38, 1.32], gap="small")


# ---------- 左侧：功能栏 ----------
with left_col:
    st.markdown("<div class='section-title'>功能栏</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-hint'>设置任务参数、后端连接、历史复用和偏好记忆。</div>", unsafe_allow_html=True)

    with st.container(border=True):
        with st.expander("连接设置", expanded=True):
            current_api_base = normalize_base_url(st.session_state.api_base_url)
            api_base_url = st.text_input("Agent API 地址", value=current_api_base, key="api_base_url_input")
            st.session_state.api_base_url = normalize_base_url(api_base_url)

            health_col, diag_col = st.columns(2)
            with health_col:
                if st.button("检查后端", use_container_width=True):
                    ok, data = request_json("GET", "/health")
                    if ok:
                        st.session_state.health = data
                        st.session_state.last_notice = "后端连接正常。"
                    else:
                        st.session_state.health = None
                        st.session_state.last_error = str(data)
            with diag_col:
                if st.button("诊断", use_container_width=True):
                    ok, data = request_json("GET", "/health/diagnostics")
                    if ok:
                        st.session_state.health = data
                        st.session_state.last_notice = "诊断信息已返回。"
                    else:
                        st.session_state.health = None
                        st.session_state.last_error = str(data)

            if st.session_state.health:
                status = str(st.session_state.health.get("status", "unknown"))
                if status == "ok":
                    st.success("后端运行正常")
                elif status == "warn":
                    st.warning("后端可用，但存在警告")
                else:
                    st.error("后端诊断异常")
                with st.expander("查看连接信息", expanded=False):
                    st.json(st.session_state.health, expanded=False)

        st.divider()

        st.selectbox(
            "任务类型",
            options=list(TASK_TYPE_OPTIONS.keys()),
            format_func=lambda value: TASK_TYPE_OPTIONS[value],
            index=option_index(TASK_TYPE_OPTIONS, st.session_state.task_type),
            key="task_type",
        )

        st.selectbox(
            "目标平台",
            options=list(PLATFORM_OPTIONS.keys()),
            format_func=lambda value: PLATFORM_OPTIONS[value],
            index=option_index(PLATFORM_OPTIONS, st.session_state.platform),
            key="platform",
        )

        st.multiselect(
            "多平台批量改写",
            options=list(PLATFORM_OPTIONS.keys()),
            format_func=lambda value: PLATFORM_OPTIONS[value],
            key="platforms",
            help="勾选 2 个及以上平台后，可在提交时选择批量生成。",
        )

        st.selectbox(
            "内容类型",
            options=list(CONTENT_TYPE_OPTIONS.keys()),
            format_func=lambda value: CONTENT_TYPE_OPTIONS[value],
            index=option_index(CONTENT_TYPE_OPTIONS, st.session_state.content_type),
            key="content_type",
        )

        st.selectbox(
            "改写强度",
            options=list(REWRITE_INTENSITY_OPTIONS.keys()),
            format_func=lambda value: REWRITE_INTENSITY_OPTIONS[value],
            key="rewrite_intensity",
        )

        st.select_slider(
            "表达力度",
            options=list(EXPRESSION_STRENGTH_OPTIONS.keys()),
            format_func=lambda value: EXPRESSION_STRENGTH_OPTIONS[value],
            key="expression_strength",
            help="允许系统增强吸引力，但不使用绝对化、虚假承诺或极限表达。",
        )

        st.text_input("用户 ID", key="user_id", help="用于历史记录和偏好记忆。")
        st.text_input("目标受众（可选）", key="target_audience", placeholder="例如：新手宝妈、大学生、职场新人")

        with st.expander("示例文案", expanded=False):
            for name, sample in SAMPLE_CONTENTS.items():
                if st.button(name, key=f"sample_{name}", use_container_width=True):
                    st.session_state.raw_content = sample
                    st.session_state.raw_content_input = sample
                    st.session_state.last_notice = f"已载入示例：{name}。"
                    st.rerun()

        with st.expander("偏好记忆", expanded=False):
            pref_col1, pref_col2 = st.columns(2)
            with pref_col1:
                if st.button("读取偏好", use_container_width=True):
                    load_preference()
                    st.rerun()
            with pref_col2:
                if st.button("保存偏好", use_container_width=True):
                    save_preference(st.session_state.get("preference_editor", ""))
                    st.rerun()
            st.text_area(
                "偏好内容",
                height=105,
                key="preference_editor",
                placeholder="例如：更喜欢短句、克制表达、少用感叹号。",
            )

        with st.expander("历史任务", expanded=False):
            if st.button("刷新历史", use_container_width=True):
                load_history(limit=12)
                st.rerun()

            st.checkbox("确认清空全部历史", key="confirm_clear_history")
            if st.button(
                "清空全部历史",
                use_container_width=True,
                disabled=not bool(st.session_state.confirm_clear_history),
            ):
                clear_all_history()
                st.session_state.confirm_clear_history = False
                st.rerun()

            if not st.session_state.history_items:
                st.caption("暂无历史记录，点击刷新历史。")
            else:
                with st.container(height=220, border=False):
                    for item in st.session_state.history_items:
                        item_task_id = item.get("task_id", "")
                        title = f"{label_of(PLATFORM_OPTIONS, item.get('platform'))} · {label_of(CONTENT_TYPE_OPTIONS, item.get('content_type'))} · {item.get('score', '-') }分"
                        st.caption(item.get("created_at", ""))
                        st.write(title)
                        reuse_col, delete_col = st.columns(2)
                        with reuse_col:
                            if st.button("复用", key=f"reuse_{item_task_id}", use_container_width=True):
                                reuse_task(item_task_id)
                                st.rerun()
                        with delete_col:
                            if st.button("删除", key=f"delete_{item_task_id}", use_container_width=True):
                                delete_history_task(item_task_id)
                                st.rerun()
                        st.divider()


# ---------- 中间：对话 / 输入栏 ----------
with middle_col:
    st.markdown("<div class='section-title'>对话栏</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-hint'>输入原始文案，选择单平台或多平台处理；下方可继续追问式二次修改。</div>", unsafe_allow_html=True)

    if st.session_state.last_error:
        st.error(st.session_state.last_error)
        st.session_state.last_error = ""
    if st.session_state.last_notice:
        st.success(st.session_state.last_notice)
        st.session_state.last_notice = ""

    if st.button("删除当前会话", use_container_width=True, disabled=not bool(st.session_state.messages or st.session_state.current_result)):
        clear_current_session()
        st.session_state.last_notice = "当前会话已删除。"
        st.rerun()

    with st.container(border=True):
        with st.form("analyze_form", clear_on_submit=False):
            raw_content = st.text_area(
                "原始文案",
                key="raw_content_input",
                height=205,
                placeholder="请输入需要质检、改写或生成标题的文案……",
            )

            submit_col1, submit_col2, submit_col3 = st.columns([1.1, 1.1, 0.9])
            with submit_col1:
                analyze_submitted = st.form_submit_button("开始分析", type="primary", use_container_width=True)
            with submit_col2:
                batch_submitted = st.form_submit_button("多平台生成", use_container_width=True)
            with submit_col3:
                clear_submitted = st.form_submit_button("清空", use_container_width=True)

        if clear_submitted:
            st.session_state.clear_input_next = True
            clear_current_session()
            st.rerun()

        if analyze_submitted or batch_submitted:
            content = str(raw_content or "").strip()
            if not content:
                st.warning("请先输入文案。")
            else:
                use_batch = bool(batch_submitted)
                payload = build_analyze_payload(content, use_batch=use_batch)
                st.session_state.last_payload = payload
                st.session_state.raw_content = content
                st.session_state.messages.append({"role": "user", "content": content})
                endpoint = f"{API_PREFIX}/content/batch" if use_batch else f"{API_PREFIX}/content/analyze"
                with st.spinner("正在调用 ContentPilot 工作流……"):
                    ok, data = request_json("POST", endpoint, payload=payload)
                if ok and isinstance(data, dict):
                    set_result_from_response(data, source="analyze")
                    st.rerun()
                else:
                    st.session_state.last_error = str(data)
                    st.rerun()

    with st.container(border=True):
        st.markdown("<div class='section-title'>会话记录</div>", unsafe_allow_html=True)
        if not st.session_state.messages:
            st.caption("暂无会话。提交文案后会显示本轮输入与系统摘要。")
        else:
            with st.container(height=190, border=False):
                for message in st.session_state.messages[-10:]:
                    role = message.get("role", "assistant")
                    content = html.escape(str(message.get("content", "")))
                    klass = "chat-bubble-user" if role == "user" else "chat-bubble-assistant"
                    role_name = "你" if role == "user" else "ContentPilot"
                    st.markdown(
                        f"<div class='{klass}'><b>{role_name}</b><br>{content}</div>",
                        unsafe_allow_html=True,
                    )

        current_task_id = (st.session_state.current_result or {}).get("task_id") if st.session_state.current_result else None
        with st.form("refine_form", clear_on_submit=True):
            refine_instruction = st.text_input(
                "继续修改",
                placeholder="例如：更短一些、语气更自然、适合知乎、标题更克制……",
                disabled=not bool(st.session_state.current_result),
            )
            refine_submit = st.form_submit_button("提交二次修改", use_container_width=True, disabled=not bool(st.session_state.current_result))

        if refine_submit:
            instruction = str(refine_instruction or "").strip()
            if not instruction:
                st.warning("请输入二次修改要求。")
            else:
                base_result = st.session_state.current_result or {}
                active_version = selected_version() or {}
                selected_body = str(active_version.get("body") or "").strip()
                original_content = str(st.session_state.get("raw_content") or st.session_state.get("raw_content_input") or "").strip()
                previous_output = safe_json(
                    {
                        "risk_level": base_result.get("risk_level"),
                        "score": base_result.get("score"),
                        "versions": [
                            {
                                "version_type": v.get("version_type"),
                                "title": v.get("title"),
                                "body": v.get("body"),
                            }
                            for v in current_versions()
                        ],
                    }
                )
                refine_payload = {
                    "task_id": current_task_id,
                    "raw_content": original_content,
                    "instruction": instruction,
                    "platform": base_result.get("platform") or st.session_state.platform,
                    "content_type": base_result.get("content_type") or st.session_state.content_type,
                    "task_type": st.session_state.task_type,
                    "target_audience": str(st.session_state.target_audience or "").strip() or None,
                    "rewrite_intensity": str(st.session_state.get("rewrite_intensity") or "medium"),
                    "expression_strength": str(st.session_state.get("expression_strength") or "moderate"),
                    "selected_version_body": selected_body,
                    "selected_version_type": active_version.get("version_type"),
                    "original_content": original_content,
                    "previous_output": previous_output,
                    "user_id": str(st.session_state.user_id or "default_user").strip() or "default_user",
                    "conversation_id": current_task_id,
                }
                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": f"继续修改（基于{version_label(active_version) if active_version else '当前结果'}）：{instruction}",
                    }
                )
                with st.spinner("正在进行二次优化……"):
                    ok, data = request_json("POST", f"{API_PREFIX}/content/refine", payload=refine_payload)
                if ok and isinstance(data, dict):
                    set_result_from_response(data, source="refine")
                    st.rerun()
                else:
                    st.session_state.last_error = str(data)
                    st.rerun()


# ---------- 右侧：输出栏 ----------
with right_col:
    st.markdown("<div class='section-title'>输出栏</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-hint'>集中查看推荐文案、风险诊断、报告、依据和流程轨迹。</div>", unsafe_allow_html=True)

    with st.container(border=True):
        render_result(st.session_state.current_result)

        if st.session_state.current_result:
            st.divider()
            st.markdown("<div class='section-title'>反馈</div>", unsafe_allow_html=True)
            versions = st.session_state.current_result.get("rewritten_versions") or []
            version_types = [v.get("version_type") or f"version_{i+1}" for i, v in enumerate(versions)]
            with st.form("feedback_form", clear_on_submit=True):
                rating = st.slider("评分", min_value=1, max_value=5, value=4)
                preferred = st.selectbox(
                    "偏好的版本",
                    options=[""] + version_types,
                    format_func=lambda value: "不指定" if not value else value,
                )
                comment = st.text_input("反馈意见", placeholder="例如：更喜欢短句和克制表达")
                remember = st.checkbox("将反馈写入偏好记忆", value=True)
                feedback_submit = st.form_submit_button("提交反馈", use_container_width=True)

            if feedback_submit:
                task_id = st.session_state.current_result.get("task_id")
                feedback_payload = {
                    "task_id": task_id,
                    "user_id": str(st.session_state.user_id or "default_user").strip() or "default_user",
                    "rating": rating,
                    "comment": comment,
                    "preferred_version_type": preferred or None,
                    "remember_as_preference": remember,
                }
                ok, data = request_json("POST", f"{API_PREFIX}/feedback", payload=feedback_payload)
                if ok:
                    st.success("反馈已提交。")
                else:
                    st.error(str(data))
