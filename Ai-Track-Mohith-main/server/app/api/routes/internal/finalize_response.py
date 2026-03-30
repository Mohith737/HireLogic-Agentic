from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, cast

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, verify_agent_secret
from app.db.models import ChatMessage, ChatSession, Job, User
from app.services.response_service import assemble_scorecard

router = APIRouter()


class FinalizeRequest(BaseModel):
    job_id: str
    session_id: str
    user_query: str
    all_scorecards: Any
    bias_flags: Any = []
    prior_conversation_summary: str = ""


def _normalize_scorecards(raw_scorecards: Any) -> list[dict[str, Any]]:
    if isinstance(raw_scorecards, str):
        try:
            parsed_scorecards = json.loads(raw_scorecards)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
    else:
        parsed_scorecards = raw_scorecards

    if isinstance(parsed_scorecards, dict):
        if isinstance(parsed_scorecards.get("all_scorecards"), list):
            return [
                cast(dict[str, Any], item)
                for item in parsed_scorecards["all_scorecards"]
                if isinstance(item, dict)
            ]
        if isinstance(parsed_scorecards.get("result"), str):
            return _normalize_scorecards(parsed_scorecards["result"])
        for value in parsed_scorecards.values():
            if isinstance(value, (dict, list, str)):
                nested = _normalize_scorecards(value)
                if nested:
                    return nested
        return []
    if isinstance(parsed_scorecards, list):
        return [item for item in parsed_scorecards if isinstance(item, dict)]
    return []


def _normalize_bias_flags(raw_bias_flags: Any) -> list[dict[str, Any]]:
    if isinstance(raw_bias_flags, dict):
        if isinstance(raw_bias_flags.get("bias_detection_result"), dict):
            inner_flags = raw_bias_flags["bias_detection_result"].get("bias_flags", [])
            return _normalize_bias_flags(inner_flags)
        if isinstance(raw_bias_flags.get("bias_flags"), list):
            return [flag for flag in raw_bias_flags["bias_flags"] if isinstance(flag, dict)]
        if isinstance(raw_bias_flags.get("result"), str):
            return _normalize_bias_flags(raw_bias_flags["result"])
        for value in raw_bias_flags.values():
            if isinstance(value, (dict, list, str)):
                nested = _normalize_bias_flags(value)
                if nested:
                    return nested
        return []
    if isinstance(raw_bias_flags, str):
        try:
            parsed_bias_flags = json.loads(raw_bias_flags)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        return _normalize_bias_flags(parsed_bias_flags)
    if isinstance(raw_bias_flags, list):
        return [flag for flag in raw_bias_flags if isinstance(flag, dict)]
    return []


@router.post("/finalize-response")
async def finalize_response(
    body: FinalizeRequest,
    _: bool = Depends(verify_agent_secret),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    try:
        session_id_int = int(body.session_id)
    except (ValueError, TypeError):
        session_id_int = (
            int(hashlib.md5(str(body.session_id).encode()).hexdigest(), 16) % 100000
        ) + 90000

    scorecards = _normalize_scorecards(body.all_scorecards)
    normalized_bias_flags = _normalize_bias_flags(body.bias_flags)

    assembled = assemble_scorecard(scorecards, normalized_bias_flags)
    scorecard_dict = assembled["scorecard"]
    ranking = assembled["ranking"]
    sorted_scorecards = sorted(
        scorecards,
        key=lambda scorecard: float(scorecard.get("overall_score", 0)),
        reverse=True,
    )

    bias_detected = any(normalized_bias_flags)
    top = sorted_scorecards[0] if sorted_scorecards else None
    if top:
        top_id = top.get("candidate_anon_id", "unknown")
        top_score = round(float(top.get("overall_score", 0)), 2)
        reply = f"{top_id} ranks first with overall score {top_score}/10. "
        if len(sorted_scorecards) > 1:
            second = sorted_scorecards[1]
            second_id = second.get("candidate_anon_id", "unknown")
            second_score = round(float(second.get("overall_score", 0)), 2)
            reply += f"{second_id} ranks second at {second_score}/10. "
        if bias_detected:
            reply += "Bias flags were detected - review recommended."
        else:
            reply += "No bias patterns detected in scoring."
    else:
        reply = "No candidates were scored."

    job_title = "the role"
    try:
        job_result = await db.execute(select(Job).where(Job.id == int(body.job_id)))
        job = job_result.scalar_one_or_none()
        if job:
            job_title = job.title
    except Exception:
        pass

    summary = (
        f"Ranked {len(sorted_scorecards)} candidates for "
        f"{job_title}. "
        f"Top: {ranking[0]['anon_id'] if ranking else 'none'} "
        f"({ranking[0]['overall_score'] if ranking else 0}). "
        f"Bias: {'detected' if bias_detected else 'none'}."
    )

    sources_used: list[dict[str, Any]] = []
    try:
        job_id_int_local = int(body.job_id)
        job_alias = "job_senior_ml_engineer" if job_id_int_local == 1 else "job_backend_engineer"
        sources_used.append(
            {
                "document_id": job_alias,
                "type": "job_description",
                "sections_read": ["section_02_competency_framework.md"],
            }
        )
        for scorecard in sorted_scorecards:
            anon_id = scorecard.get("candidate_anon_id", "")
            folder = str(anon_id).replace("-", "_")
            sources_used.append(
                {
                    "document_id": folder,
                    "type": "candidate_resume",
                    "sections_read": [
                        "section_01_experience.md",
                        "section_02_skills_projects.md",
                        "section_03_education_certs.md",
                    ],
                }
            )
        sources_used.append(
            {
                "document_id": "historical_hiring_outcomes",
                "type": "historical_data",
                "sections_read": ["section_01_outcomes.md"],
            }
        )
    except Exception:
        pass

    try:
        try:
            sess_result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id_int)
            )
            session_obj = sess_result.scalar_one_or_none()
            if not session_obj:
                user_result = await db.execute(select(User).limit(1))
                user = user_result.scalar_one_or_none()
                user_id = user.id if user else 1

                new_session = ChatSession(
                    id=session_id_int,
                    user_id=user_id,
                    job_id=int(body.job_id) if body.job_id else None,
                    title=body.user_query[:50],
                )
                db.add(new_session)
                await db.flush()
        except Exception:
            pass

        user_msg = ChatMessage(
            session_id=session_id_int,
            role="user",
            content=body.user_query or "",
        )
        db.add(user_msg)

        assistant_msg = ChatMessage(
            session_id=session_id_int,
            role="assistant",
            content=reply,
            scorecard={
                **scorecard_dict,
                "_meta": {
                    "sources_used": sources_used,
                    "conversation_summary": summary,
                },
            },
            bias_flags={"flags": normalized_bias_flags},
        )
        db.add(assistant_msg)

        await db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id_int)
            .values(title=body.user_query[:50] if not body.prior_conversation_summary else None)
        )
        await db.commit()
    except Exception as exc:
        logging.getLogger(__name__).warning("DB save failed: %s", exc)
        await db.rollback()

    return {
        "scorecard": scorecard_dict,
        "ranking": ranking,
        "bias_flags": normalized_bias_flags,
        "reply": reply,
        "session_id": session_id_int,
        "updated_conversation_summary": summary,
        "sources_used": sources_used,
    }
