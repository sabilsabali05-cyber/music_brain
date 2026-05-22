from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from scripts.feature_dataset_common import (
        default_feature_dir,
        get_active_paths,
        load_json,
        performance_metadata,
    )
except ModuleNotFoundError:  # pragma: no cover
    from feature_dataset_common import (  # type: ignore
        default_feature_dir,
        get_active_paths,
        load_json,
        performance_metadata,
    )


def validate_feature_pack(performance_manifest_path: Path, *, output_dir: Path | None = None) -> dict[str, object]:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, _, _ = get_active_paths(performance_manifest)
    performance_id, _, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    feature_dir = output_dir or default_feature_dir(performance_id, segment_run_id)

    required_files = {
        "feature_pack_manifest": feature_dir / "feature_pack_manifest.json",
        "rhythm_features": feature_dir / "rhythm_features.json",
        "harmony_features": feature_dir / "harmony_features.json",
        "tags": feature_dir / "tags.json",
        "ai_training_records": feature_dir / "ai_training_records.jsonl",
        "feature_summary": feature_dir / "feature_summary.md",
    }
    missing = [name for name, path in required_files.items() if not path.exists()]
    if missing:
        return {
            "status": "failed",
            "performance_id": performance_id,
            "feature_pack_dir": feature_dir.resolve().as_posix(),
            "missing_files": missing,
        }

    rhythm = load_json(required_files["rhythm_features"])
    harmony = load_json(required_files["harmony_features"])
    tags = load_json(required_files["tags"])
    ai_lines = [line for line in required_files["ai_training_records"].read_text(encoding="utf-8").splitlines() if line.strip()]
    ai_training_records: list[dict[str, object]] = []
    jsonl_parse_errors = 0
    for line in ai_lines:
        try:
            parsed = json.loads(line)
        except Exception:  # noqa: BLE001
            jsonl_parse_errors += 1
            continue
        if isinstance(parsed, dict):
            ai_training_records.append(parsed)
        else:
            jsonl_parse_errors += 1

    rhythm_records = rhythm.get("records", [])
    harmony_records = harmony.get("records", [])
    tag_records = tags.get("tags", [])
    has_grouped_tags = "grouped_tags" in tags
    has_top_unique_tags = "top_unique_tags" in tags
    grouped_tags = tags.get("grouped_tags", [])
    top_unique_tags = tags.get("top_unique_tags", [])
    rhythm_motifs = rhythm.get("rhythm_motifs", {})
    rhythm_motif_groups = rhythm.get("rhythm_motif_groups", [])
    rhythm_pattern_index = rhythm.get("rhythm_pattern_index", {})
    chord_movement_summary = harmony.get("chord_movement_summary", {})
    harmony_pattern_index = harmony.get("harmony_pattern_index", {})

    warnings: list[str] = []
    if not isinstance(rhythm_records, list) or len(rhythm_records) == 0:
        warnings.append("rhythm records are empty")
    if not isinstance(harmony_records, list) or len(harmony_records) == 0:
        warnings.append("harmony records are empty")
    if not isinstance(tag_records, list):
        warnings.append("tags payload malformed")
    if not has_grouped_tags or not isinstance(grouped_tags, list):
        warnings.append("grouped_tags missing or malformed")
    if not has_top_unique_tags or not isinstance(top_unique_tags, list):
        warnings.append("top_unique_tags missing or malformed")
    if not isinstance(rhythm_motifs, dict):
        warnings.append("rhythm_motifs section missing or malformed")
    if not isinstance(rhythm_motif_groups, list):
        warnings.append("rhythm_motif_groups missing or malformed")
    if not isinstance(rhythm_pattern_index, dict):
        warnings.append("rhythm_pattern_index missing or malformed")
    elif "rhythm_family_counts" not in rhythm_pattern_index or not isinstance(rhythm_pattern_index.get("rhythm_family_counts"), dict):
        warnings.append("rhythm_pattern_index missing rhythm_family_counts")
    elif not all(
        key in rhythm_pattern_index and isinstance(rhythm_pattern_index.get(key), dict)
        for key in ["strong_rhythm_family_counts", "moderate_rhythm_family_counts", "weak_rhythm_family_counts"]
    ):
        warnings.append("rhythm_pattern_index missing strong/moderate/weak family counts")
    if not isinstance(chord_movement_summary, dict):
        warnings.append("chord_movement_summary missing or malformed")
    if not isinstance(harmony_pattern_index, dict):
        warnings.append("harmony_pattern_index missing or malformed")
    if isinstance(rhythm_motif_groups, list):
        missing_matches = 0
        for group in rhythm_motif_groups:
            if not isinstance(group, dict):
                continue
            if "rhythm_lexicon_matches" not in group:
                missing_matches += 1
        if missing_matches:
            warnings.append(f"rhythm motif groups missing rhythm_lexicon_matches: {missing_matches}")
    if jsonl_parse_errors:
        warnings.append(f"ai training jsonl parse errors: {jsonl_parse_errors}")

    confidence_issues = 0
    for collection in [rhythm_records, harmony_records, tag_records, ai_training_records]:
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, dict):
                continue
            if "confidence" not in item:
                continue
            try:
                value = float(item.get("confidence", 0.0) or 0.0)
            except Exception:  # noqa: BLE001
                confidence_issues += 1
                continue
            if value < 0.0 or value > 1.0:
                confidence_issues += 1
    if confidence_issues:
        warnings.append(f"confidence out of range entries: {confidence_issues}")

    old_json_path = feature_dir / "ai_training_records.json"
    if old_json_path.exists():
        warnings.append("legacy ai_training_records.json exists; expected JSONL contract only")

    invalid_tag_entries = 0
    if isinstance(tag_records, list):
        for tag in tag_records:
            if not isinstance(tag, dict):
                invalid_tag_entries += 1
                continue
            if "confidence" not in tag or "evidence" not in tag:
                invalid_tag_entries += 1
                continue
            for required in ["rhythm_concepts", "philosophy_sources", "detection_targets"]:
                if required not in tag:
                    invalid_tag_entries += 1
                    break
            tag_name = str(tag.get("tag", ""))
            if tag_name.startswith("rhythm_family_"):
                if (
                    "matched_pattern_id" not in tag
                    or "matched_family" not in tag
                    or "match_strength" not in tag
                    or "ambiguity_score" not in tag
                ):
                    invalid_tag_entries += 1
    if invalid_tag_entries:
        warnings.append(f"tag entries missing confidence/evidence: {invalid_tag_entries}")

    invalid_time_ranges = 0
    def _check_time_range(item: dict[str, object]) -> None:
        nonlocal invalid_time_ranges
        start = item.get("start_seconds")
        end = item.get("end_seconds")
        if start is None or end is None:
            return
        try:
            if float(end) < float(start):
                invalid_time_ranges += 1
        except Exception:  # noqa: BLE001
            invalid_time_ranges += 1

    if isinstance(tag_records, list):
        for item in tag_records:
            if isinstance(item, dict):
                _check_time_range(item)
    for item in ai_training_records:
        _check_time_range(item)
        required_ai_fields = ["record_id", "performance_id", "granularity", "start_seconds", "end_seconds", "limitations"]
        for field in required_ai_fields:
            if field not in item:
                warnings.append(f"ai record missing field: {field}")
                break
        if "motif_group_refs" in item and not isinstance(item.get("motif_group_refs"), list):
            warnings.append("ai record motif_group_refs must be a list")
        if "harmony_pattern_index_refs" in item and not isinstance(item.get("harmony_pattern_index_refs"), list):
            warnings.append("ai record harmony_pattern_index_refs must be a list")
    if invalid_time_ranges:
        warnings.append(f"invalid time ranges: {invalid_time_ranges}")

    ai_granularity: dict[str, int] = {}
    for record in ai_training_records:
        granularity = str(record.get("granularity", "unknown"))
        ai_granularity[granularity] = ai_granularity.get(granularity, 0) + 1

    windows_total = len(rhythm_records) if isinstance(rhythm_records, list) else 0
    if windows_total > 3 and len(ai_training_records) <= 1:
        warnings.append("expected multiple AI records when segment/window records exist")
    required_granularities = {"performance", "segment", "window", "rhythm_region", "chord_region"}
    missing_granularities = sorted(required_granularities - set(ai_granularity.keys()))
    if missing_granularities:
        warnings.append(f"missing AI granularities: {', '.join(missing_granularities)}")

    summary_text = required_files["feature_summary"].read_text(encoding="utf-8")
    required_summary_tokens = [
        "rhythm_record_count_by_granularity",
        "harmony_record_count_by_granularity",
        "ai_record_count_by_granularity",
        "Top Unique Tags",
        "Rhythm Motif Candidates",
        "Top Rhythm Motif Groups",
        "Harmony Pattern Index",
        "Rhythm Philosophy Interpretation",
        "Standard Rhythm Family Matches",
        "Rhythm Family Classification Quality",
    ]
    for token in required_summary_tokens:
        if token not in summary_text:
            warnings.append(f"feature_summary.md missing token: {token}")
    motif_count = int(rhythm_motifs.get("motif_count", 0) or 0) if isinstance(rhythm_motifs, dict) else 0
    if "Ghost_Town" in performance_id and motif_count <= 1:
        warnings.append("motif count is suspiciously low for Ghost Town; inspect quantization/motif mining thresholds")

    status = "success" if not missing and not warnings else "failed"
    return {
        "status": status,
        "performance_id": performance_id,
        "feature_pack_dir": feature_dir.resolve().as_posix(),
        "rhythm_record_count": len(rhythm_records) if isinstance(rhythm_records, list) else 0,
        "harmony_record_count": len(harmony_records) if isinstance(harmony_records, list) else 0,
        "tag_count": len(tag_records) if isinstance(tag_records, list) else 0,
        "ai_training_record_count": len(ai_training_records),
        "ai_record_count_by_granularity": ai_granularity,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate extracted feature pack outputs for one performance.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for feature files")
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    summary = validate_feature_pack(Path(args.performance_manifest), output_dir=output_dir)
    print(f"FEATURE_PACK_DIR={summary.get('feature_pack_dir')}")
    print(f"VALIDATION_STATUS={summary.get('status')}")
    print(f"RHYTHM_RECORD_COUNT={summary.get('rhythm_record_count')}")
    print(f"HARMONY_RECORD_COUNT={summary.get('harmony_record_count')}")
    print(f"TAG_COUNT={summary.get('tag_count')}")
    print(f"AI_TRAINING_RECORD_COUNT={summary.get('ai_training_record_count')}")
    for warning in summary.get("warnings", []):
        print(f"VALIDATION_WARNING={warning}")
    if summary.get("status") != "success":
        raise SystemExit("Feature pack validation failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
