from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_model_ensemble.backends.text2midi_adapter import Text2MidiAdapter
from scripts.check_text2midi_setup import evaluate_text2midi_setup


def _write_smoke_report(output_dir: Path, payload: dict) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "text2midi_setup_status.json"
    md_path = output_dir / "text2midi_setup_status.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Text2MIDI Smoke Test Status",
        "",
        f"- status: `{payload['status']}`",
        f"- text2midi_configured: `{payload['text2midi_configured']}`",
        f"- text2midi_available: `{payload['text2midi_available']}`",
        f"- smoke_test_passed: `{payload['smoke_test_passed']}`",
        f"- unavailable_reason: `{payload['unavailable_reason']}`",
        f"- next_setup_step: {payload['next_setup_step']}",
        "- model_training_has_occurred: `False`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def run_text2midi_smoke_test() -> dict:
    base = evaluate_text2midi_setup()
    unavailable_reason = str(base.get("unavailable_reason", "disabled_or_missing_local_config"))
    if unavailable_reason in {"disabled_or_missing_local_config", "disabled_in_local_config"}:
        return {
            **base,
            "status": "unavailable",
            "text2midi_available": False,
            "smoke_test_passed": False,
            "unavailable_reason": "disabled_or_missing_local_config",
            "next_setup_step": (
                "Enable Text2MIDI and set repo_path/model_path in "
                "config/model_integrations/model_integrations.local.json."
            ),
            "model_training_has_occurred": False,
            "smoke_test_notes": [
                "Smoke test skipped because local config is disabled or missing.",
                "No weights downloaded and no training performed.",
            ],
        }

    adapter = Text2MidiAdapter()
    passed, reason = adapter.run_smoke_test()
    if not passed:
        return {
            **base,
            "status": "unavailable",
            "text2midi_available": False,
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
        "text2midi_available": True,
        "smoke_test_passed": True,
        "unavailable_reason": "",
        "next_setup_step": (
            "Text2MIDI smoke test passed. Keep prompt-sketch generation hooks unavailable "
            "until full inference wiring is complete."
        ),
        "model_training_has_occurred": False,
        "smoke_test_notes": [
            "Minimal runtime dependency import smoke probe passed.",
            "No MIDI generation was executed by this smoke test.",
            "No weights downloaded and no training performed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal Text2MIDI smoke test without generation.")
    parser.add_argument("--output-dir", default="reports/model_integrations")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir
    payload = run_text2midi_smoke_test()
    json_path, md_path = _write_smoke_report(output_dir, payload)
    print(f"TEXT2MIDI_SMOKE_JSON={json_path.as_posix()}")
    print(f"TEXT2MIDI_SMOKE_MD={md_path.as_posix()}")
    print(f"TEXT2MIDI_CONFIGURED={payload['text2midi_configured']}")
    print(f"TEXT2MIDI_AVAILABLE={payload['text2midi_available']}")
    print(f"SMOKE_TEST_PASSED={payload['smoke_test_passed']}")
    print(f"UNAVAILABLE_REASON={payload['unavailable_reason'] or 'none'}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
