from fastapi.testclient import TestClient

from application.services.content_service import ContentService
from domain.models.schemas import ContentAnalyzeRequest
from interfaces.http.main import app


client = TestClient(app)
TEST_USER = "integration_test_user"


def _payload(raw_content: str = "这款产品7天见效，绝对安全，无副作用，大家快冲。"):
    return {
        "raw_content": raw_content,
        "platform": "xiaohongshu",
        "content_type": "product_review",
        "task_type": "review_and_rewrite",
        "user_id": TEST_USER,
    }


def test_analyze_history_reuse_and_refine_flow():
    analyze = client.post("/api/v1/content/analyze", json=_payload())
    assert analyze.status_code == 200
    result = analyze.json()
    assert result["task_id"]
    assert result["final_report"]
    assert [v["version_type"] for v in result["rewritten_versions"]] == [
        "safe_compliance",
        "conversion_enhanced",
    ]

    detail = client.get(f"/api/v1/history/tasks/{result['task_id']}")
    assert detail.status_code == 200
    assert detail.json()["task"]["task_id"] == result["task_id"]

    reuse = client.get(f"/api/v1/history/tasks/{result['task_id']}/reuse")
    assert reuse.status_code == 200
    assert reuse.json()["payload"]["raw_content"]

    refine = client.post(
        "/api/v1/content/refine",
        json={
            "task_id": result["task_id"],
            "instruction": "更短一些，语气更自然。",
            "platform": "xiaohongshu",
            "content_type": "product_review",
            "user_id": TEST_USER,
        },
    )
    assert refine.status_code == 200
    assert refine.json()["parent_task_id"] if "parent_task_id" in refine.json() else refine.json()["task_id"]

    messages = client.get(f"/api/v1/history/conversations/{result['task_id']}/messages")
    assert messages.status_code == 200
    assert len(messages.json()["items"]) >= 2


def test_history_delete_flow():
    analyze = client.post("/api/v1/content/analyze", json=_payload("普通体验分享，想优化得更自然一点。"))
    assert analyze.status_code == 200
    task_id = analyze.json()["task_id"]

    delete = client.delete(f"/api/v1/history/tasks/{task_id}")
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True

    detail = client.get(f"/api/v1/history/tasks/{task_id}")
    assert detail.status_code == 200
    assert detail.json()["task"] is None


def test_batch_feedback_and_knowledge_flow():
    batch = client.post(
        "/api/v1/content/batch",
        json={**_payload("帮我把这段新品介绍适配到多个平台。"), "platforms": ["xiaohongshu", "wechat"]},
    )
    assert batch.status_code == 200
    assert len(batch.json()["items"]) == 2

    feedback = client.post(
        "/api/v1/feedback",
        json={
            "task_id": batch.json()["items"][0]["task_id"],
            "user_id": TEST_USER,
            "rating": 4,
            "comment": "更喜欢短句和克制表达。",
            "remember_as_preference": True,
        },
    )
    assert feedback.status_code == 200

    item = client.post(
        "/api/v1/knowledge/items",
        json={
            "collection": "general",
            "title": "integration-test-knowledge",
            "body": "短句、克制表达、避免绝对化承诺。",
            "platform": "xiaohongshu",
            "content_type": "product_review",
            "tags": ["test"],
        },
    )
    assert item.status_code == 200
    item_id = item.json()["id"]

    listing = client.get("/api/v1/knowledge/items", params={"limit": 10})
    assert listing.status_code == 200
    assert any(row["id"] == item_id for row in listing.json()["items"])

    delete = client.delete(f"/api/v1/knowledge/items/{item_id}")
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True


def test_method_not_allowed_response_includes_allowed_methods():
    response = client.get("/api/v1/content/analyze")

    assert response.status_code == 405
    body = response.json()
    assert body["status"] == "error"
    assert body["code"] == 405
    assert body["detail"]["path"] == "/api/v1/content/analyze"
    assert body["detail"]["method"] == "GET"
    assert "POST" in body["detail"]["allowed_methods"]


def test_chinese_high_risk_sample_is_detected():
    payload = _payload(
        "\u8fd9\u6b3e\u4ea7\u54c17\u5929\u89c1\u6548\uff0c"
        "\u7edd\u5bf9\u5b89\u5168\uff0c\u65e0\u526f\u4f5c\u7528\uff0c"
        "\u5927\u5bb6\u5feb\u51b2\u3002"
    )
    response = client.post("/api/v1/content/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "high"
    assert body["score"] < 60
    assert {"\u7edd\u5bf9", "\u65e0\u526f\u4f5c\u7528", "7\u5929\u89c1\u6548"}.issubset(
        {item["text"] for item in body["risk_items"]}
    )


def test_response_mapping_tolerates_partial_agent_state():
    service = object.__new__(ContentService)
    req = ContentAnalyzeRequest(raw_content="content")
    state = {
        "task_id": 123,
        "score": "not-a-number",
        "risk_report": {"items": [{"text": "\u7edd\u5bf9"}]},
        "rewritten_versions": [{"title": None, "score": None}],
        "title_suggestions": "not-a-list",
        "evidence_pack": [],
        "trace": ["bad-trace"],
    }

    response = service._state_to_response(state, req)

    assert response.task_id == "123"
    assert response.score == 0
    assert response.risk_items[0].text == "\u7edd\u5bf9"
    assert response.risk_items[0].risk_type == "unknown"
    assert response.rewritten_versions[0].title == ""
    assert response.rewritten_versions[0].score == 0
    assert response.title_suggestions == []
