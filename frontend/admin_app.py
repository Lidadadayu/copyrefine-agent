from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


st.set_page_config(
    page_title="ContentPilot 知识库管理",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_PREFIX = "/api/v1"
DEFAULT_API_BASE = os.getenv("CONTENTPILOT_API_BASE_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 60

COLLECTION_OPTIONS: Dict[str, str] = {
    "platform_rule": "平台规则",
    "risk_expression": "风险表达",
    "content_case": "优秀案例",
    "brand_rule": "品牌规范",
    "industry_rule": "行业规范",
    "custom_rule": "自定义规则",
    "general": "通用知识",
}

PLATFORM_OPTIONS: Dict[str, str] = {
    "": "全部平台",
    "xiaohongshu": "小红书",
    "wechat": "公众号",
    "zhihu": "知乎",
    "short_video": "短视频",
}

CONTENT_TYPE_OPTIONS: Dict[str, str] = {
    "": "全部类型",
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


STYLE = """
<style>
:root {
  --cp-bg: #f7f8fb;
  --cp-card: rgba(255, 255, 255, 0.96);
  --cp-border: #d9e2ec;
  --cp-text: #1f2937;
  --cp-muted: #64748b;
  --cp-accent: #0f766e;
}
.stApp { background: linear-gradient(180deg, #f7f8fb 0%, #eef7f5 100%); }
.block-container { padding: 1.2rem 1.5rem 1.5rem; max-width: 100%; }
h1, h2, h3, h4 { color: var(--cp-text); }
.cp-hero, .cp-card {
  background: var(--cp-card);
  border: 1px solid var(--cp-border);
  border-radius: 8px;
  padding: 1.0rem 1.1rem;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.055);
}
.cp-hero { margin-bottom: .85rem; }
.cp-subtitle { color: var(--cp-muted); margin-top: .25rem; }
.cp-pill {
  display: inline-flex;
  padding: .18rem .55rem;
  border: 1px solid var(--cp-border);
  border-radius: 999px;
  color: var(--cp-muted);
  background: #f8fafc;
  font-size: .78rem;
  margin-right: .25rem;
}
div[data-testid="stMetric"] {
  background: #f8fafc;
  border: 1px solid var(--cp-border);
  border-radius: 8px;
  padding: .65rem .8rem;
}
.stButton > button[kind="primary"] { background: var(--cp-accent); border-color: var(--cp-accent); }
textarea, input, .stSelectbox [data-baseweb="select"] { border-radius: 8px !important; }
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)


def init_state() -> None:
    st.session_state.setdefault("api_base_url", DEFAULT_API_BASE.rstrip("/"))
    st.session_state.setdefault("knowledge_items", [])
    st.session_state.setdefault("selected_item_id", None)
    st.session_state.setdefault("last_message", "")


def api_url(path: str) -> str:
    base = str(st.session_state.get("api_base_url") or DEFAULT_API_BASE).strip().rstrip("/")
    return f"{base}{API_PREFIX}{path}"


def request_json(method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    response = requests.request(method, api_url(path), timeout=REQUEST_TIMEOUT, **kwargs)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {"data": data}


def normalize_tags(text: str) -> List[str]:
    parts = []
    for chunk in text.replace("，", ",").replace("；", ",").replace(";", ",").split(","):
        value = chunk.strip()
        if value:
            parts.append(value)
    return list(dict.fromkeys(parts))


def tags_to_text(tags: Any) -> str:
    if isinstance(tags, list):
        return ", ".join(str(tag) for tag in tags if tag)
    if isinstance(tags, str):
        return tags
    return ""


def platform_label(value: Optional[str]) -> str:
    return PLATFORM_OPTIONS.get(value or "", value or "全部平台")


def content_type_label(value: Optional[str]) -> str:
    return CONTENT_TYPE_OPTIONS.get(value or "", value or "全部类型")


def collection_label(value: Optional[str]) -> str:
    return COLLECTION_OPTIONS.get(value or "general", value or "通用知识")


def load_items() -> None:
    collection = st.session_state.get("filter_collection") or ""
    platform = st.session_state.get("filter_platform") or ""
    content_type = st.session_state.get("filter_content_type") or ""
    keyword = str(st.session_state.get("filter_keyword") or "").strip()

    params: Dict[str, Any] = {"limit": 300}
    if collection and collection != "all":
        params["collection"] = collection
    if platform:
        params["platform"] = platform
    if content_type:
        params["content_type"] = content_type
    if keyword:
        params["keyword"] = keyword

    data = request_json("GET", "/knowledge/items", params=params)
    items = data.get("items") or []
    st.session_state["knowledge_items"] = items if isinstance(items, list) else []


init_state()

st.markdown(
    """
<div class="cp-hero">
  <h2 style="margin:0;">ContentPilot 知识库管理后台</h2>
  <div class="cp-subtitle">维护平台规则、风险表达、优秀案例和品牌规范；保存后可重建语义索引，让前台改写结果更准确。</div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("服务设置")
    st.session_state.api_base_url = st.text_input(
        "后端地址",
        value=str(st.session_state.get("api_base_url") or DEFAULT_API_BASE),
        help="默认读取环境变量 CONTENTPILOT_API_BASE_URL。",
    ).strip().rstrip("/")

left, middle, right = st.columns([0.95, 1.35, 1.25], gap="large")

with left:
    st.markdown("### 筛选与操作")
    with st.container(border=True):
        collection_keys = ["all"] + list(COLLECTION_OPTIONS.keys())
        collection_names = {"all": "全部知识"} | COLLECTION_OPTIONS
        st.selectbox(
            "知识类型",
            options=collection_keys,
            format_func=lambda key: collection_names.get(key, key),
            key="filter_collection",
        )
        st.selectbox(
            "平台",
            options=list(PLATFORM_OPTIONS.keys()),
            format_func=lambda key: PLATFORM_OPTIONS.get(key, key),
            key="filter_platform",
        )
        st.selectbox(
            "内容类型",
            options=list(CONTENT_TYPE_OPTIONS.keys()),
            format_func=lambda key: CONTENT_TYPE_OPTIONS.get(key, key),
            key="filter_content_type",
        )
        st.text_input("关键词", key="filter_keyword", placeholder="标题、正文或标签")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("刷新列表", use_container_width=True, type="primary"):
                try:
                    load_items()
                    st.session_state["last_message"] = "列表已刷新。"
                except Exception as exc:
                    st.error(f"读取失败：{exc}")
        with c2:
            if st.button("重建索引", use_container_width=True):
                try:
                    data = request_json("POST", "/knowledge/reindex", params={"force": True})
                    st.session_state["last_message"] = "语义索引已重建。"
                    st.success(data.get("message", "语义索引已重建。"))
                except Exception as exc:
                    st.error(f"重建失败：{exc}")

    st.markdown("### 知识库概览")
    items: List[Dict[str, Any]] = st.session_state.get("knowledge_items") or []
    total = len(items)
    collections = len({str(item.get("collection") or "") for item in items}) if items else 0
    platforms = len({str(item.get("platform") or "") for item in items if item.get("platform")}) if items else 0
    st.metric("当前列表", total)
    st.metric("知识类型", collections)
    st.metric("覆盖平台", platforms)

    if not items:
        try:
            load_items()
            items = st.session_state.get("knowledge_items") or []
        except Exception:
            pass

with middle:
    st.markdown("### 知识列表")
    items = st.session_state.get("knowledge_items") or []

    if not items:
        st.info("暂无知识条目。可以在右侧新增，或点击左侧刷新列表。")
    else:
        option_map: Dict[int, str] = {}
        for item in items:
            item_id = int(item.get("id") or 0)
            title = str(item.get("title") or "未命名")[:32]
            option_map[item_id] = f"#{item_id}｜{collection_label(item.get('collection'))}｜{platform_label(item.get('platform'))}｜{title}"

        selected_id = st.radio(
            "选择要编辑的知识条目",
            options=list(option_map.keys()),
            format_func=lambda item_id: option_map.get(item_id, str(item_id)),
            label_visibility="collapsed",
        )
        st.session_state["selected_item_id"] = selected_id

        selected = next((item for item in items if int(item.get("id") or 0) == selected_id), None)
        if selected:
            st.markdown(
                f"""
<div class="cp-card">
  <span class="cp-pill">{collection_label(selected.get('collection'))}</span>
  <span class="cp-pill">{platform_label(selected.get('platform'))}</span>
  <span class="cp-pill">{content_type_label(selected.get('content_type'))}</span>
  <h4 style="margin:.75rem 0 .35rem;">{selected.get('title') or '未命名'}</h4>
  <div style="white-space:pre-wrap;color:#4d3b2e;line-height:1.7;">{selected.get('body') or ''}</div>
  <div class="cp-subtitle" style="margin-top:.6rem;">标签：{tags_to_text(selected.get('tags')) or '无'}</div>
</div>
""",
                unsafe_allow_html=True,
            )

with right:
    st.markdown("### 新增 / 编辑")
    items = st.session_state.get("knowledge_items") or []
    selected_id = st.session_state.get("selected_item_id")
    selected_item = next((item for item in items if int(item.get("id") or 0) == selected_id), None)

    edit_mode = st.toggle("编辑当前选中条目", value=bool(selected_item), disabled=not bool(selected_item))
    source = selected_item if edit_mode and selected_item else {}

    with st.form("knowledge_form", clear_on_submit=False):
        default_collection = str(source.get("collection") or "general")
        if default_collection not in COLLECTION_OPTIONS:
            default_collection = "general"

        collection = st.selectbox(
            "知识类型",
            options=list(COLLECTION_OPTIONS.keys()),
            format_func=lambda key: COLLECTION_OPTIONS.get(key, key),
            index=list(COLLECTION_OPTIONS.keys()).index(default_collection),
        )
        title = st.text_input("标题", value=str(source.get("title") or ""), placeholder="例如：小红书功效表达边界")
        body = st.text_area(
            "正文",
            value=str(source.get("body") or ""),
            height=180,
            placeholder="写入规则、风险表达、案例正文或品牌规范。",
        )

        default_platform = str(source.get("platform") or "")
        if default_platform not in PLATFORM_OPTIONS:
            default_platform = ""
        platform = st.selectbox(
            "适用平台",
            options=list(PLATFORM_OPTIONS.keys()),
            format_func=lambda key: PLATFORM_OPTIONS.get(key, key),
            index=list(PLATFORM_OPTIONS.keys()).index(default_platform),
        )

        default_content_type = str(source.get("content_type") or "")
        if default_content_type not in CONTENT_TYPE_OPTIONS:
            default_content_type = ""
        content_type = st.selectbox(
            "适用内容类型",
            options=list(CONTENT_TYPE_OPTIONS.keys()),
            format_func=lambda key: CONTENT_TYPE_OPTIONS.get(key, key),
            index=list(CONTENT_TYPE_OPTIONS.keys()).index(default_content_type),
        )

        tags = st.text_input("标签", value=tags_to_text(source.get("tags")), placeholder="多个标签用逗号分隔")

        submit_label = "保存修改" if edit_mode and selected_item else "新增知识"
        submitted = st.form_submit_button(submit_label, use_container_width=True, type="primary")

    if submitted:
        payload = {
            "collection": collection,
            "title": title.strip(),
            "body": body.strip(),
            "platform": platform or None,
            "content_type": content_type or None,
            "tags": normalize_tags(tags),
        }
        if not payload["title"] or not payload["body"]:
            st.warning("标题和正文不能为空。")
        else:
            try:
                if edit_mode and selected_item:
                    item_id = int(selected_item.get("id") or 0)
                    request_json("PUT", f"/knowledge/items/{item_id}", json=payload)
                    st.success("已保存修改。")
                else:
                    request_json("POST", "/knowledge/items", json=payload)
                    st.success("已新增知识。")
                load_items()
            except Exception as exc:
                st.error(f"保存失败：{exc}")

    if edit_mode and selected_item:
        st.divider()
        if st.button("删除当前条目", use_container_width=True):
            try:
                item_id = int(selected_item.get("id") or 0)
                request_json("DELETE", f"/knowledge/items/{item_id}")
                st.session_state["selected_item_id"] = None
                load_items()
                st.success("已删除。")
            except Exception as exc:
                st.error(f"删除失败：{exc}")

message = str(st.session_state.get("last_message") or "")
if message:
    st.toast(message)
    st.session_state["last_message"] = ""
