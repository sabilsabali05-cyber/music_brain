from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_model_ensemble.backends.musicbert_adapter import MusicBertAdapter


def _candidate_paths(source_dir: Path) -> list[Path]:
    candidates_dir = source_dir / "generated_candidates"
    if not candidates_dir.exists():
        return []
    return sorted(candidates_dir.glob("*.ir.json"))


def evaluate_symbolic_candidates_musicbert(source_dir: Path) -> dict[str, Any]:
    adapter = MusicBertAdapter()
    availability = adapter.check_available()
    candidates = _candidate_paths(source_dir)
    candidate_rows = [
        {
            "candidate_id": path.stem.replace(".ir", ""),
            "candidate_ir_json": path.relative_to(ROOT_DIR).as_posix() if path.is_relative_to(ROOT_DIR) else path.name,
            "evaluation_status": "pending_real_musicbert_evaluation",
        }
        for path in candidates
    ]
    if availability.status != "available":
        return {
            "status": "unavailable",
            "musicbert_available": False,
            "no_fake_evaluation": True,
            "unavailable_reason": availability.reason,
            "candidate_count": len(candidate_rows),
            "candidates": candidate_rows,
            "scores_generated": False,
            "model_training_has_occurred": False,
            "limitations": [
                "No evaluation scores are generated while MusicBERT is unavailable.",
                "No training is performed.",
            ],
        }
    return {
        "status": "ok",
        "musicbert_available": True,
        "no_fake_evaluation": True,
        "unavailable_reason": "",
        "candidate_count": len(candidate_rows),
        "candidates": candidate_rows,
        "scores_generated": False,
        "model_training_has_occurred": False,
        "limitations": [
            "This scaffold does not generate real scores yet.",
            "No training is performed.",
        ],
    }


def write_evaluation_report(output_dir: Path, source_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = evaluate_symbolic_candidates_musicbert(source_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "musicbert_candidate_evaluation_report.json"
    md_path = output_dir / "musicbert_candidate_evaluation_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# MusicBERT Candidate Evaluation Report",
        "",
        f"- status: `{payload['status']}`",
        f"- musicbert_available: `{payload['musicbert_available']}`",
        f"- no_fake_evaluation: `{payload['no_fake_evaluation']}`",
        f"- scores_generated: `{payload['scores_generated']}`",
        f"- candidate_count: `{payload['candidate_count']}`",
        f"- unavailable_reason: `{payload['unavailable_reason']}`",
        "- model_training_has_occurred: `False`",
    ]
    if payload["candidates"]:
        lines.extend(["", "## Pending Candidates"])
        for row in payload["candidates"]:
            lines.append(f"- `{row['candidate_id']}` -> `{row['candidate_ir_json']}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate symbolic ensemble candidates via MusicBERT when available.")
    parser.add_argument("--output-dir", default="reports/symbolic_backends")
    parser.add_argument("--source-dir", default="outputs/symbolic_ensemble_v1")
    args = parser.parse_args()
    output_dir = ROOT_DIR / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    source_dir = ROOT_DIR / args.source_dir if not Path(args.source_dir).is_absolute() else Path(args.source_dir)
    json_path, md_path, payload = write_evaluation_report(output_dir, source_dir)
    print(f"MUSICBERT_EVAL_REPORT_JSON={json_path.as_posix()}")
    print(f"MUSICBERT_EVAL_REPORT_MD={md_path.as_posix()}")
    print(f"MUSICBERT_AVAILABLE={payload['musicbert_available']}")
    print(f"STATUS={payload['status']}")
    print(f"SCORES_GENERATED={payload['scores_generated']}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
