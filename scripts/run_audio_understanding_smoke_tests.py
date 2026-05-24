from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.check_audio_understanding_setup import evaluate_audio_understanding_setup


def run_audio_understanding_smoke_tests() -> dict[str, Any]:
    base = evaluate_audio_understanding_setup()
    status = "ok" if base["smoke_tests_passed"] else "unavailable"
    return {
        **base,
        "status": status,
        "smoke_test_notes": [
            "Smoke tests only run dependency probes when models are explicitly enabled in local config.",
            "No audio processing, no embedding generation, no downloads, and no training are performed.",
        ],
    }


def write_smoke_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = run_audio_understanding_smoke_tests()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "audio_understanding_setup_status.json"
    md_path = output_dir / "audio_understanding_setup_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Audio Understanding Smoke Test Status",
        "",
        f"- status: `{payload['status']}`",
        f"- smoke_tests_passed: `{payload['smoke_tests_passed']}`",
        f"- essentia_available: `{payload['essentia_available']}`",
        f"- muq_available: `{payload['muq_available']}`",
        f"- mert_available: `{payload['mert_available']}`",
        "- model_training_has_occurred: `False`",
        "- audio_processing_performed: `False`",
        "- embeddings_generated: `False`",
        "- downloads_performed: `False`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run audio-understanding smoke probes without audio processing.")
    parser.add_argument("--output-dir", default="reports/model_integrations")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_smoke_report(output_dir)
    print(f"AUDIO_UNDERSTANDING_SMOKE_JSON={json_path.as_posix()}")
    print(f"AUDIO_UNDERSTANDING_SMOKE_MD={md_path.as_posix()}")
    print(f"SMOKE_TESTS_PASSED={payload['smoke_tests_passed']}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
