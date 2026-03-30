"""
Slim HireLogic agent definitions.
The live ranking path is orchestrated in backend_chat.py for latency.
Only the reasoning-heavy agent contracts remain here.
"""

# pyright: reportMissingImports=false

from __future__ import annotations

import json
import os
from typing import Any

import httpx

try:
    from google.adk.agents import Agent, SequentialAgent
except ImportError:  # pragma: no cover
    class Agent:
        def __init__(
            self,
            *,
            name: str,
            model: str,
            description: str,
            instruction: str,
            tools: list[Any] | None = None,
            sub_agents: list[Any] | None = None,
        ) -> None:
            self.name = name
            self.model = model
            self.description = description
            self.instruction = instruction
            self.tools = tools or []
            self.sub_agents = sub_agents or []

    class SequentialAgent(Agent):
        def __init__(self, *, name: str, description: str = "", sub_agents: list[Any] | None = None) -> None:
            super().__init__(
                name=name,
                model=MODEL,
                description=description,
                instruction="Deterministic sequential pipeline placeholder.",
                sub_agents=sub_agents,
            )


MODEL = "gemini-2.5-flash"
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
AGENT_INTERNAL_SECRET=see .env file
DOCUMENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "documents")


def _post_internal(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{BACKEND_BASE_URL.rstrip('/')}{path}"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            json=payload,
            headers={"x-agent-secret": AGENT_INTERNAL_SECRET},
        )
        response.raise_for_status()
        data = response.json()
    return data if isinstance(data, dict) else {}


def fetch_job_context(job_id: str, weight_overrides_json: str = "{}") -> str:
    try:
        overrides = json.loads(weight_overrides_json)
    except (json.JSONDecodeError, TypeError):
        overrides = {}
    return json.dumps(
        _post_internal(
            "/internal/hirelogic/job-context",
            {"job_id": job_id, "weight_overrides": overrides},
        )
    )


def fetch_candidates_for_job(job_id: str) -> str:
    """Fetch active candidates for a job.

    Returns anonymized candidate list with document
    paths and interview feedback. Excludes hired/
    rejected historical records.

    Args:
        job_id: Postgres job id or alias string

    Returns:
        JSON string with key candidates: list of
        candidate objects with anon_id, document_path,
        application_status, interview_feedback.
    """
    result = _post_internal(
        "/internal/hirelogic/candidate-profiles",
        {"job_id": job_id},
    )
    return json.dumps(result)


def fetch_resume_analysis(
    job_id: str,
    candidate_anon_id: str,
    candidate_document_path: str,
    competency_framework_json: str,
) -> str:
    try:
        framework = json.loads(competency_framework_json)
    except (json.JSONDecodeError, TypeError):
        framework = []
    return json.dumps(
        _post_internal(
            "/internal/hirelogic/resume-analysis",
            {
                "job_id": job_id,
                "candidate_anon_id": candidate_anon_id,
                "candidate_document_path": candidate_document_path,
                "competency_framework": framework,
            },
        )
    )


def fetch_candidate_scores(
    job_id: str,
    candidate_anon_id: str,
    evidence_by_competency_json: str,
    competency_framework_json: str,
    interview_feedback_json: str = "null",
    blend_ratio_json: str = "[0.6, 0.4]",
) -> str:
    try:
        evidence = json.loads(evidence_by_competency_json)
    except (json.JSONDecodeError, TypeError):
        evidence = {}
    try:
        framework = json.loads(competency_framework_json)
    except (json.JSONDecodeError, TypeError):
        framework = []
    try:
        feedback = json.loads(interview_feedback_json)
    except (json.JSONDecodeError, TypeError):
        feedback = None
    try:
        blend = json.loads(blend_ratio_json)
    except (json.JSONDecodeError, TypeError):
        blend = [0.6, 0.4]
    return json.dumps(
        _post_internal(
            "/internal/hirelogic/score-candidates",
            {
                "job_id": job_id,
                "candidate_anon_id": candidate_anon_id,
                "evidence_by_competency": evidence,
                "competency_framework": framework,
                "interview_feedback": feedback,
                "blend_ratio": blend,
            },
        )
    )


def fetch_bias_detection(job_id: str, all_scorecards_json: str) -> str:
    try:
        scorecards = json.loads(all_scorecards_json)
    except (json.JSONDecodeError, TypeError):
        scorecards = []
    return json.dumps(
        _post_internal(
            "/internal/hirelogic/detect-bias",
            {"job_id": job_id, "all_scorecards": scorecards},
        )
    )


def finalize_response(
    job_id: str,
    session_id: str,
    user_query: str,
    all_scorecards_json: str,
    bias_flags_json: str = "[]",
    prior_conversation_summary: str = "",
) -> str:
    try:
        scorecards = json.loads(all_scorecards_json)
    except (json.JSONDecodeError, TypeError):
        scorecards = []
    try:
        flags = json.loads(bias_flags_json)
    except (json.JSONDecodeError, TypeError):
        flags = []
    return json.dumps(
        _post_internal(
            "/internal/hirelogic/finalize-response",
            {
                "job_id": job_id,
                "session_id": session_id,
                "user_query": user_query,
                "all_scorecards": scorecards,
                "bias_flags": flags,
                "prior_conversation_summary": prior_conversation_summary,
            },
        )
    )


