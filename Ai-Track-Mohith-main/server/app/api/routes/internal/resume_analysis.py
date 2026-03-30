from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import verify_agent_secret

router = APIRouter()
logger = logging.getLogger(__name__)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))


class ResumeAnalysisRequest(BaseModel):
    job_id: str
    candidate_anon_id: str
    candidate_document_path: str
    competency_framework: list[dict[str, Any]]


SECTION_FILES = [
    "section_01_experience.md",
    "section_02_skills_projects.md",
    "section_03_education_certs.md",
]


def _read_candidate_sections(document_path: str) -> str:
    combined: list[str] = []
    doc_path = document_path.strip("/")
    base_paths = [
        REPO_ROOT,
        os.path.abspath("."),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")),
    ]

    for section_file in SECTION_FILES:
        for base in base_paths:
            normalized = os.path.normpath(os.path.join(base, doc_path, section_file))
            if os.path.exists(normalized):
                try:
                    with open(normalized, encoding="utf-8") as handle:
                        content = handle.read().strip()
                    if content:
                        combined.append(f"=== {section_file} ===\n{content}")
                    break
                except Exception:
                    continue
    return "\n\n".join(combined)


def _extract_evidence(full_text: str, competency_name: str, competency_description: str) -> str:
    """Extract verbatim resume lines that match a competency."""
    if not full_text:
        return ""

    keyword_map = {
        "Python": [
            "python",
            "pytorch",
            "tensorflow",
            "keras",
            "pandas",
            "numpy",
            "sklearn",
            "pip",
            "django",
            "fastapi",
            "flask",
        ],
        "Machine Learning": [
            "machine learning",
            "ml",
            "model",
            "training",
            "inference",
            "neural",
            "deep learning",
            "nlp",
            "computer vision",
            "classification",
            "regression",
            "bert",
            "transformer",
            "llm",
            "generative",
        ],
        "System Design": [
            "system design",
            "architecture",
            "distributed",
            "microservice",
            "api",
            "kubernetes",
            "docker",
            "scale",
            "latency",
            "throughput",
            "database",
            "redis",
            "kafka",
        ],
        "Communication": [
            "led",
            "managed",
            "collaborated",
            "presented",
            "documented",
            "mentored",
            "cross-functional",
            "stakeholder",
            "team",
            "communication",
        ],
        "Research": [
            "research",
            "paper",
            "published",
            "arxiv",
            "citation",
            "novel",
            "contribution",
            "experiment",
            "hypothesis",
            "ablation",
        ],
        "Databases": [
            "database",
            "postgres",
            "mysql",
            "mongodb",
            "sql",
            "nosql",
            "redis",
            "elasticsearch",
            "query",
            "schema",
            "migration",
        ],
        "Go": ["golang", " go ", "goroutine", "channel", "grpc", "protobuf"],
    }

    comp_lower = competency_name.lower()
    keywords: list[str] = []
    for key, values in keyword_map.items():
        if key.lower() in comp_lower or comp_lower in key.lower():
            keywords.extend(values)

    if not keywords:
        keywords = [word.lower() for word in competency_description.split() if len(word) > 4]

    sentences: list[str] = []
    for line in full_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("===") or stripped.startswith("#"):
            continue
        lowered = stripped.lower()
        if any(keyword in lowered for keyword in keywords):
            sentences.append(stripped)

    result = " ".join(sentences[:3])
    return result if result else ""


@router.post("/resume-analysis")
async def resume_analysis(
    body: ResumeAnalysisRequest, _: bool = Depends(verify_agent_secret)
) -> dict[str, Any]:
    logger.info(
        "resume-analysis called: candidate=%s path=%s repo_root=%s",
        body.candidate_anon_id,
        body.candidate_document_path,
        REPO_ROOT,
    )
    full_text = _read_candidate_sections(body.candidate_document_path)
    logger.info(
        "text found: %s chars for %s",
        len(full_text),
        body.candidate_anon_id,
    )

    if not full_text:
        evidence = {competency["name"]: "" for competency in body.competency_framework}
        return {
            "candidate_anon_id": body.candidate_anon_id,
            "evidence_by_competency": evidence,
            "warning": f"No resume text found at {body.candidate_document_path}",
        }

    evidence_by_competency: dict[str, str] = {}
    for competency in body.competency_framework:
        name = competency.get("name", "")
        description = competency.get("description", "")
        evidence_by_competency[name] = _extract_evidence(full_text, name, description)

    return {
        "candidate_anon_id": body.candidate_anon_id,
        "evidence_by_competency": evidence_by_competency,
    }
