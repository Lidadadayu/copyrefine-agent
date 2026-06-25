from application.agents.graph import build_workflow


def test_workflow_run():
    wf = build_workflow()
    state = wf.run({
        "raw_content": "这款产品7天见效，绝对安全，无副作用，大家快冲！",
        "platform": "xiaohongshu",
        "content_type": "product_review",
        "task_type": "review_and_rewrite",
        "user_id": "default_user",
    })
    assert state["risk_level"] in ["high", "medium", "low"]
    assert state["final_report"]
    assert state["rewritten_versions"]
