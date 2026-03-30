# HireLogic - Codex Agent Instructions

## Project Overview
AI-powered candidate screening and ranking system.
Recruiters interact via natural language to rank candidates,
detect bias, and get explainable hiring recommendations.

## Stack
- Frontend:  React 18 + TypeScript + MUI v6      (client/)
- Backend:   FastAPI + SQLAlchemy async + Postgres (server/)
- Agent:     Google ADK + Gemini 2.5 Flash        (hirelogic_agent/)
- Documents: Job descriptions + candidate resumes  (documents/)

## Folder Structure
client/           React frontend
server/           FastAPI backend + DB models + migrations
hirelogic_agent/  ADK agent, sub-agents, evals, tools
documents/        Job and candidate source documents (TOC-first)
scripts/          Utility scripts for candidate management

## Key Files
hirelogic_agent/agents/hirelogic_agent.py  <- root supervisor agent
hirelogic_agent/backend_chat.py            <- ADK runner
hirelogic_agent/agents/tools.py            <- merged helper tool module
server/app/api/routes/hirelogic.py         <- /api/v1/hirelogic/chat
documents/resource_index.json             <- TOC root, read first
Solution.md                               <- architecture decisions
Spec.md                                   <- problem statement

## Rules
- NEVER modify files in documents/ directly
- NEVER put business logic in agent files - use /internal/ routes
- NEVER pass JWT tokens through LLM - use x-agent-secret header
- ALWAYS run `cd client && npx tsc --noEmit` after frontend changes
- ALWAYS run `cd server && python -m pytest tests/` after backend changes
- ALWAYS read Solution.md before making architecture decisions

## Environment Variables
server/.env             backend secrets + DATABASE_URL
hirelogic_agent/.env    GOOGLE_API_KEY + AGENT_INTERNAL_SECRET
