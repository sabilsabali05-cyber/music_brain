from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_integrations.model_policy import transcription_witness_policy_state

REPORT_DIR = ROOT_DIR / "reports" / "transcription_witnesses"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_transcription_witness_plan() -> dict[str, Any]:
    policy = transcription_witness_policy_state()
    return {
        "status": "planned",
        "created_at": _now_iso(),
        "yourmt3_available": policy["yourmt3_available"],
        "basic_pitch_available": policy["basic_pitch_available"],
        "transcription_performed": policy["transcription_performed"],
        "model_training_has_occurred": policy["model_training_has_occurred"],
        "witness_policy": policy["witness_policy"],
        "audio_processing_performed": False,
        "downloads_performed": False,
        "no_fake_transcription_outputs": True,
        "workflow_plan": [
            "Step 1: Keep both witness backends disabled unless local config is explicitly enabled.",
            "Step 2: Require explicit command + explicit user input before any future witness inference call.",
            "Step 3: Record witness outputs as optional evidence only; never promote to truth labels automatically.",
            "Step 4: Preserve no-download and no-training guarantees for this vertical slice.",
            "Step 5: Add future execution hooks only behind explicit opt-in flags and policy checks.",
        ],
        "limitations": [
            "Plan-only scaffold; no transcription execution occurs.",
            "No audio is processed and no model downloads are triggered.",
            "No model training is performed or claimed.",
        ],
        "next_setup_step": (
            "Copy config/model_integrations/model_integrations.example.json to "
            "config/model_integrations/model_integrations.local.json and keep yourmt3/basic_pitch disabled "
            "until explicit witness execution wiring is intentionally enabled."
        ),
    }


def write_plan_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = build_transcription_witness_plan()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "transcription_witness_plan.json"
    md_path = output_dir / "transcription_witness_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Transcription Witness Plan",
        "",
        f"- status: `{payload['status']}`",
        f"- yourmt3_available: `{payload['yourmt3_available']}`",
        f"- basic_pitch_available: `{payload['basic_pitch_available']}`",
        f"- transcription_performed: `{payload['transcription_performed']}`",
        f"- witness_policy: `{payload['witness_policy']}`",
        "- model_training_has_occurred: `False`",
        "- audio_processing_performed: `False`",
        "- downloads_performed: `False`",
        "",
        "## Next Setup Step",
        f"- {payload['next_setup_step']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan transcription witness workflow without execution.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_plan_report(output_dir)
    print(f"TRANSCRIPTION_WITNESS_PLAN_JSON={json_path.as_posix()}")
    print(f"TRANSCRIPTION_WITNESS_PLAN_MD={md_path.as_posix()}")
    print(f"PLAN_STATUS={payload['status']}")
    print("YOURMT3_AVAILABLE=False")
    print("BASIC_PITCH_AVAILABLE=False")
    print("TRANSCRIPTION_PERFORMED=False")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    print("WITNESS_POLICY=witness_not_truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
