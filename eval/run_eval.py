import json
from pathlib import Path
from application.services.content_service import ContentService
from domain.models.schemas import ContentAnalyzeRequest


def main():
    service = ContentService()
    cases = [json.loads(x) for x in Path("eval/test_cases.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    total, correct = 0, 0
    for c in cases:
        req = ContentAnalyzeRequest(
            raw_content=c["raw_content"],
            platform=c.get("platform", "xiaohongshu"),
            content_type=c.get("content_type", "product_review"),
            task_type="review_and_rewrite",
        )
        resp = service.analyze(req)
        total += 1
        ok = resp.risk_level == c.get("expected_risk_level")
        correct += int(ok)
        print(f"[{'OK' if ok else 'FAIL'}] expected={c.get('expected_risk_level')} got={resp.risk_level} text={c['raw_content'][:20]}")
    print(f"accuracy={correct}/{total}")


if __name__ == "__main__":
    main()
