from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db, get_db_session


async def db_session(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    return session


def settings(s: Settings = Depends(get_settings)) -> Settings:
    return s


async def verify_agent_secret(x_agent_secret: str | None = Header(default=None)) -> bool:
    """Dependency for /internal/ routes.
    Verifies x-agent-secret header. JWT never reaches these routes.
    Raises 403 if secret does not match.
    """
    current = get_settings()
    if x_agent_secret != current.AGENT_INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Invalid agent secret")
    return True


async def db(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    return session
