from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.check_source_separation_setup import evaluate_source_separation_setup


def run_source_separation_smoke_tests() -> dict[str, Any]:
    base = evaluate_source_separation_setup()
    return {
        **base,
        "status": "unavailable_safe",
        "smoke_test_passed": False,
        "smoke_tests_performed": [],
        "generated_stem_paths": [],
        "no_fake_stems": True,
        "smoke_test_notes": [
            "Smoke tests validate witness-only source separation semantics.",
            "No audio processing, no stem separation, and no model downloads were performed.",
            "Stem outputs remain weak evidence and not ground truth.",
        ],
    }


def write_smoke_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = run_source_separation_smoke_tests()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source_separation_setup_status.json"
    md_path = output_dir / "source_separation_setup_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Separation Smoke Test Status",
        "",
        f"- status: `{payload['status']}`",
        "- smoke_test_passed: `False`",
        f"- demucs_available: `{payload['demucs_available']}`",
        "- source_separation_performed: `False`",
        "- stems_generated: `False`",
        "- downloads_performed: `False`",
        "- model_training_has_occurred: `False`",
        f"- witness_policy: `{payload['witness_policy']}`",
        "- training_use_allowed: `false_by_default`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run source separation witness smoke scaffolds without separating stems.")
    parser.add_argument("--output-dir", default="reports/model_integrations")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_smoke_report(output_dir)
    print(f"SOURCE_SEPARATION_SMOKE_JSON={json_path.as_posix()}")
    print(f"SOURCE_SEPARATION_SMOKE_MD={md_path.as_posix()}")
    print(f"SMOKE_TEST_PASSED={payload['smoke_test_passed']}")
    print("DEMUCS_AVAILABLE=False")
    print("SOURCE_SEPARATION_PERFORMED=False")
    print("STEMS_GENERATED=False")
    print("DOWNLOADS_PERFORMED=False")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    print("WITNESS_POLICY=weak_evidence_not_truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
