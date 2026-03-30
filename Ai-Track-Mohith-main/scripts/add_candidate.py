#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = REPO_ROOT / "documents"
DB_URL_CANDIDATES = (
    os.environ.get("DATABASE_URL"),
    "postgresql://postgres:postgres@localhost:5433/app_scaffold",
    "postgresql://hirelogic:hirelogic@localhost:5432/hirelogic",
)
ALLOWED_STATUSES = {"applied", "screening", "interview"}


def _bootstrap_server_site_packages() -> None:
    server_venv_lib = REPO_ROOT / "server" / ".venv" / "lib"
    if not server_venv_lib.exists():
        return
    for python_dir in server_venv_lib.iterdir():
        site_packages = python_dir / "site-packages"
        if site_packages.exists():
            sys.path.insert(0, str(site_packages))
            break


_bootstrap_server_site_packages()

import asyncpg


@dataclass
class CandidateArgs:
    job_id: int
    anon_id: str
    years_exp: int
    skills: list[str]
    summary: str
    status: str


def parse_args() -> CandidateArgs:
    parser = argparse.ArgumentParser(description="Add a HireLogic demo candidate.")
    parser.add_argument("--job-id", type=int, required=True, choices=[1, 2])
    parser.add_argument("--anon-id", type=str, required=True)
    parser.add_argument("--years-exp", type=int, required=True)
    parser.add_argument("--skills", type=str, required=True)
    parser.add_argument("--summary", type=str, required=True)
    parser.add_argument(
        "--status",
        type=str,
        default="applied",
        choices=sorted(ALLOWED_STATUSES),
    )
    parsed = parser.parse_args()

    if not parsed.anon_id.startswith("candidate-uuid-"):
        parser.error("--anon-id must match candidate-uuid-NNN")

    skills = [skill.strip() for skill in parsed.skills.split(",") if skill.strip()]
    if len(skills) < 2:
        parser.error("--skills must contain at least 2 comma-separated skills")

    return CandidateArgs(
        job_id=parsed.job_id,
        anon_id=parsed.anon_id,
        years_exp=parsed.years_exp,
        skills=skills,
        summary=parsed.summary.strip(),
        status=parsed.status,
    )


def _candidate_dir(anon_id: str) -> Path:
    return DOCUMENTS_ROOT / anon_id.replace("-", "_")


def create_documents(args: CandidateArgs) -> Path:
    candidate_dir = _candidate_dir(args.anon_id)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    first_skill = args.skills[0]
    second_skill = args.skills[1]
    skills_csv = ", ".join(args.skills)
    today_iso = date.today().isoformat()

    metadata = {
        "anon_id": args.anon_id,
        "document_version": "1.0",
        "created_at": today_iso,
        "blinding_applied": True,
        "fields_removed": [
            "full_name",
            "university_name",
            "gender_pronouns",
            "nationality",
        ],
    }
    index = {
        "anon_id": args.anon_id,
        "sections": [
            "section_01_experience.md",
            "section_02_skills_projects.md",
            "section_03_education_certs.md",
        ],
    }
    experience = f"""# Experience

## Professional Background
{args.summary}

## Years of Experience
{args.years_exp} years of professional experience in
software engineering.

## Key Roles
- Senior Engineer role focused on backend systems
  and API development
- Led technical projects with cross-functional teams
- Contributed to production systems serving
  real user traffic
"""
    skills_projects = f"""# Skills and Projects

## Technical Skills
{skills_csv}

## Notable Projects

### Project Alpha
Built and deployed production system using
{first_skill} and {second_skill}.
Reduced system latency by 25% through
optimization of core data pipeline.

### Project Beta
Designed and implemented scalable architecture
supporting 100k+ daily active users.
Led end-to-end delivery from design to deployment.

## Open Source
Contributed to 3 open source projects in the
{skills_csv} ecosystem.
"""
    education = f"""# Education and Certifications

## Education
Degree in Computer Science or related field from
[EDUCATION_INSTITUTION].
Graduated with strong academic performance.

## Certifications
- Cloud platform certification (AWS/GCP/Azure)
- Relevant technical certification in {first_skill}

## Continuous Learning
Active learner — completed online courses in
machine learning, system design, and distributed
systems in the past 2 years.
"""

    (candidate_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    (candidate_dir / "index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8"
    )
    (candidate_dir / "section_01_experience.md").write_text(experience, encoding="utf-8")
    (candidate_dir / "section_02_skills_projects.md").write_text(
        skills_projects, encoding="utf-8"
    )
    (candidate_dir / "section_03_education_certs.md").write_text(
        education, encoding="utf-8"
    )

    return candidate_dir


def _normalize_db_url(raw_url: str) -> str:
    if raw_url.startswith("postgresql+asyncpg://"):
        return raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw_url


async def connect_db() -> asyncpg.Connection:
    last_error: Exception | None = None
    for raw_url in DB_URL_CANDIDATES:
        if not raw_url:
            continue
        try:
            return await asyncpg.connect(_normalize_db_url(raw_url), timeout=3)
        except Exception as exc:  # pragma: no cover - validation prints actual outcome
            last_error = exc
    raise RuntimeError(f"Unable to connect to Postgres: {last_error}")


async def insert_rows(args: CandidateArgs, candidate_dir: Path) -> None:
    conn = await connect_db()
    try:
        candidate_id = await conn.fetchval(
            """
            INSERT INTO candidates (anon_id, display_name, email, resume_path, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (anon_id) DO NOTHING
            RETURNING id
            """,
            args.anon_id,
            f"Candidate {args.anon_id[-3:]}",
            None,
            f"documents/{candidate_dir.name}/",
        )

        if candidate_id is None:
            print(f"Candidate {args.anon_id} already exists.")
            raise SystemExit(0)

        await conn.execute(
            """
            INSERT INTO applications (candidate_id, job_id, status, applied_at)
            VALUES ($1, $2, $3, NOW())
            """,
            candidate_id,
            args.job_id,
            args.status,
        )
    finally:
        await conn.close()


async def main() -> None:
    args = parse_args()
    candidate_dir = create_documents(args)
    await insert_rows(args, candidate_dir)
    print(
        f"""
✅ Candidate added successfully!

  anon_id:   {args.anon_id}
  job_id:    {args.job_id}
  status:    {args.status}
  documents: documents/{candidate_dir.name}/
  skills:    {', '.join(args.skills)}

Next step — run this in HireLogic chat:
  "Rank all candidates for {'Senior ML Engineer' if args.job_id == 1 else 'Backend Software Engineer'}"

The new candidate will appear in rankings.
""".strip()
    )


if __name__ == "__main__":
    asyncio.run(main())
