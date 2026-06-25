from __future__ import annotations
# ruff: noqa: E402

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import csv
import json
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from application.services.content_service import ContentService
from domain.models.schemas import ContentAnalyzeRequest
from infrastructure.tools.risk_matcher import match_risks


DEFAULT_EVAL_FILE = Path("eval/test_cases.jsonl")
DEFAULT_OUTPUT_DIR = Path("eval/reports")
RISK_ORDER = {"unknown": 0, "low": 1, "medium": 2, "high": 3}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "passed",
        "expected_risk_level",
        "actual_risk_level",
        "score",
        "risk_level_ok",
        "risk_terms_ok",
        "rewrite_success",
        "residual_risk_count",
        "title_count",
        "version_count",
        "llm_usage",
        "latency_ms",
        "error",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def trace_nodes(trace: List[Dict[str, Any]]) -> List[str]:
    return [str(item.get("node", "")) for item in trace]


def trace_messages(trace: List[Dict[str, Any]]) -> List[str]:
    return [str(item.get("message", "")) for item in trace]


def detect_llm_usage(trace: List[Dict[str, Any]]) -> str:
    messages = " ".join(trace_messages(trace))
    if "使用 LLM" in messages or "LLM 生成" in messages:
        return "llm"
    if "LLM 调用失败" in messages or "LLM 输出格式不符合要求" in messages:
        return "fallback_after_llm_error"
    if "规则兜底" in messages:
        return "fallback"
    return "unknown"


def risk_terms_ok(expected_terms: List[str], hit_terms: List[str], expected_risk_level: str) -> bool:
    if expected_terms:
        return all(any(term in hit for hit in hit_terms) for term in expected_terms)
    return len(hit_terms) == 0 or expected_risk_level in {"low", "unknown"}


