from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import select, text

from app.api.router import root_router
from app.core.logging import setup_logging
from app.db.models import User
from app.db.seed.seed_db import seed
from app.db.session import get_engine, get_sessionmaker
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    get_sessionmaker()
    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(select(User.id).limit(1))
        if result.scalar_one_or_none() is None:
            await seed()
    logger.info("Application started")
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(title="App Scaffold", version="1.0.0", lifespan=lifespan)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(root_router)
    return app


app = create_app()
