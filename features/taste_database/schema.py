from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

ABSOLUTE_PATH_HINT = re.compile(r"^[A-Za-z]:[\\/]|^/|^\\\\")


def hash_identifier(value: str) -> str:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact_private_path(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "<PRIVATE_LOCAL_PATH>/unknown"
    if "<PRIVATE_LOCAL_PATH>" in text:
        return text
    if ABSOLUTE_PATH_HINT.search(text):
        return "<PRIVATE_LOCAL_PATH>/indexed"
    if ":" in text or "\\" in text:
        return "<PRIVATE_LOCAL_PATH>/indexed"
    return text


@dataclass(frozen=True)
class ModelDerivedRef:
    witness_id: str
    witness_tool: str
    witness_role: str
    derived_output_ref_hash: str
    confidence: float = 0.0
    output_committed_inline: bool = False

    def __post_init__(self) -> None:
        role = self.witness_role.strip().lower()
        if role not in {"tool", "witness"}:
            raise ValueError("witness_role must be tool|witness")
        object.__setattr__(self, "witness_role", role)
        object.__setattr__(self, "output_committed_inline", bool(self.output_committed_inline))
        if self.output_committed_inline:
            raise ValueError("model derived outputs cannot be committed inline")
        if not str(self.derived_output_ref_hash).strip():
            raise ValueError("derived_output_ref_hash is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TasteItemRecord:
    taste_item_id: str
    loop_id: str
    source_id_hash: str
    source_redacted_path: str
    model_witness_refs: list[ModelDerivedRef]
    retrieval_tags: list[str] = field(default_factory=list)
    feedback_summary: dict[str, Any] = field(default_factory=dict)
    training_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.loop_id.strip():
            raise ValueError("loop_id is required")
        object.__setattr__(self, "source_redacted_path", redact_private_path(self.source_redacted_path))
        object.__setattr__(self, "training_allowed", bool(self.training_allowed))
        if self.training_allowed:
            raise ValueError("training must be disabled by default")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["model_witness_refs"] = [row.to_dict() for row in self.model_witness_refs]
        return payload


def validate_taste_item_record(payload: dict[str, Any]) -> tuple[bool, str]:
    path = str(payload.get("source_redacted_path", ""))
    if "<PRIVATE_LOCAL_PATH>" not in path:
        return False, "missing_private_path_placeholder"
    if not str(payload.get("loop_id", "")).strip():
        return False, "missing_loop_id"
    if bool(payload.get("training_allowed", False)):
        return False, "training_must_be_disabled_default"
    refs = payload.get("model_witness_refs", [])
    if not isinstance(refs, list) or not refs:
        return False, "missing_model_witness_refs"
    return True, "ok"
