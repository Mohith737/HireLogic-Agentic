"""Sample Google ADK agent.

Replace the greeting tool and agent definition with your own logic.
Run standalone:  adk run app.agent
Integrate via:   POST /api/v1/agent/run
"""

from __future__ import annotations

from typing import Any

_AgentCls: Any = None
_RunnerCls: Any = None
_SessionServiceCls: Any = None
genai_types: Any = None

try:
    from google.adk.agents import Agent as GoogleAgent
    from google.adk.runners import Runner as GoogleRunner
    from google.adk.sessions import InMemorySessionService as GoogleSessionService
    from google.genai import types as google_genai_types

    _AgentCls = GoogleAgent
    _RunnerCls = GoogleRunner
    _SessionServiceCls = GoogleSessionService
    genai_types = google_genai_types
    ADK_AVAILABLE = True
except ImportError:  # pragma: no cover - keeps API importable without ADK installed
    ADK_AVAILABLE = False


def greet(name: str) -> dict[str, str]:
    """Return a greeting for the given name."""
    return {"greeting": f"Hello, {name}! Welcome to App Scaffold."}


if ADK_AVAILABLE:
    root_agent: Any = _AgentCls(
        name="scaffold_agent",
        model="gemini-2.5-flash",
        description="A starter agent for the scaffold project.",
        instruction="You are a helpful assistant. Use the greet tool when asked to greet someone.",
        tools=[greet],
    )
else:

    class _FallbackAgent:
        name = "scaffold_agent"

    root_agent = _FallbackAgent()


async def run_agent(user_message: str, user_id: str = "user") -> str:
    """Run the agent with a single user message and return the final text response."""
    if not ADK_AVAILABLE:
        return f"ADK dependencies are not installed in this environment. Received: {user_message}"

    session_service = _SessionServiceCls()
    session = await session_service.create_session(
        app_name="scaffold_agent",
        user_id=user_id,
    )

    runner = _RunnerCls(
        agent=root_agent,
        app_name="scaffold_agent",
        session_service=session_service,
    )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=user_message)],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""

    return final_text
