from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_ROOT = REPO_ROOT / "documents"


def get_resource_overview(documents_path: str | None = None) -> dict[str, Any]:
    root = Path(documents_path) if documents_path else DOCUMENTS_ROOT
    with (root / "resource_index.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def read_segment(document_path: str, section_filename: str) -> str:
    candidates = [
        REPO_ROOT / document_path / section_filename,
        DOCUMENTS_ROOT / Path(document_path).name / section_filename,
        Path(document_path) / section_filename,
    ]
    for candidate in candidates:
        normalized = candidate.resolve(strict=False)
        if normalized.exists():
            return normalized.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Unable to locate {section_filename} in {document_path}")


def query_postgres(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {
        "status": "not_implemented",
        "message": "Database access is handled via backend internal routes.",
    }
