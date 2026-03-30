"""
Standalone test runner for HireLogic agent.
Usage: python run_agent.py
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

load_dotenv()

from backend_chat import run_hirelogic

TEST_CASES = [
    {
        "name": "Full ranking — Senior ML Engineer",
        "question": ("Rank all candidates for the " "Senior ML Engineer role"),
        "job_id": 1,
        "session_id": 101,
        "user_id": "test_user_suite",
    },
    {
        "name": "Follow-up comparison",
        "question": ("Why is the top ranked candidate " "higher than the others?"),
        "job_id": 1,
        "session_id": 101,
        "user_id": "test_user_suite",
    },
    {
        "name": "Weight adjustment",
        "question": (
            "Re-rank candidates for Senior ML Engineer "
            "but increase Python weight to 40%"
        ),
        "job_id": 1,
        "session_id": 102,
        "user_id": "test_user_suite",
    },
    {
        "name": "Ambiguous query — no job_id",
        "question": "Rank the candidates",
        "job_id": None,
        "session_id": 103,
        "user_id": "test_user_suite",
    },
    {
        "name": "Out of scope",
        "question": "What is the weather in Bengaluru today?",
        "job_id": None,
        "session_id": 104,
        "user_id": "test_user_suite",
    },
]


async def main() -> None:
    print("=" * 60)
    print("HireLogic Agent — Full Test Suite")
    print("=" * 60)

    results: dict[int, tuple[str, str]] = {}
    test2_answer = ""

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 60}")
        print(f"[TEST {i}] {test['name']}")
        print(f"Question: {test['question']}")
        print("-" * 40)

        try:
            result = await asyncio.wait_for(
                run_hirelogic(
                    question=test["question"],
                    user_id=test["user_id"],
                    session_id=test["session_id"],
                    job_id=test["job_id"],
                ),
                timeout=200.0,
            )
        except asyncio.TimeoutError:
            result = {
                "answer": "TIMEOUT",
                "scorecard": None,
                "ranking": [],
                "bias_flags": [],
            }
        except Exception as exc:
            result = {
                "answer": f"ERROR: {exc}",
                "scorecard": None,
                "ranking": [],
                "bias_flags": [],
            }

        answer = result.get("answer", "")
        scorecard = result.get("scorecard")
        ranking = result.get("ranking", [])
        print(f"Answer: {answer[:200]}")
        print(f"Scorecard: {scorecard is not None}")
        print(f"Rankings: {len(ranking)}")
        if i == 1:
            passed = (
                result.get("scorecard") is not None
                and len(result.get("ranking", [])) >= 2
            )
            reason = "" if passed else "missing scorecard or ranking"
        elif i == 2:
            test2_answer = str(answer)
            passed = (
                len(str(answer)) > 30
                and "TIMEOUT" not in str(answer)
                and "ERROR" not in str(answer)
                and "422" not in str(answer)
                and "500" not in str(answer)
            )
            reason = "" if passed else "follow-up answer missing or errored"
        else:
            if i == 3:
                passed = (
                    result.get("scorecard") is not None
                    and len(result.get("ranking", [])) >= 2
                )
                reason = "" if passed else "missing rerank scorecard or ranking"
            elif i == 4:
                passed = (
                    result.get("scorecard") is None
                    and len(str(answer)) > 10
                    and "TIMEOUT" not in str(answer)
                    and "ERROR" not in str(answer)
                    and (
                        "which role" in str(answer).lower()
                        or "job" in str(answer).lower()
                        or "role" in str(answer).lower()
                    )
                )
                reason = "" if passed else "no clarification question returned"
            else:
                passed = (
                    result.get("scorecard") is None
                    and len(str(answer)) > 10
                    and "TIMEOUT" not in str(answer)
                    and "ERROR" not in str(answer)
                )
                reason = "" if passed else "out-of-scope response invalid"

        status = "PASS" if passed else "FAIL"
        results[i] = (status, reason)
        print(f"Result: {status}")

    print(f"\n{'=' * 60}")
    print("FINAL RESULTS")
    print("=" * 60)
    for i in range(1, len(TEST_CASES) + 1):
        status, reason = results[i]
        suffix = f" — {reason}" if reason else ""
        print(f"TEST {i}: {status}{suffix}")
    passing = sum(1 for status, _ in results.values() if status == "PASS")
    print(f"\nTEST 2 answer (full): {test2_answer}")
    print(f"Total: {passing}/5 passing")


asyncio.run(main())
