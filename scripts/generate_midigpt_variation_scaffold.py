from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_model_ensemble.backends.midigpt_adapter import MidiGptAdapter

DEFAULT_VARIATION_TYPES = [
    "drum_variation",
    "groove_variation",
    "density_variation",
    "multitrack_infill",
]


def _candidate_paths(source_dir: Path) -> list[Path]:
    candidates_dir = source_dir / "generated_candidates"
    if not candidates_dir.exists():
        return []
    return sorted(candidates_dir.glob("*.ir.json"))


def generate_midigpt_variation_scaffold(
    source_dir: Path,
    variation_types: list[str] | None = None,
) -> dict[str, Any]:
    adapter = MidiGptAdapter()
    availability = adapter.check_available()
    requested_variation_types = variation_types or list(DEFAULT_VARIATION_TYPES)
    candidates = _candidate_paths(source_dir)
    candidate_rows = [
        {
            "candidate_id": path.stem.replace(".ir", ""),
            "candidate_ir_json": path.relative_to(ROOT_DIR).as_posix() if path.is_relative_to(ROOT_DIR) else path.name,
            "status": "pending_midigpt_variation_generation",
        }
        for path in candidates
    ]

    if availability.status != "available":
        return {
            "status": "unavailable",
            "midigpt_available": False,
            "unavailable_reason": availability.reason,
            "requested_variation_types": requested_variation_types,
            "candidate_count": len(candidate_rows),
            "candidates": candidate_rows,
            "variations_generated": False,
            "no_fake_generation": True,
            "generated_midi_outputs": [],
            "scores_generated": False,
            "model_training_has_occurred": False,
            "limitations": [
                "No fake MIDI output is generated when MIDI-GPT is unavailable.",
                "No fake ranking/evaluation scores are produced.",
                "No training is performed.",
            ],
        }

    return {
        "status": "available_but_not_implemented",
        "midigpt_available": True,
        "unavailable_reason": "",
        "requested_variation_types": requested_variation_types,
        "candidate_count": len(candidate_rows),
        "candidates": candidate_rows,
        "variations_generated": False,
        "no_fake_generation": True,
        "generated_midi_outputs": [],
        "scores_generated": False,
        "model_training_has_occurred": False,
        "limitations": [
            "Scaffold only: real MIDI-GPT generation wiring is intentionally not implemented.",
            "No fake MIDI output is produced.",
            "No training is performed.",
        ],
    }


def write_variation_report(output_dir: Path, source_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = generate_midigpt_variation_scaffold(source_dir=source_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "midigpt_variation_report.json"
    md_path = output_dir / "midigpt_variation_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# MIDI-GPT Variation Scaffold Report",
        "",
        f"- status: `{payload['status']}`",
        f"- midigpt_available: `{payload['midigpt_available']}`",
        f"- no_fake_generation: `{payload['no_fake_generation']}`",
        f"- variations_generated: `{payload['variations_generated']}`",
        f"- candidate_count: `{payload['candidate_count']}`",
        f"- unavailable_reason: `{payload['unavailable_reason']}`",
        "- model_training_has_occurred: `False`",
        "",
        "## Requested Variation Types",
    ]
    for variation_type in payload["requested_variation_types"]:
        lines.append(f"- `{variation_type}`")
    if payload["candidates"]:
        lines.extend(["", "## Candidate Inputs"])
        for row in payload["candidates"]:
            lines.append(f"- `{row['candidate_id']}` -> `{row['candidate_ir_json']}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a MIDI-GPT variation scaffold report without fake outputs.")
    parser.add_argument("--output-dir", default="reports/symbolic_backends")
    parser.add_argument("--source-dir", default="outputs/symbolic_ensemble_v1")
    args = parser.parse_args()
    output_dir = ROOT_DIR / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    source_dir = ROOT_DIR / args.source_dir if not Path(args.source_dir).is_absolute() else Path(args.source_dir)
    json_path, md_path, payload = write_variation_report(output_dir, source_dir)
    print(f"MIDIGPT_VARIATION_REPORT_JSON={json_path.as_posix()}")
    print(f"MIDIGPT_VARIATION_REPORT_MD={md_path.as_posix()}")
    print(f"MIDIGPT_AVAILABLE={payload['midigpt_available']}")
    print(f"STATUS={payload['status']}")
    print(f"VARIATIONS_GENERATED={payload['variations_generated']}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
