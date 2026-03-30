# HireLogic — Solution Document

## 1. System Overview
HireLogic is an AI-assisted recruiting system for screening and ranking
candidates against weighted job competencies. Recruiters ask natural-language
questions in the frontend, the backend orchestrates the ranking flow, and the
agent layer remains available for ADK contracts and evaluation.

Current top-level layout:
- `client/` -> React + TypeScript recruiter UI
- `server/` -> FastAPI API, auth, Postgres models, internal scoring routes
- `hirelogic_agent/` -> ADK agent definitions, eval suite, runtime helper
- `documents/` -> root TOC plus blinded job and candidate source documents

## 2. Runtime Architecture
The current production path is Python-first and low-latency.
It does not depend on a long-running multi-agent ADK conversation for every
ranking request.

### Entry Point
Recruiter chat requests hit:
- `POST /api/v1/hirelogic/chat`
- implemented in `server/app/api/routes/hirelogic.py`

That route:
1. authenticates the recruiter with JWT
2. loads `hirelogic_agent/.env`
3. imports `hirelogic_agent/backend_chat.py`
4. runs the async orchestration in a worker thread so the FastAPI event loop
   stays free for internal route calls

### Primary Orchestrator
`hirelogic_agent/backend_chat.py` is the live runtime orchestrator.

It handles:
- out-of-scope redirects
- ambiguous job clarification
- follow-up explanation turns using cached scorecards
- weight-adjustment reranking
- full ranking pipeline execution

### Internal API Boundary
All business logic lives behind backend internal routes.
The agent/runtime layer never directly touches Postgres models and never sends
JWTs through model prompts.

Internal routes used by the runtime:
- `POST /internal/hirelogic/job-context`
- `POST /internal/hirelogic/candidate-profiles`
- `POST /internal/hirelogic/resume-analysis`
- `POST /internal/hirelogic/score-candidates`
- `POST /internal/hirelogic/detect-bias`
- `POST /internal/hirelogic/finalize-response`

Authentication between runtime and backend is done with:
- `x-agent-secret`

## 3. Full Ranking Flow
For a normal ranking request, the live path is:

1. Read `documents/resource_index.json`
   - used as the root TOC sanity check

2. Load job context
   - fetch job title and weighted competency framework
   - apply any weight overrides from the user request

3. Load active candidates
   - returns anonymized candidates only
   - excludes historical hired/rejected records from ranking input

4. Run candidate processing in parallel
   - resume analysis per candidate
   - evidence validation against source sections
   - evidence compression
   - scoring per candidate

5. Run bias detection once across all scorecards

6. Finalize response on the backend
   - assemble scorecard + ranking
   - generate recruiter-facing reply
   - persist chat messages
   - attach sources used and updated conversation summary

Measured local runtime after optimization was reduced from the older
multi-agent path to roughly sub-second to low-single-digit-second behavior
depending on environment and backend availability.

## 4. Candidate Processing Details
Per-candidate work is performed in parallel inside `backend_chat.py`.

Each candidate goes through:
1. `resume-analysis`
   - maps blinded markdown evidence to competencies
2. `validate_resume_analysis()`
   - checks grounding and low-confidence fields
3. `compress_evidence()`
   - shortens evidence before scoring
4. `score-candidates`
   - computes weighted competency and overall scores
   - blends interview feedback when present

Supporting backend service modules:
- `server/app/services/validation.py`
- `server/app/services/response_service.py`

## 5. Follow-up and Routing Behavior
The current live routing behavior is:

- Follow-up questions:
  - handled from cached scorecards in `FOLLOWUP_CACHE`
  - no full rerun when the prior ranking context exists

- Weight adjustments:
  - rerun the ranking path with updated competency weights

- Ambiguous questions:
  - return a clarification prompt for job selection

- Out-of-scope questions:
  - return a recruiter-scope redirect message

Important note:
- the ADK eval suite still treats follow-up routing as a known gap for strict
  deterministic evaluation, even though the live runtime contains a pragmatic
  follow-up path

## 6. ADK Agent Layer
`hirelogic_agent/agents/hirelogic_agent.py` is now a slim contract layer.

Its purpose is:
- preserve the 5-agent ADK graph for evaluation and inspection
- define tool contracts against backend internal routes
- keep Gemini-facing instructions for the reasoning-heavy steps

It is not the main latency-critical production runtime anymore.

Current defined agents:
- `job_context_agent`
- `resume_analysis_agent`
- `scoring_agent`
- `bias_agent`
- `response_agent`

The main live ranking path is still `backend_chat.py`.

## 7. Document Architecture
Documents now live at the repo root:
- `documents/resource_index.json`
- `documents/job_*`
- `documents/candidate_uuid_*`
- `documents/historical_hiring_outcomes`

Document model:
- PDFs are retained as source artifacts
- markdown sections are the agent-readable representation
- metadata and `index.json` are stored per document folder

Blind extraction rules:
- candidate names removed
- universities replaced with placeholders
- gendered self-references removed
- anonymous IDs preserved for ranking

## 8. Session and Response State
The runtime keeps lightweight session state in memory for follow-ups:

```json
{
  "job_id": "1",
  "weight_overrides": {},
  "prior_scorecard": {},
  "prior_conversation_summary": ""
}
```

The finalized backend response contains:
- `scorecard`
- `ranking`
- `bias_flags`
- `reply`
- `session_id`
- `updated_conversation_summary`
- `sources_used`

## 9. Evaluation Strategy
Current active eval coverage lives in:
- `hirelogic_agent/evals/agent_eval.py`

Active passing suite:
- ranking pipeline
- bias detection

Preserved but disabled:
- follow-up routing eval (`evalset3`)
  - disabled because routing behavior is not yet deterministic enough for
    strict repeatable evaluation

Current metric strategy:
- `rubric_based_tool_use_quality_v1`
- `final_response_match_v2`

Removed intentionally:
- `tool_trajectory_avg_score`
- `response_match_score`

Reason:
- exact tool-argument matching is too brittle for dynamic JSON payloads
- ROUGE-style lexical scoring is a poor fit for wrapped JSON responses

## 10. Security and Boundaries
Key design rules currently enforced:
- recruiter JWT stays between frontend and backend only
- LLM/runtime calls use `x-agent-secret`, not recruiter tokens
- candidate identity remains anonymized in ranking responses
- backend owns scoring persistence and response assembly
- documents remain TOC-first and blinded

## 11. Current Gaps
The system is functional, but these remain true:
- `Solution.md` now reflects the current runtime, but some older repo docs may
  still describe the historical multi-agent-first architecture
- follow-up routing is good enough for runtime use, but not yet deterministic
  enough to be a strict active eval case
- `hirelogic_agent/agents/tools.py` exists for structural cleanliness; the live
  runtime orchestration still primarily uses `backend_chat.py` and backend
  internal routes
