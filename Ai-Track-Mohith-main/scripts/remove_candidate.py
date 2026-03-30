#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = REPO_ROOT / "documents"
DB_URL_CANDIDATES = (
    os.environ.get("DATABASE_URL"),
    "postgresql://postgres:postgres@localhost:5433/app_scaffold",
    "postgresql://hirelogic:hirelogic@localhost:5432/hirelogic",
)


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


def parse_args() -> str:
    parser = argparse.ArgumentParser(description="Remove a HireLogic demo candidate.")
    parser.add_argument("--anon-id", type=str, required=True)
    parsed = parser.parse_args()
    return parsed.anon_id


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
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Unable to connect to Postgres: {last_error}")


async def remove_candidate(anon_id: str) -> None:
    conn = await connect_db()
    try:
        candidate_id = await conn.fetchval(
            "SELECT id FROM candidates WHERE anon_id = $1",
            anon_id,
        )
        if candidate_id is None:
            print(f"Candidate {anon_id} not found in database.")
        else:
            application_ids = await conn.fetch(
                "SELECT id FROM applications WHERE candidate_id = $1",
                candidate_id,
            )
            app_ids = [row["id"] for row in application_ids]
            if app_ids:
                await conn.execute(
                    "DELETE FROM interview_feedback WHERE application_id = ANY($1::int[])",
                    app_ids,
                )
                await conn.execute(
                    "DELETE FROM hiring_outcomes WHERE application_id = ANY($1::int[])",
                    app_ids,
                )
                await conn.execute(
                    "DELETE FROM applications WHERE id = ANY($1::int[])",
                    app_ids,
                )
            await conn.execute("DELETE FROM candidates WHERE id = $1", candidate_id)
    finally:
        await conn.close()

    candidate_dir = DOCUMENTS_ROOT / anon_id.replace("-", "_")
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)

    print(
        f"""
🧹 Candidate removed successfully!

  anon_id:   {anon_id}
  documents: documents/{anon_id.replace('-', '_')}/

The candidate will no longer appear in rankings.
""".strip()
    )


if __name__ == "__main__":
    asyncio.run(remove_candidate(parse_args()))
