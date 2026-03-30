"""
HireLogic low-latency runner.
Python-first orchestration with parallel candidate processing.
"""
# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from typing import Any, cast

import httpx

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from server.app.services.validation import compress_evidence, validate_resume_analysis

APP_NAME = "hirelogic"
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
AGENT_INTERNAL_SECRET = os.getenv("AGENT_INTERNAL_SECRET", "dev-agent-secret")
DOCUMENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "documents")
FOLLOWUP_CACHE: dict[str, dict[str, object]] = {}


def _get_resource_overview(documents_path: str) -> dict[str, Any]:
    with open(
        os.path.join(documents_path, "resource_index.json"),
        "r",
        encoding="utf-8",
    ) as handle:
        return cast(dict[str, Any], json.load(handle))


async def _call_internal_async(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BACKEND_BASE_URL.rstrip('/')}{path}",
            json=payload,
            headers={"x-agent-secret": AGENT_INTERNAL_SECRET},
        )
        response.raise_for_status()
        data = response.json()
    return data if isinstance(data, dict) else {}


def _read_candidate_sections(document_path: str) -> list[str]:
    sections: list[str] = []
    for section_file in [
        "section_01_experience.md",
        "section_02_skills_projects.md",
        "section_03_education_certs.md",
    ]:
        candidate_paths = [
            os.path.join(os.path.dirname(__file__), "..", document_path, section_file),
            os.path.join(os.path.dirname(__file__), document_path, section_file),
            os.path.join(document_path, section_file),
        ]
        for path in candidate_paths:
            normalized = os.path.normpath(path)
            if os.path.exists(normalized):
                with open(normalized, "r", encoding="utf-8") as handle:
                    sections.append(handle.read())
                break
    return sections


def _build_followup_answer(question: str, scorecard: dict[str, Any]) -> str:
    del question
    if not scorecard:
        return (
            "I don't have prior ranking results to reference. "
            "Please run a full ranking first."
        )

    sorted_candidates = sorted(
        scorecard.items(),
        key=lambda item: float(item[1].get("overall_score", 0)),
        reverse=True,
    )
    top_id, top_data = sorted_candidates[0]
    top_score = top_data.get("overall_score", 0)
    comp_scores = cast(dict[str, Any], top_data.get("competency_scores", {}))
    sorted_comps = sorted(
        comp_scores.items(),
        key=lambda item: float(
            item[1].get("score", 0) if isinstance(item[1], dict) else item[1]
        ),
        reverse=True,
    )
    answer = f"{top_id} ranks highest with an overall score of {top_score}/10. "
    if sorted_comps:
        top_comp_name, top_comp_data = sorted_comps[0]
        top_comp_score = (
            top_comp_data.get("score", "?")
            if isinstance(top_comp_data, dict)
            else top_comp_data
        )
        evidence = (
            top_comp_data.get("evidence", "")
            if isinstance(top_comp_data, dict)
            else ""
        )
        answer += f"Their strongest area is {top_comp_name} ({top_comp_score}/10)"
        answer += f", supported by: {evidence[:120]}." if evidence else "."
    if len(sorted_candidates) > 1:
        second_id, second_data = sorted_candidates[1]
        second_score = second_data.get("overall_score", 0)
        gap = round(float(top_score) - float(second_score), 2)
        answer += f" {second_id} ranks second at {second_score}/10, a gap of {gap} points."
    if len(sorted_candidates) > 2:
        third_id, third_data = sorted_candidates[2]
        answer += f" {third_id} ranks third at {third_data.get('overall_score', 0)}/10."
    return answer


async def run_followup(question: str, prior_scorecard: dict[str, Any]) -> dict[str, Any]:
    print(f"[followup] prior_scorecard keys: {list(prior_scorecard.keys())}")
    answer = _build_followup_answer(question, prior_scorecard)
    return {
        "answer": answer,
        "scorecard": None,
        "ranking": [],
        "bias_flags": [],
        "fallback_triggered": False,
    }


