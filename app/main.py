"""FastAPI application factory.

Run:  uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router
from app.config import Settings, get_settings
from app.database.repository import TicketRepository
from app.database.session import create_db_engine, init_db, make_session_factory
from app.policies.automation_policy import AutomationPolicy
from app.services.decision_service import DecisionService
from app.services.jev_client import JevClient, build_jev_client
from app.utils.logging import configure_logging

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None, jev_client: JevClient | None = None) -> FastAPI:
    """Build the app. Tests pass their own settings and a JevClient wired to a mock transport."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.log_level)
        engine = create_db_engine(settings.database_url)
        init_db(engine)
        jev = jev_client or build_jev_client(settings)  # fails fast on a missing API key
        app.state.settings = settings
        app.state.engine = engine
        app.state.repository = TicketRepository(make_session_factory(engine))
        app.state.decision_service = DecisionService(jev, AutomationPolicy.from_settings(settings))
        model = settings.jev_model if jev.backend_name == "typesafe" else "mock-offline"
        logger.info(
            "startup", extra={"fields": {"jev_backend": jev.backend_name, "jev_model": model}}
        )
        if jev.backend_name == "mock":
            logger.warning("OFFLINE MOCK BACKEND: decisions are NOT produced by Jev")
        yield
        await jev.aclose()
        engine.dispose()

    app = FastAPI(
        title="Jev Support Decision Engine",
        version="1.0.0",
        description="Classifies, prioritizes and routes support tickets with Jev "
        "(TypeSafe System One model) and an explicit Python automation policy.",
        lifespan=lifespan,
    )
    app.include_router(router)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request",
            extra={
                "fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            },
        )
        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("database_error", extra={"fields": {"exc_type": type(exc).__name__}})
        return JSONResponse(status_code=503, content={"detail": "database unavailable"})

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Never leak internals (stack traces, SQL, payloads) to clients.
        logger.error("unhandled_error", extra={"fields": {"exc_type": type(exc).__name__}})
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    return app


app = create_app()
