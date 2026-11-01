"""FastAPI application factory."""

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, error_body
from app.core.rate_limit import RateLimiter
from app.db.session import build_engine, build_session_factory
from app.services.email_sender import build_email_sender

logger = logging.getLogger("solarops")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(title="SolarOps API", version="0.1.0")
    application.state.settings = settings
    application.state.engine = build_engine(settings.database_url)
    application.state.session_factory = build_session_factory(application.state.engine)
    application.state.email_sender = build_email_sender(settings)
    application.state.limiter = RateLimiter()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Strong-Auth"],
    )
    application.include_router(api_router)

    @application.middleware("http")
    async def correlate(request: Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("request_completed", extra={"request_id": request_id, "method": request.method,
            "path": request.url.path, "status": response.status_code,
            "duration_ms": round((time.monotonic() - started) * 1000, 2)})
        return response

    @application.exception_handler(HTTPException)
    def _http(_request: Request, exc: HTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        message = (
            exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
        )
        return JSONResponse(status_code=exc.status_code, content=error_body(code, message))

    @application.exception_handler(AppError)
    def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @application.exception_handler(RequestValidationError)
    def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[dict[str, Any]] = []
        for item in exc.errors():
            loc = [str(part) for part in item.get("loc", []) if part not in {"body", "query"}]
            details.append({"field": ".".join(loc), "message": item.get("msg", "Invalid value")})
        return JSONResponse(
            status_code=422,
            content=error_body("validation_error", "Check the submitted fields.", details),
        )

    @application.exception_handler(IntegrityError)
    def _integrity(_request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("database_integrity_conflict")
        return JSONResponse(
            status_code=409,
            content=error_body("conflict", "The request conflicts with existing data."),
        )

    @application.exception_handler(OperationalError)
    def _database(_request: Request, exc: OperationalError) -> JSONResponse:
        logger.error("database_unavailable")
        return JSONResponse(
            status_code=503,
            content=error_body("database_unavailable", "The database is not available."),
        )

    @application.exception_handler(Exception)
    def _unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "The request could not be completed."),
        )

    return application


app = create_app()
