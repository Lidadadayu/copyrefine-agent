from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        headers = getattr(exc, "headers", None) or {}
        if exc.status_code == 405:
            allowed_methods = headers.get("Allow") or headers.get("allow")
            content = {
                "status": "error",
                "code": 405,
                "message": "Method Not Allowed",
                "detail": {
                    "path": request.url.path,
                    "method": request.method,
                    "allowed_methods": allowed_methods,
                    "hint": "Use one of the allowed HTTP methods for this API path.",
                },
            }
            return JSONResponse(status_code=405, content=content, headers=headers)

        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "code": exc.status_code, "message": exc.detail},
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "code": 422,
                "message": "request validation failed",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "code": 400, "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"unhandled request error: {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": 500,
                "message": "internal server error",
                "detail": str(exc),
            },
        )
