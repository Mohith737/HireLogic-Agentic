from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.auth.passwords import hash_password
from app.db.models import (
    Application,
    Candidate,
    ChatSession,
    CompetencyFramework,
    HiringOutcome,
    InterviewFeedback,
    Job,
    User,
)
from app.db.session import AsyncSessionLocal


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing_users = await session.scalar(select(func.count(User.id)))
        if existing_users and existing_users > 0:
            return

        recruiter_alice = User(
            username="recruiter_alice",
            email="alice@hirelogic.com",
            full_name="Recruiter Alice",
            hashed_password=see .env file
        )
        recruiter_bob = User(
            username="recruiter_bob",
            email="bob@hirelogic.com",
            full_name="Recruiter Bob",
            hashed_password=see .env file
        )
        session.add_all([recruiter_alice, recruiter_bob])
        await session.flush()

        job_1 = Job(
            id=1,
            title="Senior ML Engineer",
            description="AI-assisted candidate screening for a senior machine learning role.",
            document_path="documents/job_senior_ml_engineer/",
        )
        job_2 = Job(
            id=2,
            title="Backend Software Engineer",
            description="Backend software engineering role with emphasis on service design.",
            document_path="documents/job_backend_engineer/",
        )
        session.add_all([job_1, job_2])
        await session.flush()

        framework_job_1 = CompetencyFramework(
            job_id=job_1.id,
            framework={
                "competencies": [
                    {
                        "name": "Python",
                        "weight": 0.30,
                        "description": "Python proficiency for ML systems",
                        "scoring_criteria": {
                            "10": "Expert, production systems at scale",
                            "7": "Proficient, 3+ years, some production",
                            "4": "Basic, scripts and notebooks only",
                        },
                    },
                    {
                        "name": "Machine Learning",
                        "weight": 0.25,
                        "description": "ML model development and deployment",
                        "scoring_criteria": {
                            "10": "Novel model development, production impact",
                            "7": "Standard ML pipelines, fine-tuning, deployment",
                            "4": "Theoretical knowledge, limited application",
                        },
                    },
                    {
                        "name": "System Design",
                        "weight": 0.20,
                        "description": "Distributed systems architecture",
                        "scoring_criteria": {
                            "10": "Designed distributed systems serving millions",
                            "7": "Solid architecture knowledge, mid-scale",
                            "4": "Basic understanding, no production design",
                        },
                    },
                    {
                        "name": "Communication",
                        "weight": 0.15,
                        "description": "Cross-functional collaboration",
                        "scoring_criteria": {
                            "10": "Led cross-functional projects, clear docs",
                            "7": "Effective collaborator, decent writing",
                            "4": "Limited evidence beyond individual work",
                        },
                    },
                    {
                        "name": "Research",
                        "weight": 0.10,
                        "description": "Research depth and contribution",
                        "scoring_criteria": {
                            "10": "Published papers, novel contributions",
                            "7": "Deep reading, applied research to products",
                            "4": "Academic exposure only",
                        },
                    },
                ]
            },
        )
        framework_job_2 = CompetencyFramework(
            job_id=job_2.id,
            framework={
                "competencies": [
                    {
                        "name": "Python/Go",
                        "weight": 0.35,
                        "description": "Backend language proficiency",
                        "scoring_criteria": {
                            "10": "Expert production engineering in Python or Go at scale",
                            "7": (
                                "Strong implementation skills with meaningful production ownership"
                            ),
                            "4": "Limited production experience, mostly scripts or coursework",
                        },
                    },
                    {
                        "name": "System Design",
                        "weight": 0.30,
                        "description": "Distributed service architecture",
                        "scoring_criteria": {
                            "10": "Designed large-scale distributed systems with clear tradeoffs",
                            "7": "Good architecture judgment for mid-scale service design",
                            "4": "Basic service design understanding",
                        },
                    },
                    {
                        "name": "Databases",
                        "weight": 0.20,
                        "description": "Schema design and query performance",
                        "scoring_criteria": {
                            "10": "Strong data modeling, tuning, and reliability",
                            "7": "Solid schema design and query optimization",
                            "4": "Basic CRUD familiarity",
                        },
                    },
                    {
                        "name": "Communication",
                        "weight": 0.15,
                        "description": "Clear technical collaboration",
                        "scoring_criteria": {
                            "10": "Excellent technical communication and influence",
                            "7": "Clear collaborator with useful design docs",
                            "4": "Limited written and verbal evidence",
                        },
                    },
                ]
            },
        )
        session.add_all([framework_job_1, framework_job_2])

        candidates = [
            Candidate(
                anon_id="candidate-uuid-001",
                display_name="Rahul Sharma",
                email="rahul.sharma@example.com",
                resume_path="documents/candidate_uuid_001/",
            ),
            Candidate(
                anon_id="candidate-uuid-002",
                display_name="Priya Patel",
                email="priya.patel@example.com",
                resume_path="documents/candidate_uuid_002/",
            ),
            Candidate(
                anon_id="candidate-uuid-003",
                display_name="Jordan Lee",
                email="jordan.lee@example.com",
                resume_path="documents/candidate_uuid_003/",
            ),
            Candidate(
                anon_id="candidate-uuid-004",
                display_name="Sam Chen",
                email="sam.chen@example.com",
                resume_path=None,
            ),
            Candidate(
                anon_id="candidate-uuid-005",
                display_name="Alex Kumar",
                email="alex.kumar@example.com",
                resume_path=None,
            ),
        ]
        session.add_all(candidates)
        await session.flush()

        application_1_ml = Application(candidate_id=candidates[0].id, job_id=1, status="screening")
        application_2_ml = Application(candidate_id=candidates[1].id, job_id=1, status="applied")
        application_3_ml = Application(candidate_id=candidates[2].id, job_id=1, status="interview")
        application_1_be = Application(candidate_id=candidates[0].id, job_id=2, status="applied")
        session.add_all([application_1_ml, application_2_ml, application_3_ml, application_1_be])
        await session.flush()

        session.add(
            InterviewFeedback(
                application_id=application_3_ml.id,
                interviewer_notes="Strong architecture judgment with practical tradeoff awareness.",
                feedback={
                    "Python": 7,
                    "Machine Learning": 6,
                    "System Design": 9,
                    "Communication": 8,
                    "Research": 5,
                },
                overall_score=7.0,
            )
        )

        past_app_1 = Application(
            candidate_id=candidates[0].id,
            job_id=1,
            status="hired",
            applied_at=datetime.utcnow() - timedelta(days=700),
        )
        past_app_2 = Application(
            candidate_id=candidates[2].id,
            job_id=1,
            status="hired",
            applied_at=datetime.utcnow() - timedelta(days=540),
        )
        past_app_3 = Application(
            candidate_id=candidates[1].id,
            job_id=1,
            status="rejected",
            applied_at=datetime.utcnow() - timedelta(days=420),
        )
        session.add_all([past_app_1, past_app_2, past_app_3])
        await session.flush()

        session.add_all(
            [
                HiringOutcome(
                    application_id=past_app_1.id,
                    hired=True,
                    performance_score=8.5,
                    retention_months=18,
                    notes="Strong long-term production impact.",
                ),
                HiringOutcome(
                    application_id=past_app_2.id,
                    hired=True,
                    performance_score=7.2,
                    retention_months=12,
                    notes="Strong architecture performance after hire.",
                ),
                HiringOutcome(
                    application_id=past_app_3.id,
                    hired=False,
                    performance_score=None,
                    retention_months=None,
                    notes="Offer declined before start.",
                ),
            ]
        )

        session.add(
            ChatSession(user_id=recruiter_alice.id, title="Initial HireLogic Session", job_id=1)
        )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())


