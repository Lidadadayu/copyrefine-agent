from typing import Any, Dict, Generator, List

from application.agents.graph import build_workflow
from domain.models.schemas import (
    BatchAnalyzeResponse,
    ContentAnalyzeRequest,
    ContentAnalyzeResponse,
    ContentVersion,
    RefineRequest,
    RiskItem,
)
from infrastructure.database.sqlite import (
    append_conversation_message,
    fetch_task,
    fetch_task_versions,
    get_user_preference,
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


class ContentService:
    def __init__(self):
        self.workflow = build_workflow()

    def _state_to_response(
        self,
        state: Dict[str, Any],
        req: ContentAnalyzeRequest,
    ) -> ContentAnalyzeResponse:
        risk_report = _safe_dict(state.get("risk_report"))
        risk_items = []
        for item in _safe_list(risk_report.get("items")):
            item = _safe_dict(item)
            risk_items.append(
                RiskItem(
                    text=_safe_str(item.get("text")),
                    risk_type=_safe_str(item.get("risk_type"), "unknown"),
                    severity=_safe_str(item.get("severity"), "medium"),
                    suggestion=_safe_str(item.get("suggestion")),
                )
            )

        versions = []
        for item in _safe_list(state.get("rewritten_versions")):
            item = _safe_dict(item)
            versions.append(
                ContentVersion(
                    version_type=_safe_str(item.get("version_type")),
                    title=_safe_str(item.get("title")),
                    body=_safe_str(item.get("body")),
                    score=_safe_int(item.get("score"), 0),
                    notes=_safe_str(item.get("notes")),
                )
            )

        return ContentAnalyzeResponse(
            task_id=_safe_str(state.get("task_id")),
            platform=state.get("detected_platform") or req.platform or "",
            content_type=state.get("detected_content_type") or req.content_type or "",
            risk_level=_safe_str(state.get("risk_level"), "unknown"),
            score=_safe_int(state.get("score"), 0),
            risk_items=risk_items,
            title_suggestions=[_safe_str(t) for t in _safe_list(state.get("title_suggestions"))],
            rewritten_versions=versions,
            evidence_pack=_safe_dict(state.get("evidence_pack")),
            final_report=_safe_str(state.get("final_report")),
            trace=[_safe_dict(item) for item in _safe_list(state.get("trace"))],
        )

    def _with_preferences(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user_id = payload.get("user_id") or "default_user"
        preference = get_user_preference(user_id)
        if preference:
            payload["user_preference"] = preference
        return payload

    def _conversation_summary(self, response: ContentAnalyzeResponse) -> str:
        versions = response.rewritten_versions[:2]
        version_lines = [
            f"{item.version_type}: {item.title}（{item.score}分）"
            for item in versions
        ]
        risk_terms = "、".join(item.text for item in response.risk_items[:4]) or "未发现明显高风险表达"
        return (
            f"风险等级：{response.risk_level}，评分：{response.score}/100。\n"
            f"风险提示：{risk_terms}\n"
            f"推荐版本：{'; '.join(version_lines) if version_lines else '本轮未生成正文改写版本'}"
        )

    def _record_conversation(
        self,
        response: ContentAnalyzeResponse,
        user_text: str,
        assistant_text: str,
        conversation_id: str | None,
        user_id: str,
    ) -> None:
        cid = conversation_id or response.task_id
        append_conversation_message(cid, response.task_id, user_id, "user", user_text)
        append_conversation_message(cid, response.task_id, user_id, "assistant", assistant_text)

    def _target_platforms(self, req: ContentAnalyzeRequest) -> List[str]:
        platforms = [p for p in req.platforms if p]
        if platforms:
            return list(dict.fromkeys(platforms))
        return [req.platform or "xiaohongshu"]

    def analyze(self, req: ContentAnalyzeRequest) -> ContentAnalyzeResponse:
        payload = self._with_preferences(req.model_dump())
        state = self.workflow.run(payload)
        response = self._state_to_response(state, req)
        user_text = f"继续修改：{req.refine_instruction}" if req.refine_instruction else req.raw_content
        self._record_conversation(
            response=response,
            user_text=user_text,
            assistant_text=self._conversation_summary(response),
            conversation_id=req.conversation_id,
            user_id=req.user_id,
        )
        return response

    def batch_analyze(self, req: ContentAnalyzeRequest) -> BatchAnalyzeResponse:
        items = []
        for platform in self._target_platforms(req):
            single = req.model_copy(update={"platform": platform, "platforms": []})
            items.append(self.analyze(single))
        return BatchAnalyzeResponse(items=items)

    def refine(self, req: RefineRequest) -> ContentAnalyzeResponse:
        source = self._resolve_refine_source(req)
        raw_content = source["raw_content"]
        instruction = req.instruction.strip()

        # 用户继续修改时，正文仍然只传文案本身。
        # 修改要求单独进入 refine_instruction，避免把 instruction 当成正文内容。
        analyze_req = ContentAnalyzeRequest(
            raw_content=raw_content,
            platform=req.platform or source.get("platform") or "xiaohongshu",
            platforms=req.platforms,
            content_type=req.content_type or source.get("content_type") or "general",
            task_type=req.task_type or "review_and_rewrite",
            target_audience=req.target_audience,
            rewrite_intensity=req.rewrite_intensity,
            expression_strength=req.expression_strength,
            user_id=req.user_id,
            refine_instruction=instruction,
            parent_task_id=req.task_id,
            conversation_id=req.conversation_id or req.task_id,
            original_content=req.original_content or source.get("original_content") or raw_content,
            previous_output=req.previous_output,
        )
        return self.analyze(analyze_req)

    def _resolve_refine_source(self, req: RefineRequest) -> Dict[str, Any]:
        if req.selected_version_body and req.selected_version_body.strip():
            return {
                "raw_content": req.selected_version_body.strip(),
                "platform": req.platform,
                "content_type": req.content_type,
                "original_content": req.original_content or req.raw_content,
            }

        if req.raw_content and req.raw_content.strip():
            return {
                "raw_content": req.raw_content.strip(),
                "platform": req.platform,
                "content_type": req.content_type,
                "original_content": req.original_content or req.raw_content.strip(),
            }

        if not req.task_id:
            raise ValueError("task_id or raw_content is required for refine")

        task = fetch_task(req.task_id)
        if not task:
            raise ValueError(f"task not found: {req.task_id}")

        raw_content = task.get("raw_content") or ""
        versions = fetch_task_versions(req.task_id)

        if req.version_id:
            selected = next((v for v in versions if int(v.get("id", 0)) == req.version_id), None)
            if selected:
                raw_content = selected.get("body") or raw_content
        elif versions:
            raw_content = versions[0].get("body") or raw_content

        return {
            "raw_content": raw_content,
            "platform": task.get("platform"),
            "content_type": task.get("content_type"),
            "original_content": task.get("raw_content"),
        }

    def stream(self, req: ContentAnalyzeRequest) -> Generator[Dict[str, Any], None, None]:
        for event in self.workflow.stream(self._with_preferences(req.model_dump())):
            if event.get("event") == "finished":
                final_state = event.get("result", {})
                response = self._state_to_response(final_state, req)
                yield {
                    "event": "finished",
                    "result": response.model_dump(),
                }
            else:
                yield event
