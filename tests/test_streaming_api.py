from fastapi.testclient import TestClient

from interfaces.http.main import app


def test_content_stream_reaches_finished_event():
    client = TestClient(app)
    payload = {
        "raw_content": "这款产品7天见效，绝对安全，无副作用，大家快冲。",
        "platform": "xiaohongshu",
        "content_type": "product_review",
        "task_type": "review_and_rewrite",
        "user_id": "default_user",
    }

    events = []
    with client.stream("POST", "/api/v1/content/stream", json=payload) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line:
                events.append(line)

    assert any('"event": "connected"' in line for line in events)
    assert any('"event": "finished"' in line for line in events)
    assert not any('"event": "error"' in line for line in events)
