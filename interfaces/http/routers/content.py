import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger

from domain.models.schemas import (
    BatchAnalyzeResponse,
    ContentAnalyzeRequest,
    ContentAnalyzeResponse,
    RefineRequest,
)
from application.services.content_service import ContentService

router = APIRouter(prefix="/content", tags=["content"])
service = ContentService()


@router.post("/analyze", response_model=ContentAnalyzeResponse)
def analyze_content(req: ContentAnalyzeRequest):
    return service.analyze(req)


@router.post("/batch", response_model=BatchAnalyzeResponse)
def batch_content(req: ContentAnalyzeRequest):
    return service.batch_analyze(req)


@router.post("/refine", response_model=ContentAnalyzeResponse)
def refine_content(req: RefineRequest):
    return service.refine(req)


@router.post("/stream")
def stream_content(req: ContentAnalyzeRequest):
    def event_generator():
        try:
            yield 'data: {"event": "connected"}\n\n'
            for event in service.stream(req):
                data = json.dumps(event, ensure_ascii=False, default=str)
                yield f"data: {data}\n\n"
        except Exception as exc:
            logger.exception("content stream failed")
            data = json.dumps(
                {
                    "event": "error",
                    "message": str(exc),
                },
                ensure_ascii=False,
                default=str,
            )
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
