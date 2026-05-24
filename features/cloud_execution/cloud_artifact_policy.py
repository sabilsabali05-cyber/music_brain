from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PRIVATE_PATTERNS = [
    (re.compile(r"https://[^\s\"']*X-Amz-Signature=[^\s\"']+", flags=re.IGNORECASE), "<REDACTED_SIGNED_URL>"),
    (re.compile(r"\b(?:s3|gs|az)://[^\s\"']+", flags=re.IGNORECASE), "<REDACTED_BUCKET_PATH>"),
    (re.compile(r"[A-Za-z]:\\\\Users\\\\[^\s\"']+", flags=re.IGNORECASE), "<PRIVATE_USERS_PATH>"),
    (re.compile(r"[A-Za-z]:/Users/[^\s\"']+", flags=re.IGNORECASE), "<PRIVATE_USERS_PATH>"),
]

DEVICE_PATTERN = re.compile(r"\b(?:cuda:\d+|cpu|mps|gpu|npu)\b", flags=re.IGNORECASE)
SECRET_NAME_PATTERN = re.compile(r"\b(?:MODAL_TOKEN(?:_ID|_SECRET)?|HF_TOKEN|REPLICATE_API_TOKEN)\b")


def redact_public_text(text: str) -> str:
    redacted = text
    for pattern, token in PRIVATE_PATTERNS:
        redacted = pattern.sub(token, redacted)
    redacted = DEVICE_PATTERN.sub("<REDACTED_DEVICE>", redacted)
    redacted = SECRET_NAME_PATTERN.sub("<REDACTED_SECRET_NAME>", redacted)
    return redacted


def redact_public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(redact_public_text(json.dumps(payload, ensure_ascii=True)))


def verify_artifact_provenance(artifact_path: str | Path | None, provenance: dict[str, Any] | None) -> tuple[bool, str]:
    if artifact_path is None:
        return False, "missing_artifact_path"
    path = Path(artifact_path)
    if not path.exists():
        return False, "artifact_missing_on_disk"
    if not isinstance(provenance, dict):
        return False, "missing_provenance"
    if str(provenance.get("artifact_path", "")).strip() != path.as_posix():
        return False, "provenance_artifact_path_mismatch"
    if not bool(provenance.get("producer_confirmed", False)):
        return False, "provenance_not_confirmed"
    return True, "ok"