def residual_risks(versions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for version in versions:
        body = str(version.get("body") or "")
        for item in match_risks(body):
            item = dict(item)
            item["version_type"] = str(version.get("version_type") or "")
            rows.append(item)
    return rows


def evaluate_case(case: Dict[str, Any], service: ContentService) -> Dict[str, Any]:
    start = time.perf_counter()
    case_id = str(case.get("case_id") or "")

    try:
        req = ContentAnalyzeRequest(
            raw_content=str(case["raw_content"]),
            platform=case.get("platform", "xiaohongshu"),
            content_type=case.get("content_type", "product_review"),
            task_type=case.get("task_type", "review_and_rewrite"),
            target_audience=case.get("target_audience", "普通用户"),
            user_id="eval_user",
        )
        response = service.analyze(req)
        result = response.model_dump()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        risk_items = result.get("risk_items", []) or []
        hit_terms = [str(item.get("text") or "") for item in risk_items]
        versions = result.get("rewritten_versions", []) or []
        titles = result.get("title_suggestions", []) or []
        trace = result.get("trace", []) or []
        nodes = trace_nodes(trace)
        residual = residual_risks(versions)

        expected_risk_level = str(case.get("expected_risk_level") or "unknown")
        expected_terms = [str(term) for term in case.get("expected_terms", [])]
        expected_optimize = bool(case.get("expected_optimize", True))
        expected_versions = bool(case.get("expected_versions", True))

        checks = {
            "risk_level_ok": str(result.get("risk_level")) == expected_risk_level,
            "risk_terms_ok": risk_terms_ok(expected_terms, hit_terms, expected_risk_level),
            "route_optimize_ok": ("optimize_node" in nodes) if expected_optimize else ("optimize_node" not in nodes),
            "versions_ok": (len(versions) > 0) if expected_versions else (len(versions) == 0),
            "titles_ok": (len(titles) > 0) if expected_optimize else True,
            "final_report_ok": bool(result.get("final_report")),
        }
        checks["rewrite_success"] = checks["versions_ok"] and (len(residual) == 0 if expected_versions else True)
        passed = all(checks.values())

        return {
            "case_id": case_id,
            "passed": passed,
            "checks": checks,
            "case": case,
            "result": result,
            "summary_row": {
                "case_id": case_id,
                "passed": passed,
                "expected_risk_level": expected_risk_level,
                "actual_risk_level": result.get("risk_level"),
                "score": result.get("score"),
                "risk_level_ok": checks["risk_level_ok"],
                "risk_terms_ok": checks["risk_terms_ok"],
                "rewrite_success": checks["rewrite_success"],
                "residual_risk_count": len(residual),
                "title_count": len(titles),
                "version_count": len(versions),
                "llm_usage": detect_llm_usage(trace),
                "latency_ms": latency_ms,
                "error": "",
            },
            "actual": {
                "risk_level": result.get("risk_level"),
                "score": result.get("score"),
                "hit_terms": hit_terms,
                "nodes": nodes,
                "title_count": len(titles),
                "version_count": len(versions),
                "llm_usage": detect_llm_usage(trace),
                "residual_risks": residual,
                "latency_ms": latency_ms,
            },
        }

    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "case_id": case_id,
            "passed": False,
            "checks": {},
            "case": case,
            "result": {},
            "summary_row": {
                "case_id": case_id,
                "passed": False,
                "expected_risk_level": case.get("expected_risk_level"),
                "actual_risk_level": "error",
                "score": "",
                "risk_level_ok": False,
                "risk_terms_ok": False,
                "rewrite_success": False,
                "residual_risk_count": "",
                "title_count": 0,
                "version_count": 0,
                "llm_usage": "error",
                "latency_ms": latency_ms,
                "error": str(exc),
            },
            "actual": {"error": str(exc), "latency_ms": latency_ms},
        }


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def build_metrics(details: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(details)
    rows = [item["summary_row"] for item in details]
    passed = sum(1 for item in details if item.get("passed"))
    high_cases = [item for item in details if item.get("case", {}).get("expected_risk_level") == "high"]
    low_cases = [item for item in details if item.get("case", {}).get("expected_risk_level") == "low"]
    expected_rewrite_cases = [item for item in details if item.get("case", {}).get("expected_versions", True)]
    latencies = [float(row.get("latency_ms") or 0) for row in rows]

    risk_correct = sum(1 for row in rows if row.get("risk_level_ok") is True)
    term_correct = sum(1 for row in rows if row.get("risk_terms_ok") is True)
    residual_cases = sum(1 for row in rows if int(row.get("residual_risk_count") or 0) > 0)

    high_recall = 0.0
    if high_cases:
        high_recall = sum(
            1 for item in high_cases
            if RISK_ORDER.get(str(item.get("result", {}).get("risk_level")), 0) >= RISK_ORDER["high"]
        ) / len(high_cases)

    low_false_positive_rate = 0.0
    if low_cases:
        low_false_positive_rate = sum(
            1 for item in low_cases
            if RISK_ORDER.get(str(item.get("result", {}).get("risk_level")), 0) >= RISK_ORDER["medium"]
        ) / len(low_cases)

    rewrite_success_rate = 0.0
    if expected_rewrite_cases:
        rewrite_success_rate = sum(
            1 for item in expected_rewrite_cases
            if item.get("summary_row", {}).get("rewrite_success") is True
        ) / len(expected_rewrite_cases)

    llm_count = sum(1 for row in rows if row.get("llm_usage") == "llm")
    fallback_count = sum(1 for row in rows if str(row.get("llm_usage", "")).startswith("fallback"))

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "risk_accuracy": round(risk_correct / total, 4) if total else 0,
        "risk_term_accuracy": round(term_correct / total, 4) if total else 0,
        "high_risk_recall": round(high_recall, 4),
        "low_risk_false_positive_rate": round(low_false_positive_rate, 4),
        "rewrite_success_rate": round(rewrite_success_rate, 4),
        "residual_risk_case_rate": round(residual_cases / len(expected_rewrite_cases), 4) if expected_rewrite_cases else 0,
        "title_generation_success_rate": round(
            sum(1 for row in rows if int(row.get("title_count") or 0) > 0) / total, 4
        ) if total else 0,
        "llm_usage_rate": round(llm_count / total, 4) if total else 0,
        "fallback_count": fallback_count,
        "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else 0,
        "latency_ms_p95": round(_p95(latencies), 2) if latencies else 0,
    }


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(len(values) - 1, int(round((len(values) - 1) * 0.95)))
    return values[idx]


