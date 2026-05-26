from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

PRIVATE_PATH_MARKERS = ("C:/Users/", "C:\\Users\\", "/Users/")


def redact_private_path(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "<PRIVATE_LOCAL_PATH>/unknown"
    out = text
    out = out.replace("C:/Users/", "<PRIVATE_LOCAL_PATH>/")
    out = out.replace("C:\\Users\\", "<PRIVATE_LOCAL_PATH>\\")
    out = out.replace("/Users/", "<PRIVATE_LOCAL_PATH>/")
    return out


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class ModelWitnessStatus:
    witness_id: str
    witness_name: str
    witness_type: str
    backend: str
    required_for_pipeline: bool
    configured: bool
    installed: bool
    smoke_test_passed: bool
    available: bool
    gate_status: str
    unavailable_reason: str
    blockers: list[str] = field(default_factory=list)
    next_setup_step: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["metadata"] = {
            str(k): (redact_private_path(v) if isinstance(v, str) else v) for k, v in self.metadata.items()
        }
        return payload


@dataclass(frozen=True)
class ModelWitnessAudit:
    generated_at: str
    gate_rule: str
    witnesses: list[ModelWitnessStatus]
    counters: dict[str, int]
    blockers: list[str]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "gate_rule": self.gate_rule,
            "witnesses": [row.to_dict() for row in self.witnesses],
            "counters": dict(self.counters),
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
        }