async def run_pipeline_for_candidate(
    candidate: dict[str, Any],
    job_id: str,
    competency_framework: list[dict[str, Any]],
) -> dict[str, Any]:
    analysis = await _call_internal_async(
        "/internal/hirelogic/resume-analysis",
        {
            "job_id": job_id,
            "candidate_anon_id": candidate["anon_id"],
            "candidate_document_path": candidate["document_path"],
            "competency_framework": competency_framework,
        },
    )
    evidence = cast(dict[str, str], analysis.get("evidence_by_competency", {}))
    validation = validate_resume_analysis(
        evidence,
        _read_candidate_sections(str(candidate["document_path"])),
        [],
    )
    compressed = compress_evidence(evidence)
    scores = await _call_internal_async(
        "/internal/hirelogic/score-candidates",
        {
            "job_id": job_id,
            "candidate_anon_id": candidate["anon_id"],
            "evidence_by_competency": compressed,
            "competency_framework": competency_framework,
            "interview_feedback": candidate.get("interview_feedback"),
            "blend_ratio": [0.6, 0.4],
        },
    )
    scores["application_status"] = candidate.get("application_status")
    scores["low_confidence"] = bool(scores.get("low_confidence")) or bool(
        validation.get("low_confidence_fields")
    )
    scores["validation"] = validation
    return scores


