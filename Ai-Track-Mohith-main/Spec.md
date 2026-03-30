# HireLogic — Recruitment & Candidate Assessment Agent
## Specification Document

## 1. Project Scenario
HireLogic supports recruiter teams that need to evaluate unstructured resumes against structured competency frameworks. The system converts job descriptions into weighted competencies, extracts blinded evidence from resumes, ranks candidates semantically, and returns explainable scorecards with bias checks.

## 2. Functional Requirements
- FR-1: Parse job descriptions into weighted competency frameworks.
- FR-2: Analyze resume content from PDF source artifacts and blinded markdown sections.
- FR-3: Score and rank candidates with evidence-backed explanations.
- FR-4: Detect bias signals through statistical and counterfactual analysis.
- FR-5: Support follow-up recruiter conversation without full re-scoring when prior scorecards exist.
- FR-6: Return structured JSON with scorecard, ranking, bias flags, and reply.
- FR-7: Enforce TOC-first retrieval from `resource_index.json`.
- FR-8: Enforce blind extraction before agent-readable sections are stored.

## 3. Non-Functional Requirements
- NFR-1: Single-candidate scoring target under 4 seconds.
- NFR-2: 50-candidate batch target under 30 seconds.
- NFR-3: `hallucinations_v1` threshold at or above 0.95.
- NFR-4: Counterfactual bias delta under 3%.
- NFR-5: PDF upload support for recruiter source artifacts.
- NFR-6: OCR-compatible pipeline for scanned documents.

## 4. Acceptance Criteria
- AC-1: Agents read `resource_index.json` before any document section.
- AC-2: Candidate sections contain no names, universities, or gender pronouns.
- AC-3: Scorecards cite section-grounded evidence per competency.
- AC-4: Bias flags appear when protected-attribute proxies influence outcomes.
- AC-5: Follow-up queries reuse cached scorecards when available.
- AC-6: Evaluation thresholds in `test_config.json` pass in CI.

## 5. Tech Stack
- Frontend: React, TypeScript, Vite
- Backend: FastAPI, PostgreSQL, SQLAlchemy async
- Agents: Google ADK, Gemini 2.5 Flash
- Documents: Markdown sections paired with source PDFs
- Evaluation: ADK eval with golden datasets

## 6. Evaluation Metrics and Thresholds
- `rubric_based_tool_use_quality_v1`: 0.70 for ranking, 0.60 for bias
- `final_response_match_v2`: 0.70 for ranking, 0.60 for bias
- Follow-up routing eval is preserved but currently disabled due to
  nondeterministic routing behavior
