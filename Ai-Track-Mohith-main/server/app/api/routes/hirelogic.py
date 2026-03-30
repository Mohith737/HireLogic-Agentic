from __future__ import annotations

import asyncio
import importlib
import os
import sys
from collections.abc import Callable, Coroutine
from typing import Any, cast

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_user
from app.db.models import ChatMessage, ChatSession, User

router = APIRouter(prefix="/hirelogic", tags=["hirelogic"])

AGENT_RUNTIME_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "hirelogic_agent")
)
if AGENT_RUNTIME_PATH not in sys.path:
    sys.path.insert(0, AGENT_RUNTIME_PATH)

load_dotenv(os.path.join(AGENT_RUNTIME_PATH, ".env"))


class ChatRequest(BaseModel):
    question: str
    job_id: int | None = None
    session_id: int = 1


class SessionCreateRequest(BaseModel):
    job_id: int | None = None
    title: str = "New Session"


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    del db
    try:
        backend_chat = importlib.import_module("backend_chat")
        run_hirelogic_fn = cast(
            Callable[..., Coroutine[Any, Any, dict[str, Any]]],
            backend_chat.run_hirelogic,
        )

        result: dict[str, Any] = await asyncio.to_thread(
            lambda: asyncio.run(
                run_hirelogic_fn(
                    question=body.question,
                    user_id=str(current_user.id),
                    session_id=body.session_id,
                    job_id=body.job_id,
                )
            )
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc


@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.created_at))
        .limit(50)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": session.id,
            "title": session.title or "Untitled Session",
            "created_at": session.created_at.isoformat(),
            "job_id": session.job_id,
        }
        for session in sessions
    ]


@router.post("/sessions")
async def create_session(
    body: SessionCreateRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    session = ChatSession(
        user_id=current_user.id,
        job_id=body.job_id,
        title=body.title,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
    }


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = messages_result.scalars().all()
    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "scorecard": message.scorecard,
            "bias_flags": message.bias_flags,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]