async def run_full_pipeline(
    job_id: str,
    candidates: list[dict[str, Any]],
    competency_framework: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tasks = [
        run_pipeline_for_candidate(candidate, job_id, competency_framework)
        for candidate in candidates
    ]
    results = await asyncio.gather(*tasks)
    return cast(list[dict[str, Any]], results)


async def run_hirelogic(
    question: str,
    user_id: str,
    session_id: int,
    job_id: int | None = None,
) -> dict[str, Any]:
    session_key = f"{APP_NAME}-{user_id}-{session_id}"
    state = dict(FOLLOWUP_CACHE.get(session_key, {}))
    q_lower = question.lower()
    prior_scorecard = cast(dict[str, Any], state.get("prior_scorecard") or {})

    is_weight_adjustment = any(
        word in q_lower
        for word in [
            "weight",
            "increase",
            "decrease",
            "adjust",
            "re-rank",
            "rerank",
            "change weight",
            "40%",
            "30%",
            "50%",
            "priority",
            "prioritize",
        ]
    )
    follow_up_words = [
        "why",
        "compare",
        "explain",
        "higher",
        "lower",
        "difference",
        "better",
        "worse",
        "reason",
        "because",
        "tell me more",
        "elaborate",
    ]
    is_follow_up = (
        not is_weight_adjustment
        and bool(prior_scorecard)
        and any(word in q_lower for word in follow_up_words)
        and not any(word in q_lower for word in ["score all", "rank all", "assess"])
    )
    recruitment_words = [
        "rank",
        "candidate",
        "score",
        "hire",
        "job",
        "ml",
        "engineer",
        "apply",
        "resume",
        "weight",
        "competency",
        "why",
        "compare",
        "explain",
        "higher",
        "lower",
        "better",
        "worse",
        "top",
        "re-rank",
        "rerank",
        "increase",
        "decrease",
        "python",
        "assess",
        "evaluate",
    ]
    is_out_of_scope = not any(word in q_lower for word in recruitment_words)
    has_job_context = (
        job_id is not None
        or bool(state.get("job_id"))
        or bool(prior_scorecard)
        or any(word in q_lower for word in ["senior ml", "backend", "engineer", "job 1", "job 2"])
    )
    is_ambiguous = (
        not has_job_context
        and not is_out_of_scope
        and not is_follow_up
        and not is_weight_adjustment
    )

    if is_out_of_scope:
        return {
            "answer": (
                "I can help with candidate screening and ranking for open roles. "
                "Please ask me to rank or score candidates for a specific job."
            ),
            "scorecard": None,
            "ranking": [],
            "bias_flags": [],
            "fallback_triggered": False,
        }
    if is_ambiguous:
        return {
            "answer": (
                "Which role would you like to rank candidates for? Available roles: "
                "Senior ML Engineer (job_id=1) or Backend Software Engineer (job_id=2)."
            ),
            "scorecard": None,
            "ranking": [],
            "bias_flags": [],
            "fallback_triggered": False,
        }
    if is_follow_up:
        print("[routing] Follow-up detected — bypassing pipeline")
        return await run_followup(question, prior_scorecard)

    if is_weight_adjustment:
        weight_overrides: dict[str, float] = {}
        for competency in [
            "Python",
            "Machine Learning",
            "System Design",
            "Communication",
            "Research",
            "Go",
            "Databases",
        ]:
            if competency.lower() in q_lower:
                matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", question)
                if matches:
                    weight_overrides[competency] = float(matches[0]) / 100.0
        if weight_overrides:
            state["weight_overrides"] = weight_overrides
            print(f"[routing] Weight overrides: {weight_overrides}")

    effective_job_id = str(job_id or state.get("job_id") or "1")
    state["job_id"] = effective_job_id

    total_start = time.perf_counter()

    t0 = time.perf_counter()
    _ = _get_resource_overview(DOCUMENTS_PATH)
    print(f"TOC: {time.perf_counter() - t0:.2f}s")

    t1 = time.perf_counter()
    job_ctx = await _call_internal_async(
        "/internal/hirelogic/job-context",
        {
            "job_id": effective_job_id,
            "weight_overrides": state.get("weight_overrides", {}),
        },
    )
    print(f"job_context: {time.perf_counter() - t1:.2f}s")

    t2 = time.perf_counter()
    candidate_payload = await _call_internal_async(
        "/internal/hirelogic/candidate-profiles",
        {"job_id": effective_job_id},
    )
    candidates = cast(list[dict[str, Any]], candidate_payload.get("candidates", []))
    print(f"candidate_fetch: {time.perf_counter() - t2:.2f}s")

    t3 = time.perf_counter()
    all_scores = await run_full_pipeline(
        str(job_ctx.get("job_id", effective_job_id)),
        candidates,
        cast(list[dict[str, Any]], job_ctx.get("competency_framework", [])),
    )
    print(f"parallel analysis+scoring: {time.perf_counter() - t3:.2f}s")

    t4 = time.perf_counter()
    bias = await _call_internal_async(
        "/internal/hirelogic/detect-bias",
        {
            "job_id": str(job_ctx.get("job_id", effective_job_id)),
            "all_scorecards": all_scores,
        },
    )
    print(f"bias: {time.perf_counter() - t4:.2f}s")

    t5 = time.perf_counter()
    result = await _call_internal_async(
        "/internal/hirelogic/finalize-response",
        {
            "job_id": str(job_ctx.get("job_id", effective_job_id)),
            "session_id": str(session_id),
            "user_query": question,
            "all_scorecards": all_scores,
            "bias_flags": bias.get("bias_flags", []),
            "prior_conversation_summary": state.get("prior_conversation_summary", ""),
        },
    )
    print(f"response: {time.perf_counter() - t5:.2f}s")
    print(f"TOTAL: {time.perf_counter() - total_start:.2f}s")

    if result.get("scorecard"):
        FOLLOWUP_CACHE[session_key] = {
            "prior_scorecard": result["scorecard"],
            "prior_conversation_summary": result.get(
                "updated_conversation_summary", ""
            ),
            "job_id": str(job_ctx.get("job_id", effective_job_id)),
            "weight_overrides": cast(dict[str, Any], state.get("weight_overrides", {})),
        }

    return {
        "answer": result.get("reply", "No response generated."),
        "scorecard": result.get("scorecard"),
        "ranking": result.get("ranking", []),
        "bias_flags": result.get("bias_flags", []),
        "fallback_triggered": False,
    }
