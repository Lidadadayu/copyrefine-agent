from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

from fastapi import APIRouter

from config.settings import get_settings
from infrastructure.database.sqlite import DB_PATH, get_conn, init_db

router = APIRouter(tags=["health"])


CheckResult = Dict[str, Any]


DATA_FILES = {
    "platform_rules": Path("data/platform_rules.jsonl"),
    "risk_expressions": Path("data/risk_expressions.jsonl"),
    "content_cases": Path("data/content_cases.jsonl"),
    "seed_history": Path("data/seed_history.jsonl"),
}


REQUIRED_TABLES = [
    "content_tasks",
    "content_versions",
    "user_feedback",
    "user_preferences",
    "knowledge_items",
]


def _now_ms() -> float:
    return time.perf_counter() * 1000


def _result(name: str, status: str, message: str, latency_ms: float, details: Dict[str, Any] | None = None) -> CheckResult:
    return {
        "name": name,
        "status": status,
        "message": message,
        "latency_ms": round(latency_ms, 2),
        "details": details or {},
    }


def _safe_check(name: str, func: Callable[[], CheckResult]) -> CheckResult:
    start = _now_ms()
    try:
        return func()
    except Exception as exc:
        return _result(
            name=name,
            status="error",
            message=str(exc),
            latency_ms=_now_ms() - start,
            details={"exception_type": exc.__class__.__name__},
        )


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _check_app_config() -> CheckResult:
    start = _now_ms()
    settings = get_settings()
    details = {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "api_prefix": settings.api_prefix,
        "database_url": settings.database_url,
        "enable_langgraph": settings.enable_langgraph,
        "enable_llm_optimize": settings.enable_llm_optimize,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_api_key_present": bool(settings.llm_api_key),
    }
    return _result("app_config", "ok", "应用配置加载正常", _now_ms() - start, details)


def _check_database() -> CheckResult:
    start = _now_ms()
    init_db()
    conn = get_conn()
    try:
        table_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        tables = {row["name"] for row in table_rows}
        missing = [table for table in REQUIRED_TABLES if table not in tables]

        counts: Dict[str, int] = {}
        for table in REQUIRED_TABLES:
            if table in tables:
                counts[table] = int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"])

        details = {
            "db_path": str(DB_PATH.resolve()),
            "exists": DB_PATH.exists(),
            "tables": sorted(tables),
            "missing_tables": missing,
            "counts": counts,
        }

        if missing:
            return _result("sqlite", "error", "SQLite 表结构不完整", _now_ms() - start, details)

        return _result("sqlite", "ok", "SQLite 数据库正常", _now_ms() - start, details)
    finally:
        conn.close()


def _check_data_files() -> CheckResult:
    start = _now_ms()
    files: Dict[str, Any] = {}
    missing: List[str] = []

    for name, path in DATA_FILES.items():
        exists = path.exists()
        if not exists:
            missing.append(name)
        files[name] = {
            "path": str(path),
            "exists": exists,
            "line_count": _line_count(path),
            "size_bytes": path.stat().st_size if exists else 0,
        }

    status = "ok" if not missing else "error"
    message = "数据文件正常" if not missing else f"缺少数据文件：{', '.join(missing)}"
    return _result("data_files", status, message, _now_ms() - start, {"files": files})


def _check_chroma() -> CheckResult:
    start = _now_ms()
    chroma_available = importlib.util.find_spec("chromadb") is not None
    details: Dict[str, Any] = {
        "chromadb_installed": chroma_available,
        "persist_dir": str(Path("data/chroma").resolve()),
    }

    if not chroma_available:
        return _result("chroma", "warn", "未安装 chromadb，系统会退回 BM25 检索", _now_ms() - start, details)

    from infrastructure.retrieval.vector_store import ChromaVectorStore

    store = ChromaVectorStore("health_probe", persist_dir="data/chroma")
    details["store_enabled"] = bool(getattr(store, "enabled", False))

    if not getattr(store, "enabled", False):
        return _result("chroma", "warn", "Chroma 初始化失败，系统会退回 BM25 检索", _now_ms() - start, details)

    return _result("chroma", "ok", "Chroma 向量检索组件可用", _now_ms() - start, details)


