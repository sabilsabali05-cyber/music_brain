from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .model_role_registry import MODEL_ROLE_REGISTRY

ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_INTEGRATION_REPORTS = ROOT_DIR / "reports" / "model_integration"
WITNESS_REPORTS = ROOT_DIR / "reports" / "model_witnesses"
ORDERED_MODELS = ["basicpitch", "demucs", "moonbeam", "mt3", "omnizart", "musicbert", "midigpt", "text2midi"]


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", "", f"- generated_at: `{payload.get('generated_at', '')}`"]
    for key, value in payload.items():
        if key == "generated_at":
            continue
        lines.append(f"- {key}: `{value}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _model_report_stem(model: str) -> str:
    return {
        "basicpitch": "basicpitch_integration_report",
        "demucs": "demucs_integration_report",
        "moonbeam": "moonbeam_integration_report",
        "mt3": "mt3_integration_report",
        "omnizart": "omnizart_integration_report",
        "musicbert": "musicbert_integration_report",
        "midigpt": "midigpt_integration_report",
        "text2midi": "text2midi_integration_report",
    }[model]


def _witness_row(model: str, report: dict[str, Any]) -> dict[str, Any]:
    role = MODEL_ROLE_REGISTRY[model]
    active = bool(report.get("active", False))
    real_observation = int(report.get("real_backend_observation", 0))
    callable_witness = active and real_observation > 0
    reason = str(report.get("reason", ""))
    if not reason and callable_witness:
        reason = "real_output_verified"
    return {
        "model": model,
        "role": role.role,
        "witness_required": role.witness_required,
        "callable_witness": callable_witness,
        "active_reported": active,
        "real_backend_observation": real_observation,
        "status": str(report.get("status", "unknown")),
        "reason": reason,
        "fallback_behavior": role.fallback_behavior,
    }


def build_witness_artifacts() -> dict[str, Any]:
    WITNESS_REPORTS.mkdir(parents=True, exist_ok=True)
    reports: dict[str, dict[str, Any]] = {}
    for model in ORDERED_MODELS:
        stem = _model_report_stem(model)
        reports[model] = _read_json(MODEL_INTEGRATION_REPORTS / f"{stem}.json")

    witness_rows = [_witness_row(model, reports[model]) for model in ORDERED_MODELS]
    required_missing = [
        row["model"] for row in witness_rows if row["witness_required"] and not bool(row["callable_witness"])
    ]
    callable_models = [row["model"] for row in witness_rows if bool(row["callable_witness"])]
    optional_blocked = [
        {"model": row["model"], "reason": row["reason"]}
        for row in witness_rows
        if not row["witness_required"] and not bool(row["callable_witness"])
    ]

    baseline = {
        "generated_at": _timestamp(),
        "required_witnesses": [row["model"] for row in witness_rows if row["witness_required"]],
        "callable_witnesses": callable_models,
        "required_witnesses_missing": required_missing,
        "minimum_stack_ready": len(required_missing) == 0,
        "models": witness_rows,
    }
    _write_json(WITNESS_REPORTS / "baseline_witness_reverification.json", baseline)
    _write_md(WITNESS_REPORTS / "baseline_witness_reverification.md", "Baseline Witness Reverification", baseline)

    for row in witness_rows:
        per_model = {
            "generated_at": _timestamp(),
            "model": row["model"],
            "role": row["role"],
            "callable_witness": row["callable_witness"],
            "status": row["status"],
            "reason": row["reason"],
            "fallback_behavior": row["fallback_behavior"],
            "real_backend_observation": row["real_backend_observation"],
        }
        stem = f"{row['model']}_product_activation"
        _write_json(WITNESS_REPORTS / f"{stem}.json", per_model)
        _write_md(WITNESS_REPORTS / f"{stem}.md", f"{row['model']} Product Activation", per_model)

    expansion_plan = {
        "generated_at": _timestamp(),
        "active_callable_models": callable_models,
        "required_missing": required_missing,
        "optional_blocked": optional_blocked,
        "next_expansion_priority": [entry["model"] for entry in optional_blocked],
        "gating_policy": {
            "no_fake_activations": True,
            "real_output_required_for_witness": True,
            "fallbacks_must_be_explicit": True,
        },
    }
    _write_json(WITNESS_REPORTS / "model_stack_expansion_plan.json", expansion_plan)
    _write_md(WITNESS_REPORTS / "model_stack_expansion_plan.md", "Model Stack Expansion Plan", expansion_plan)
    return {
        "baseline": baseline,
        "expansion_plan": expansion_plan,
    }

