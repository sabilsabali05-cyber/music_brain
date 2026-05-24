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

from features.model_integrations.model_policy import source_separation_witness_policy_state

REPORT_DIR = ROOT_DIR / "reports" / "source_separation"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_source_separation_witness_plan() -> dict[str, Any]:
    policy = source_separation_witness_policy_state()
    return {
        "status": "planned",
        "created_at": _now_iso(),
        "demucs_available": policy["demucs_available"],
        "source_separation_performed": policy["source_separation_performed"],
        "stems_generated": policy["stems_generated"],
        "audio_processing_performed": False,
        "downloads_performed": policy["downloads_performed"],
        "model_training_has_occurred": policy["model_training_has_occurred"],
        "witness_policy": policy["witness_policy"],
        "training_use_allowed": policy["training_use_allowed"],
        "no_fake_stems": True,
        "workflow_plan": [
            "Step 1: Keep Demucs disabled unless explicit local witness setup is configured.",
            "Step 2: Require explicit command and explicit user-provided input before any future separation execution.",
            "Step 3: Treat stems strictly as weak evidence for arrangement and texture inspection.",
            "Step 4: Never claim stem outputs as ground truth labels.",
            "Step 5: Preserve no-download and no-training defaults in this vertical slice.",
        ],
        "limitations": [
            "Plan-only scaffold; no source separation execution occurs.",
            "No audio is processed and no model downloads are triggered.",
            "No model training is performed or claimed.",
        ],
        "next_setup_step": (
            "Copy config/model_integrations/model_integrations.example.json to "
            "config/model_integrations/model_integrations.local.json and set models.demucs.enabled=true "
            "only when explicit witness execution wiring is intentionally enabled."
        ),
    }


def write_plan_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = build_source_separation_witness_plan()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source_separation_witness_plan.json"
    md_path = output_dir / "source_separation_witness_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Separation Witness Plan",
        "",
        f"- status: `{payload['status']}`",
        f"- demucs_available: `{payload['demucs_available']}`",
        "- source_separation_performed: `False`",
        "- stems_generated: `False`",
        "- audio_processing_performed: `False`",
        "- downloads_performed: `False`",
        "- model_training_has_occurred: `False`",
        f"- witness_policy: `{payload['witness_policy']}`",
        "- training_use_allowed: `false_by_default`",
        "",
        "## Next Setup Step",
        f"- {payload['next_setup_step']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan source separation witness workflow without execution.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_plan_report(output_dir)
    print(f"SOURCE_SEPARATION_WITNESS_PLAN_JSON={json_path.as_posix()}")
    print(f"SOURCE_SEPARATION_WITNESS_PLAN_MD={md_path.as_posix()}")
    print(f"PLAN_STATUS={payload['status']}")
    print("DEMUCS_AVAILABLE=False")
    print("SOURCE_SEPARATION_PERFORMED=False")
    print("STEMS_GENERATED=False")
    print("AUDIO_PROCESSING_PERFORMED=False")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    print("WITNESS_POLICY=weak_evidence_not_truth")
    print("TRAINING_USE_ALLOWED=false_by_default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
