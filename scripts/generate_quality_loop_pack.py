from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_witnesses.model_stack_orchestrator import build_witness_artifacts
from features.quality_loop_product.model_integrated_quality_scorer import build_ensemble_scoring_summary
from scripts.build_quality_loop_product_pass import run_quality_pass
from scripts.run_model_integration_lock_campaign import run_lock_campaign

REPORT_DIR = ROOT_DIR / "reports" / "quality_loop_product"


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


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


def run_model_integrated_quality_pack() -> dict[str, Any]:
    lock_payload = run_lock_campaign()
    witness_payload = build_witness_artifacts()
    quality_payload = run_quality_pass()
    ensemble = build_ensemble_scoring_summary(witness_payload["baseline"]).to_dict()

    gate = quality_payload["gate"]
    base_passed = bool(gate.get("pack_passed", False))
    model_integrated_passed = base_passed and not ensemble["required_missing_models"]
    merged_blockers = list(gate.get("blockers", [])) + list(ensemble.get("blockers", []))
    merged_blockers = sorted(set(str(item) for item in merged_blockers if str(item).strip()))

    integrated_gate = {
        "generated_at": _timestamp(),
        "pack_id": "quality_loop_pack_v1",
        "base_pack_passed": base_passed,
        "model_integrated_pack_passed": model_integrated_passed,
        "base_gate_path": "reports/quality_loop_product/quality_loop_pack_v1_gate.json",
        "required_witnesses_missing": ensemble["required_missing_models"],
        "callable_witness_models": ensemble["callable_witness_models"],
        "ensemble_multiplier": ensemble["quality_multiplier"],
        "ensemble_score_offset": ensemble["score_offset"],
        "fallbacks_applied": ensemble["fallbacks"],
        "blockers": merged_blockers,
        "local_only_outputs": True,
        "privacy_mode": "normal_iteration_non_blocking_release_blocking",
    }

    integrated_report = {
        "generated_at": _timestamp(),
        "source_loop": lock_payload.get("source_loop", {}),
        "model_status": lock_payload.get("results", {}),
        "quality_report": quality_payload.get("report", {}),
        "integrated_gate_path": "reports/quality_loop_product/model_integrated_quality_pack_v1_gate.json",
        "model_integrated_pack_passed": model_integrated_passed,
        "required_missing_models": ensemble["required_missing_models"],
        "callable_witness_models": ensemble["callable_witness_models"],
        "ensemble_multiplier": ensemble["quality_multiplier"],
        "ensemble_score_offset": ensemble["score_offset"],
        "blockers": merged_blockers,
    }

    _write_json(REPORT_DIR / "model_integrated_quality_pack_v1_gate.json", integrated_gate)
    _write_md(REPORT_DIR / "model_integrated_quality_pack_v1_gate.md", "Model Integrated Quality Pack v1 Gate", integrated_gate)
    _write_json(REPORT_DIR / "model_integrated_quality_pack_v1_report.json", integrated_report)
    _write_md(REPORT_DIR / "model_integrated_quality_pack_v1_report.md", "Model Integrated Quality Pack v1 Report", integrated_report)

    # Compatibility mirrors for tools expecting generic report stems.
    _write_json(REPORT_DIR / "report.json", integrated_report)
    _write_md(REPORT_DIR / "report.md", "Quality Loop Product Report", integrated_report)
    return {
        "integrated_gate": integrated_gate,
        "integrated_report": integrated_report,
    }


def main() -> int:
    payload = run_model_integrated_quality_pack()
    gate = payload["integrated_gate"]
    print(f"MODEL_INTEGRATED_PACK_PASSED={str(gate['model_integrated_pack_passed']).lower()}")
    print(f"CALLABLE_WITNESSES={','.join(gate['callable_witness_models'])}")
    print(f"REQUIRED_MISSING={','.join(gate['required_witnesses_missing'])}")
    print("GATE_JSON=reports/quality_loop_product/model_integrated_quality_pack_v1_gate.json")
    print("REPORT_JSON=reports/quality_loop_product/model_integrated_quality_pack_v1_report.json")
    return 0 if bool(gate["model_integrated_pack_passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