job_context_agent = Agent(
    name="job_context_agent",
    model=MODEL,
    description=(
        "Loads competency framework and candidate "
        "list for a job."
    ),
    instruction="""You are the Job Context Agent.

Extract job_id from the user question.
If the user says "Senior ML Engineer" use job_id="1".
If the user says "Backend Engineer" use job_id="2".
If a number is mentioned (job 1, job_id=1) use it.
- Default to "1" if unclear

Call fetch_job_context with the job_id.
Then call fetch_candidates_for_job with the same job_id.

Output ONLY this JSON, no fences, no other text:
{
  "job_id": "1",
  "title": "Senior ML Engineer",
  "competency_framework": [...],
  "candidates": [...]
}
""",
    tools=[fetch_job_context, fetch_candidates_for_job],
)

resume_analysis_agent = Agent(
    name="resume_analysis_agent",
    model=MODEL,
    description="Extracts evidence from resumes.",
    instruction="""You are the Resume Analysis Agent.

From the conversation context find the job_context_agent
output which contains:
- competency_framework: list of competencies
- candidates: list of candidate objects

For EACH candidate call fetch_resume_analysis with:
- job_id: the job_id string
- candidate_anon_id: the candidate's anon_id
- candidate_document_path: the candidate's document_path
- competency_framework_json: JSON string of framework

Call ALL candidates before outputting results.

Output ONLY this JSON, no fences:
{
  "resume_analysis_results": [
    {
      "candidate_anon_id": "candidate-uuid-001",
      "evidence_by_competency": {...}
    }
  ]
}
""",
    tools=[fetch_resume_analysis],
)

scoring_agent = Agent(
    name="scoring_agent",
    model=MODEL,
    description="Scores candidates 0-10 per competency.",
    instruction="""You are the Scoring Agent.

From context find resume_analysis_results and
competency_framework.

For EACH candidate call fetch_candidate_scores with:
- job_id: job_id string
- candidate_anon_id: candidate's anon_id
- evidence_by_competency_json: JSON string of evidence
- competency_framework_json: JSON string of framework
- interview_feedback_json: feedback JSON or "null"
- blend_ratio_json: "[0.6, 0.4]"

Output ONLY this JSON, no fences:
{
  "all_scorecards": [...],
  "job_id": "<from context>",
  "session_id": "1",
  "user_query": "<original user question>"
}
""",
    tools=[fetch_candidate_scores],
)

bias_agent = Agent(
    name="bias_agent",
    model=MODEL,
    description="Detects bias patterns across scorecards.",
    instruction="""You are the Bias Agent.

Find all_scorecards from scoring_agent output.
Find job_id from context.

Call fetch_bias_detection once:
- job_id: job_id string
- all_scorecards_json: JSON string of all_scorecards

Output ONLY this JSON, no fences:
{
  "bias_detection_result": {
    "bias_detected": false,
    "bias_flags": []
  }
}
""",
    tools=[fetch_bias_detection],
)

response_agent = Agent(
    name="response_agent",
    model=MODEL,
    description="Assembles final ranked response.",
    instruction="""You are the Response Agent.
Final step. Call finalize_response exactly once.

From scoring_agent output extract:
- all_scorecards, job_id, session_id, user_query

From bias_agent output extract:
- bias_flags ([] if none)

Call finalize_response with all values.

Output ONLY the raw JSON from finalize_response.
First char must be {, last must be }.
No fences. No extra text.
""",
    tools=[finalize_response],
)

conversation_agent = Agent(
    name="conversation_agent",
    model=MODEL,
    description="Answers follow-up questions using cached scorecard data.",
    instruction="""Answer follow-up questions using only existing ranking results and evidence.
Do not call tools, re-score candidates, or run the pipeline. Output plain text only.""",
    tools=[],
)

root_agent = SequentialAgent(
    name="hirelogic_agent",
    description=(
        "HireLogic 5-agent pipeline: "
        "Job Context → Resume Analysis → "
        "Scoring → Bias Detection → Response"
    ),
    sub_agents=[
        job_context_agent,
        resume_analysis_agent,
        scoring_agent,
        bias_agent,
        response_agent,
    ],
)

agent = root_agent

__all__ = [
    "MODEL",
    "BACKEND_BASE_URL",
    "AGENT_INTERNAL_SECRET",
    "DOCUMENTS_PATH",
    "fetch_job_context",
    "fetch_candidates_for_job",
    "fetch_resume_analysis",
    "fetch_candidate_scores",
    "fetch_bias_detection",
    "finalize_response",
    "job_context_agent",
    "resume_analysis_agent",
    "scoring_agent",
    "bias_agent",
    "response_agent",
    "conversation_agent",
    "root_agent",
    "agent",
    "SequentialAgent",
]


