from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import time

import yaml


PROMPTS_DIR = Path("prompts")

DEFAULT_PROMPTS: Dict[str, Dict[str, str]] = {
    "content_optimizer": {
        "version": "v1",
        "prompt": "你是内容优化助手。请在合规前提下优化标题和正文。",
    },
    "content_optimizer_system": {
        "version": "v1",
        "prompt": """你是一个内容发布前质检与优化助手。
你的任务是根据平台规则、风险表达、相似案例、历史风格画像和用户偏好，生成更安全、更自然、更适合平台的标题和改写文案。

要求：
1. 不要规避平台审核，不要生成违规绕审表达。
2. 不要保留绝对化承诺、健康功效承诺、强诱导购买、焦虑营销表达。
3. 保留原文核心意思，但改成体验型、边界清晰、理性建议的表达。
4. 如果用户偏好与合规要求冲突，优先满足合规要求。
5. 必须只输出 JSON，不要输出 Markdown，不要输出解释文字。""",
    },
    "intent_classifier": {
        "version": "v1",
        "prompt": "你是内容运营任务识别助手。请识别平台、内容类型、任务意图和风险敏感度。",
    },
    "query_rewriter": {
        "version": "v1",
        "prompt": "你是查询改写助手。请将用户需求改写为适合检索规则库、风险库和案例库的查询。",
    },
    "query_router": {
        "version": "v1",
        "prompt": "你是查询路由助手。请判断需要检索哪些知识库。",
    },
    "context_compressor": {
        "version": "v1",
        "prompt": "你是上下文压缩助手。请将检索结果压缩成 evidence pack。",
    },
    "risk_checker": {
        "version": "v1",
        "prompt": "你是发布前风险质检助手。请检查绝对化表达、功效承诺、诱导性表达和结构问题。",
    },
    "review_guard": {
        "version": "v1",
        "prompt": "你是安全审核助手。请检查生成内容是否仍然存在高风险表达。",
    },
}


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(name or "").strip())
    if not cleaned:
        raise ValueError("prompt name cannot be empty")
    return cleaned


def _prompt_path(name: str) -> Path:
    return PROMPTS_DIR / f"{_safe_name(name)}.yaml"


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _write_yaml(name: str, prompt: str, version: str = "v1") -> Dict[str, Any]:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_name(name)
    path = _prompt_path(safe_name)

    data: Dict[str, Any] = {
        "name": safe_name,
        "version": str(version or "v1"),
        "prompt": str(prompt or ""),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return _template_from_file(path)


def ensure_prompt_files() -> None:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    for name, data in DEFAULT_PROMPTS.items():
        path = _prompt_path(name)
        if not path.exists():
            _write_yaml(name=name, prompt=data["prompt"], version=data.get("version", "v1"))


def _template_from_file(path: Path) -> Dict[str, Any]:
    data = _read_yaml(path)
    stat = path.stat() if path.exists() else None

    name = str(data.get("name") or path.stem)
    version = str(data.get("version") or "v1")
    prompt = str(data.get("prompt") or "")

    return {
        "name": name,
        "version": version,
        "prompt": prompt,
        "path": str(path.as_posix()),
        "updated_at": str(data.get("updated_at") or ""),
        "mtime": stat.st_mtime if stat else 0,
    }


def list_prompt_templates() -> List[Dict[str, Any]]:
    ensure_prompt_files()
    items = [_template_from_file(path) for path in sorted(PROMPTS_DIR.glob("*.yaml"))]
    return sorted(items, key=lambda item: str(item.get("name", "")))


def get_prompt_template(name: str) -> Dict[str, Any]:
    ensure_prompt_files()
    safe_name = _safe_name(name)
    direct_path = _prompt_path(safe_name)

    if direct_path.exists():
        return _template_from_file(direct_path)

    for path in PROMPTS_DIR.glob("*.yaml"):
        data = _read_yaml(path)
        if str(data.get("name") or path.stem) == safe_name:
            return _template_from_file(path)

    default = DEFAULT_PROMPTS.get(safe_name)
    if default:
        return _write_yaml(safe_name, default["prompt"], default.get("version", "v1"))

    raise FileNotFoundError(f"prompt template not found: {safe_name}")


def update_prompt_template(name: str, prompt: str, version: str = "v1") -> Dict[str, Any]:
    return _write_yaml(name=name, prompt=prompt, version=version)


def reset_prompt_template(name: str) -> Dict[str, Any]:
    safe_name = _safe_name(name)
    default = DEFAULT_PROMPTS.get(safe_name)
    if not default:
        raise ValueError(f"no built-in default prompt for: {safe_name}")

    return _write_yaml(safe_name, default["prompt"], default.get("version", "v1"))


def get_prompt_template_text(name: str, fallback: Optional[str] = None) -> str:
    try:
        template = get_prompt_template(name)
        prompt = str(template.get("prompt") or "").strip()
        return prompt if prompt else str(fallback or "")
    except Exception:
        return str(fallback or "")
