import time
from fastapi import FastAPI, Request
from loguru import logger

from config.settings import get_settings
from interfaces.http.exceptions import register_exception_handlers
from interfaces.http.routers.health import router as health_router
from interfaces.http.routers.content import router as content_router
from interfaces.http.routers.history import router as history_router
from interfaces.http.routers.feedback import router as feedback_router
from interfaces.http.routers.knowledge import router as knowledge_router
from interfaces.http.routers.prompts import router as prompts_router


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} {response.status_code} {elapsed}ms")
    return response


register_exception_handlers(app)

app.include_router(health_router)
app.include_router(content_router, prefix=settings.api_prefix)
app.include_router(history_router, prefix=settings.api_prefix)
app.include_router(feedback_router, prefix=settings.api_prefix)
app.include_router(knowledge_router, prefix=settings.api_prefix)
app.include_router(prompts_router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "message": "ContentPilot API is running",
        "docs": "/docs",
        "health": "/health",
    }
