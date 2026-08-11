"""Write per-question artifact directories and meta.json."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def question_artifact_dir(artifacts_root: Path, question_id: str) -> Path:
    path = artifacts_root / question_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_meta(directory: Path, meta: dict[str, Any]) -> Path:
    payload = {
        **meta,
        "written_at": datetime.now(UTC).isoformat(),
    }
    path = directory / "meta.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
