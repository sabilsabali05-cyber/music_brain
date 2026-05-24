from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.taste_learning.composition_ranker import result_to_dict, train_ranker  # noqa: E402


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _is_valid_generated_outcome_row(row: dict) -> bool:
    if not str(row.get("generation_id", "")).strip():
        return False
    if str(row.get("authorization_status", "")).strip().lower() not in {"authorized", "public_domain", "self_owned"}:
        return False
    if not bool(row.get("source_authorized_for_learning", False)):
        return False
    if "result_available" in row and not bool(row.get("result_available", False)):
        return False
    return True


def main() -> int:
    feedback_path = ROOT_DIR / "datasets" / "taste_learning" / "taste_feedback.jsonl"
    beat_battle_feedback_path = ROOT_DIR / "datasets" / "taste_learning" / "beat_battle_site_feedback.jsonl"
    model_path = ROOT_DIR / "artifacts" / "taste_learning" / "composition_ranker" / "model.json"
    report_json = ROOT_DIR / "reports" / "taste_learning" / "composition_ranker_training_report.json"
    report_md = ROOT_DIR / "reports" / "taste_learning" / "composition_ranker_training_report.md"
    combined_rows = [row for row in _load_jsonl(feedback_path) if _is_valid_generated_outcome_row(row)]
    combined_rows.extend(row for row in _load_jsonl(beat_battle_feedback_path) if _is_valid_generated_outcome_row(row))
    with tempfile.TemporaryDirectory() as tmpdir:
        combined_path = Path(tmpdir) / "combined_feedback.jsonl"
        with combined_path.open("w", encoding="utf-8") as handle:
            for row in combined_rows:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")
        result = train_ranker(combined_path, model_path)
    payload = result_to_dict(result)
    payload["model_path"] = _repo_rel(Path(payload["model_path"]))
    payload["combined_rows_count"] = len(combined_rows)
    payload["beat_battle_rows_considered"] = len([row for row in combined_rows if str(row.get("generation_id", "")).startswith("beat_battle_")])
    ratio_keys = {
        "golden_section_alignment",
        "phrase_ratio_score",
        "rhythm_ratio_score",
        "interval_ratio_score",
        "density_ratio_score",
        "ratio_musicality_score",
    }
    payload["ratio_feature_rows_count"] = sum(1 for row in combined_rows if any(key in row for key in ratio_keys))
    payload["ratio_feature_coverage"] = (
        round(payload["ratio_feature_rows_count"] / len(combined_rows), 6) if combined_rows else 0.0
    )
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_md.write_text(
        "\n".join(
            [
                "# Composition Taste Ranker Training Report",
                "",
                f"- training_examples_count: `{payload['training_examples_count']}`",
                f"- authorized_examples_count: `{payload['authorized_examples_count']}`",
                f"- blocked_examples_count: `{payload['blocked_examples_count']}`",
                f"- trained_ranker_used: `{str(payload['trained_ranker_used']).lower()}`",
                f"- heuristic_ranker_used: `{str(payload['heuristic_ranker_used']).lower()}`",
                f"- train_status: `{payload['train_status']}`",
                f"- model_path: `{payload['model_path']}`",
                f"- ratio_feature_rows_count: `{payload['ratio_feature_rows_count']}`",
                f"- ratio_feature_coverage: `{payload['ratio_feature_coverage']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"TRAINING_REPORT_JSON={report_json.as_posix()}")
    print(f"TRAINING_REPORT_MD={report_md.as_posix()}")
    print(f"TRAINING_EXAMPLES_COUNT={payload['training_examples_count']}")
    print(f"TRAINED_RANKER_USED={str(payload['trained_ranker_used']).lower()}")
    print(f"HEURISTIC_RANKER_USED={str(payload['heuristic_ranker_used']).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