def _check_retrieval() -> CheckResult:
    start = _now_ms()
    from infrastructure.retrieval.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever()
    result = retriever.retrieve(
        queries=["小红书 产品种草 绝对安全 无副作用 风险改写"],
        routes=["platform_rules", "risk_expressions", "content_cases", "user_history"],
        platform="xiaohongshu",
        content_type="product_review",
    )
    counts = {key: len(value) for key, value in result.items()}
    total = sum(counts.values())
    details = {"counts": counts, "total": total}

    if total == 0:
        return _result("retrieval", "warn", "检索链路可运行，但没有召回结果", _now_ms() - start, details)

    return _result("retrieval", "ok", "混合检索链路正常", _now_ms() - start, details)


def _check_llm() -> CheckResult:
    start = _now_ms()
    settings = get_settings()
    enabled = bool(settings.enable_llm_optimize)
    has_key = bool(settings.llm_api_key)
    details = {
        "enable_llm_optimize": enabled,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_api_key_present": has_key,
        "llm_base_url": settings.llm_base_url,
    }

    if not enabled:
        return _result("llm", "warn", "LLM 优化未启用，系统使用规则兜底", _now_ms() - start, details)

    if enabled and not has_key:
        return _result("llm", "error", "LLM 已启用但缺少 API Key", _now_ms() - start, details)

    return _result("llm", "ok", "LLM 配置已启用", _now_ms() - start, details)


def _check_write_permissions() -> CheckResult:
    start = _now_ms()
    targets = [Path("logs"), Path("data/chroma")]
    details: Dict[str, Any] = {}
    failed: List[str] = []

    for target in targets:
        try:
            target.mkdir(parents=True, exist_ok=True)
            probe = target / ".health_write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            details[str(target)] = "writable"
        except Exception as exc:
            failed.append(str(target))
            details[str(target)] = f"not_writable: {exc}"

    if failed:
        return _result("write_permissions", "error", "部分目录不可写", _now_ms() - start, details)

    return _result("write_permissions", "ok", "运行目录写入权限正常", _now_ms() - start, details)


def _overall_status(checks: List[CheckResult]) -> str:
    statuses = [item.get("status") for item in checks]
    if "error" in statuses:
        return "error"
    if "warn" in statuses:
        return "warn"
    return "ok"


def _diagnostics_payload() -> Dict[str, Any]:
    start = _now_ms()
    checks = [
        _safe_check("app_config", _check_app_config),
        _safe_check("sqlite", _check_database),
        _safe_check("data_files", _check_data_files),
        _safe_check("write_permissions", _check_write_permissions),
        _safe_check("chroma", _check_chroma),
        _safe_check("retrieval", _check_retrieval),
        _safe_check("llm", _check_llm),
    ]
    return {
        "status": _overall_status(checks),
        "service": "ContentPilot",
        "timestamp": datetime_like(),
        "latency_ms": round(_now_ms() - start, 2),
        "checks": checks,
    }


def datetime_like() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@router.get("/health")
def health_check() -> Dict[str, Any]:
    init_db()
    return {
        "status": "ok",
        "database": "sqlite",
        "message": "ContentPilot backend is running",
        "timestamp": datetime_like(),
    }


@router.get("/api/v1/health")
def health_check_api_prefix() -> Dict[str, Any]:
    return health_check()


@router.get("/health/diagnostics")
def health_diagnostics() -> Dict[str, Any]:
    return _diagnostics_payload()


@router.get("/api/v1/health/diagnostics")
def health_diagnostics_api_prefix() -> Dict[str, Any]:
    return _diagnostics_payload()
