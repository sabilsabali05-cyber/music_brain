from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_model_ensemble.backends.musicbert_adapter import MusicBertAdapter
from scripts.check_musicbert_setup import evaluate_musicbert_setup


def _write_smoke_report(output_dir: Path, payload: dict) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "musicbert_setup_status.json"
    md_path = output_dir / "musicbert_setup_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# MusicBERT Smoke Test Status",
        "",
        f"- status: `{payload['status']}`",
        f"- musicbert_configured: `{payload['musicbert_configured']}`",
        f"- musicbert_available: `{payload['musicbert_available']}`",
        f"- smoke_test_passed: `{payload['smoke_test_passed']}`",
        f"- unavailable_reason: `{payload['unavailable_reason']}`",
        f"- next_setup_step: {payload['next_setup_step']}",
        "- model_training_has_occurred: `False`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def run_musicbert_smoke_test() -> dict:
    base = evaluate_musicbert_setup()
    unavailable_reason = str(base.get("unavailable_reason", "disabled_or_missing_local_config"))
    if unavailable_reason in {"disabled_or_missing_local_config", "disabled_in_local_config"}:
        return {
            **base,
            "status": "unavailable",
            "musicbert_available": False,
            "smoke_test_passed": False,
            "unavailable_reason": "disabled_or_missing_local_config",
            "next_setup_step": (
                "Enable MusicBERT and set repo_path/model_path/tokenizer_path in "
                "config/model_integrations/model_integrations.local.json."
            ),
            "model_training_has_occurred": False,
            "smoke_test_notes": [
                "Smoke test skipped because local config is disabled or missing.",
                "No weights downloaded and no training performed.",
            ],
        }

    adapter = MusicBertAdapter()
    passed, reason = adapter.run_smoke_test()
    if not passed:
        return {
            **base,
            "status": "unavailable",
            "musicbert_available": False,
            "smoke_test_passed": False,
            "unavailable_reason": reason,
            "next_setup_step": base["next_setup_step"],
            "model_training_has_occurred": False,
            "smoke_test_notes": [
                "Smoke test failed preconditions or dependency probe.",
                "No weights downloaded and no training performed.",
            ],
        }
    return {
        **base,
        "status": "ok",
        "musicbert_available": True,
        "smoke_test_passed": True,
        "unavailable_reason": "",
        "next_setup_step": "MusicBERT smoke test passed. Keep evaluation hooks disabled until full integration is implemented.",
        "model_training_has_occurred": False,
        "smoke_test_notes": [
            "Minimal runtime dependency import smoke probe passed.",
            "No evaluation/ranking inference was executed.",
            "No weights downloaded and no training performed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal MusicBERT smoke test without evaluation.")
    parser.add_argument("--output-dir", default="reports/model_integrations")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    payload = run_musicbert_smoke_test()
    json_path, md_path = _write_smoke_report(output_dir, payload)
    print(f"MUSICBERT_SMOKE_JSON={json_path.as_posix()}")
    print(f"MUSICBERT_SMOKE_MD={md_path.as_posix()}")
    print(f"MUSICBERT_CONFIGURED={payload['musicbert_configured']}")
    print(f"MUSICBERT_AVAILABLE={payload['musicbert_available']}")
    print(f"SMOKE_TEST_PASSED={payload['smoke_test_passed']}")
    print(f"UNAVAILABLE_REASON={payload['unavailable_reason'] or 'none'}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
