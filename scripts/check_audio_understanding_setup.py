from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.audio_understanding.essentia_adapter import EssentiaAdapter
from features.audio_understanding.mert_adapter import MERTAdapter
from features.audio_understanding.muq_adapter import MuQAdapter

REPORT_DIR = ROOT_DIR / "reports" / "model_integrations"


def evaluate_audio_understanding_setup() -> dict[str, Any]:
    essentia = EssentiaAdapter().availability()
    muq = MuQAdapter().availability()
    mert = MERTAdapter().availability()
    smoke_tests_passed = bool(essentia["available"] and muq["available"] and mert["available"])
    return {
        "status": "ok",
        "essentia_configured": bool(essentia["configured"]),
        "essentia_available": bool(essentia["available"]),
        "muq_configured": bool(muq["configured"]),
        "muq_available": bool(muq["available"]),
        "mert_configured": bool(mert["configured"]),
        "mert_available": bool(mert["available"]),
        "smoke_tests_passed": smoke_tests_passed,
        "model_training_has_occurred": False,
        "audio_processing_performed": False,
        "embeddings_generated": False,
        "downloads_performed": False,
        "details": {
            "essentia": essentia,
            "muq": muq,
            "mert": mert,
        },
        "limitations": [
            "Checker is configuration-only and import-probe-only; no audio processing is performed.",
            "No model downloads and no model training are performed.",
            "All adapters are disabled by default until explicitly enabled in local config.",
        ],
    }


def write_audio_understanding_setup_report(output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = evaluate_audio_understanding_setup()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "audio_understanding_setup_status.json"
    md_path = output_dir / "audio_understanding_setup_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Audio Understanding Setup Status",
        "",
        f"- essentia_configured: `{payload['essentia_configured']}`",
        f"- essentia_available: `{payload['essentia_available']}`",
        f"- muq_configured: `{payload['muq_configured']}`",
        f"- muq_available: `{payload['muq_available']}`",
        f"- mert_configured: `{payload['mert_configured']}`",
        f"- mert_available: `{payload['mert_available']}`",
        f"- smoke_tests_passed: `{payload['smoke_tests_passed']}`",
        "- model_training_has_occurred: `False`",
        "- audio_processing_performed: `False`",
        "- embeddings_generated: `False`",
        "- downloads_performed: `False`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Check audio-understanding local setup readiness without heavy processing.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    json_path, md_path, payload = write_audio_understanding_setup_report(output_dir)
    print(f"AUDIO_UNDERSTANDING_SETUP_JSON={json_path.as_posix()}")
    print(f"AUDIO_UNDERSTANDING_SETUP_MD={md_path.as_posix()}")
    print(f"ESSENTIA_CONFIGURED={payload['essentia_configured']}")
    print(f"ESSENTIA_AVAILABLE={payload['essentia_available']}")
    print(f"MUQ_CONFIGURED={payload['muq_configured']}")
    print(f"MUQ_AVAILABLE={payload['muq_available']}")
    print(f"MERT_CONFIGURED={payload['mert_configured']}")
    print(f"MERT_AVAILABLE={payload['mert_available']}")
    print(f"SMOKE_TESTS_PASSED={payload['smoke_tests_passed']}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
