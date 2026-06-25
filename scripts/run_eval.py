import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from application.services.content_service import ContentService
from domain.models.schemas import ContentAnalyzeRequest


EVAL_FILE = Path("eval/test_cases.jsonl")
OUTPUT_DIR = Path("logs/eval_runs")


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []

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


def trace_nodes(trace: List[Dict[str, Any]]) -> List[str]:
    return [item.get("node", "") for item in trace]


def trace_messages(trace: List[Dict[str, Any]]) -> List[str]:
    return [item.get("message", "") for item in trace]


def detect_llm_usage(trace: List[Dict[str, Any]]) -> str:
    messages = " ".join(trace_messages(trace))

    if "使用 LLM" in messages or "LLM 生成" in messages:
        return "llm"

    if "规则兜底" in messages:
        return "fallback"

    if "LLM 调用失败" in messages or "LLM 输出格式不符合要求" in messages:
        return "fallback_after_llm_error"

    return "unknown"


def check_case(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    risk_items = result.get("risk_items", [])
    hit_terms = [item.get("text", "") for item in risk_items]
    nodes = trace_nodes(result.get("trace", []))

    expected_terms = case.get("expected_terms", [])
    expected_risk_level = case.get("expected_risk_level")
    expected_optimize = case.get("expected_optimize", True)
    expected_versions = case.get("expected_versions", True)

    checks = {}

    checks["risk_level_ok"] = result.get("risk_level") == expected_risk_level

    if expected_terms:
        checks["risk_terms_ok"] = all(
            any(term in hit for hit in hit_terms)
            for term in expected_terms
        )
    else:
        checks["risk_terms_ok"] = len(hit_terms) == 0 or result.get("risk_level") in ["low", "unknown"]

    if expected_optimize:
        checks["route_optimize_ok"] = "optimize_node" in nodes
    else:
        checks["route_optimize_ok"] = "optimize_node" not in nodes

    versions = result.get("rewritten_versions", [])
    titles = result.get("title_suggestions", [])

    if expected_versions:
        checks["versions_ok"] = len(versions) > 0
    else:
        checks["versions_ok"] = len(versions) == 0

    checks["titles_ok"] = len(titles) > 0 if expected_optimize else True

    checks["final_report_ok"] = bool(result.get("final_report"))

    passed = all(checks.values())

    return {
        "case_id": case.get("case_id"),
        "passed": passed,
        "checks": checks,
        "expected": {
            "risk_level": expected_risk_level,
            "terms": expected_terms,
            "expected_optimize": expected_optimize,
            "expected_versions": expected_versions,
        },
        "actual": {
            "risk_level": result.get("risk_level"),
            "score": result.get("score"),
            "hit_terms": hit_terms,
            "nodes": nodes,
            "title_count": len(titles),
            "version_count": len(versions),
            "llm_usage": detect_llm_usage(result.get("trace", [])),
        },
    }


def main() -> None:
    if not EVAL_FILE.exists():
        raise FileNotFoundError(f"Eval file not found: {EVAL_FILE}")

    cases = load_jsonl(EVAL_FILE)
    service = ContentService()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_rows = []

    pass_count = 0

    for case in cases:
        req = ContentAnalyzeRequest(
            raw_content=case["raw_content"],
            platform=case["platform"],
            content_type=case["content_type"],
            task_type=case["task_type"],
            target_audience=case.get("target_audience", "普通用户"),
            user_id="eval_user",
        )

        response = service.analyze(req)
        result = response.model_dump()

        check = check_case(case, result)

        if check["passed"]:
            pass_count += 1

        detail_rows.append(
            {
                "case": case,
                "check": check,
                "result": result,
            }
        )

        status = "PASS" if check["passed"] else "FAIL"
        print(
            f"[{status}] {case['case_id']} | "
            f"risk={result.get('risk_level')} | "
            f"score={result.get('score')} | "
            f"llm={check['actual']['llm_usage']} | "
            f"nodes={','.join(check['actual']['nodes'])}"
        )

    total = len(cases)
    pass_rate = pass_count / total if total else 0

    summary = {
        "run_id": run_id,
        "total": total,
        "passed": pass_count,
        "failed": total - pass_count,
        "pass_rate": round(pass_rate, 4),
        "detail_file": f"logs/eval_runs/eval_detail_{run_id}.jsonl",
    }

    save_json(OUTPUT_DIR / f"eval_summary_{run_id}.json", summary)
    save_jsonl(OUTPUT_DIR / f"eval_detail_{run_id}.jsonl", detail_rows)

    print()
    print("Evaluation finished.")
    print(f"Total: {total}")
    print(f"Passed: {pass_count}")
    print(f"Failed: {total - pass_count}")
    print(f"Pass rate: {pass_rate:.2%}")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()