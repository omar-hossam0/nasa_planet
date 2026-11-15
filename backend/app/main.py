"""FastAPI application factory."""

from __future__ import annotations

import logging
import secrets

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    analyses,
    catalog,
    comparisons,
    explanations,
    receipts,
    recommendations,
    results,
    spatial,
    spin,
    system,
)
from app.core.config import Settings, get_settings
from app.core.dependencies import build_container
from app.core.exceptions import AppError, ErrorCode
from app.core.logging import REQUEST_ID_HEADER, configure_logging, get_request_id, set_request_id

logger = logging.getLogger(__name__)

DESCRIPTION = """
**Trend Detective - What the Average Hides** backend.

Every endpoint in this build is backed by **deterministic mock data**. There is no
database, no AI/RAG provider, no frontend and no live NASA connection.

Every payload carries `data_mode: "mock"` and a disclaimer. Synthetic slopes are
descriptive only: no significance test is computed, so `p_value` is always `null`
and `inference_status` is `not_computed`.

State is held in process memory and disappears when the server restarts.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "Trend Detective backend workstream"},
        license_info={"name": "Repository default - see project README"},
    )

    app.state.container = build_container(settings)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER],
        )

    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routers(app, settings)
    return app


def _register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        incoming = request.headers.get(REQUEST_ID_HEADER)
        if incoming and 0 < len(incoming) <= 64:
            request_id = incoming
        else:
            request_id = f"req_{secrets.token_hex(6)}"
        set_request_id(request_id)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code.value,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": get_request_id(),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "loc": ".".join(str(part) for part in error.get("loc", ())),
                "msg": error.get("msg", "invalid value"),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "Request validation failed.",
                    "details": {"errors": errors},
                    "request_id": get_request_id(),
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 405:
            code = "METHOD_NOT_ALLOWED"
        else:
            code = "HTTP_ERROR"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": str(exc.detail),
                    "details": {},
                    "request_id": get_request_id(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An unexpected internal error occurred.",
                    "details": {},
                    "request_id": get_request_id(),
                }
            },
        )


def _register_routers(app: FastAPI, settings: Settings) -> None:
    app.include_router(system.router)

    for module in (
        catalog,
        recommendations,
        analyses,
        results,
        spatial,
        comparisons,
        spin,
        explanations,
        receipts,
    ):
        app.include_router(module.router, prefix=settings.api_prefix)


app = create_app()