def save_markdown(path: Path, run_id: str, metrics: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    failed = [row for row in rows if not row.get("passed")]

    lines = [
        "# ContentPilot 评测报告",
        "",
        f"- 运行编号：`{run_id}`",
        f"- 样本总数：{metrics['total']}",
        f"- 通过率：{pct(metrics['pass_rate'])}",
        f"- 风险等级准确率：{pct(metrics['risk_accuracy'])}",
        f"- 风险词命中准确率：{pct(metrics['risk_term_accuracy'])}",
        f"- 高风险召回率：{pct(metrics['high_risk_recall'])}",
        f"- 低风险误判率：{pct(metrics['low_risk_false_positive_rate'])}",
        f"- 改写成功率：{pct(metrics['rewrite_success_rate'])}",
        f"- 改写后风险残留样本率：{pct(metrics['residual_risk_case_rate'])}",
        f"- 标题生成成功率：{pct(metrics['title_generation_success_rate'])}",
        f"- LLM 使用率：{pct(metrics['llm_usage_rate'])}",
        f"- 平均耗时：{metrics['latency_ms_avg']} ms",
        f"- P95 耗时：{metrics['latency_ms_p95']} ms",
        "",
        "## 明细结果",
        "",
        "| 样本 | 通过 | 预期风险 | 实际风险 | 评分 | LLM | 耗时(ms) | 问题 |",
        "|---|---:|---|---|---:|---|---:|---|",
    ]

    for row in rows:
        problem = row.get("error") or ""
        if not problem and not row.get("passed"):
            failed_checks = [key for key, value in row.get("checks", {}).items() if not value]
            problem = ", ".join(failed_checks)
        lines.append(
            f"| {row.get('case_id')} | {'是' if row.get('passed') else '否'} | "
            f"{row.get('expected_risk_level')} | {row.get('actual_risk_level')} | "
            f"{row.get('score')} | {row.get('llm_usage')} | {row.get('latency_ms')} | {problem} |"
        )

    if failed:
        lines.extend(["", "## 未通过样本", ""])
        for row in failed:
            lines.append(f"### {row.get('case_id')}")
            lines.append(f"- 预期风险：{row.get('expected_risk_level')}")
            lines.append(f"- 实际风险：{row.get('actual_risk_level')}")
            lines.append(f"- 错误信息：{row.get('error') or '检查项未通过'}")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ContentPilot evaluation and generate JSON/CSV/Markdown reports.")
    parser.add_argument("--file", default=str(DEFAULT_EVAL_FILE), help="eval jsonl file")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="report output directory")
    args = parser.parse_args()

    eval_file = Path(args.file)
    output_dir = Path(args.output_dir)
    if not eval_file.exists():
        raise FileNotFoundError(f"Eval file not found: {eval_file}")

    service = ContentService()
    cases = load_jsonl(eval_file)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    details: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []

    for case in cases:
        detail = evaluate_case(case, service)
        details.append(detail)
        row = dict(detail["summary_row"])
        row["checks"] = detail.get("checks", {})
        rows.append(row)

        status = "PASS" if detail.get("passed") else "FAIL"
        actual = detail.get("actual", {})
        print(
            f"[{status}] {detail.get('case_id')} | "
            f"risk={actual.get('risk_level', 'error')} | "
            f"llm={actual.get('llm_usage', 'error')} | "
            f"latency={actual.get('latency_ms')}ms"
        )

    metrics = build_metrics(details)
    summary = {
        "run_id": run_id,
        "eval_file": str(eval_file),
        "metrics": metrics,
        "files": {
            "summary_json": str(output_dir / f"eval_summary_{run_id}.json"),
            "detail_jsonl": str(output_dir / f"eval_detail_{run_id}.jsonl"),
            "summary_csv": str(output_dir / f"eval_summary_{run_id}.csv"),
            "report_md": str(output_dir / f"eval_report_{run_id}.md"),
        },
    }

    save_json(output_dir / f"eval_summary_{run_id}.json", summary)
    save_jsonl(output_dir / f"eval_detail_{run_id}.jsonl", details)
    save_csv(output_dir / f"eval_summary_{run_id}.csv", rows)
    save_markdown(output_dir / f"eval_report_{run_id}.md", run_id, metrics, rows)

    print("\nEvaluation finished.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
