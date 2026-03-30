import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

AGENTS_DIR = Path(__file__).resolve().parents[1]
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

load_dotenv(AGENTS_DIR / ".env")
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


@pytest.fixture(autouse=True)
def check_backend():
    """
    Verify backend is reachable before each eval.
    Evals require tool calls -> backend on port 8000.
    """
    import httpx

    try:
        response = httpx.get("http://localhost:8000/health", timeout=3.0)
        if response.status_code != 200:
            pytest.skip(
                "Backend not healthy on port 8000. Start with: "
                "uvicorn app.main:app --port 8000"
            )
    except Exception:
        pytest.skip(
            "Backend not reachable on port 8000. Start with: cd server && "
            "uvicorn app.main:app --port 8000 --reload"
        )
