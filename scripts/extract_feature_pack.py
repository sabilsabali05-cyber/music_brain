from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from scripts.build_ai_training_records import build_ai_training_records
    from scripts.extract_harmony_features import extract_harmony_features
    from scripts.extract_rhythm_features import extract_rhythm_features
    from scripts.feature_dataset_common import (
        default_feature_dir,
        get_active_paths,
        load_json,
        now_iso,
        performance_metadata,
        save_json,
    )
    from scripts.tag_performance_features import tag_performance_features
except ModuleNotFoundError:  # pragma: no cover
    from build_ai_training_records import build_ai_training_records  # type: ignore
    from extract_harmony_features import extract_harmony_features  # type: ignore
    from extract_rhythm_features import extract_rhythm_features  # type: ignore
    from feature_dataset_common import (  # type: ignore
        default_feature_dir,
        get_active_paths,
        load_json,
        now_iso,
        performance_metadata,
        save_json,
    )
    from tag_performance_features import tag_performance_features  # type: ignore


def extract_feature_pack(performance_manifest_path: Path, *, output_dir: Path | None = None) -> Path:
    performance_manifest = load_json(performance_manifest_path)
    segments_manifest_path, analysis_path, merged_midi_path = get_active_paths(performance_manifest)
    performance_id, _, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    target_dir = output_dir or default_feature_dir(performance_id, segment_run_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    rhythm_path = extract_rhythm_features(performance_manifest_path, output_dir=target_dir)
    harmony_path = extract_harmony_features(performance_manifest_path, output_dir=target_dir)
    tags_path = tag_performance_features(performance_manifest_path, output_dir=target_dir)
    ai_records_path = build_ai_training_records(performance_manifest_path, output_dir=target_dir)

    rhythm_payload = load_json(rhythm_path)
    harmony_payload = load_json(harmony_path)
    tags_payload = load_json(tags_path)
    ai_record_count = 0
    ai_records_by_granularity: dict[str, int] = {}
    if ai_records_path.exists():
        ai_records = []
        for line in ai_records_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ai_records.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
        ai_record_count = len(ai_records)
        for record in ai_records:
            if not isinstance(record, dict):
                continue
            granularity = str(record.get("granularity", "unknown"))
            ai_records_by_granularity[granularity] = ai_records_by_granularity.get(granularity, 0) + 1

    rhythm_by_granularity = rhythm_payload.get("summary", {}).get("record_count_by_granularity", {})
    if not isinstance(rhythm_by_granularity, dict):
        rhythm_by_granularity = {}
    harmony_by_granularity = harmony_payload.get("summary", {}).get("record_count_by_granularity", {})
    if not isinstance(harmony_by_granularity, dict):
        harmony_by_granularity = {}

    tags = tags_payload.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    grouped_tags = tags_payload.get("grouped_tags", [])
    if not isinstance(grouped_tags, list):
        grouped_tags = []
    top_unique_tags = tags_payload.get("top_unique_tags", [])
    if not isinstance(top_unique_tags, list):
        top_unique_tags = []
    highest_conf_local = sorted(
        [item for item in tags if isinstance(item, dict)],
        key=lambda item: float(item.get("confidence", 0.0) or 0.0),
        reverse=True,
    )[:10]

    limitations: list[str] = []
    for payload in [rhythm_payload, harmony_payload]:
        values = payload.get("limitations", [])
        if isinstance(values, list):
            limitations.extend(str(item) for item in values)
    unique_limitations = sorted({item for item in limitations if item})

    summary_lines = [
        f"# Feature Summary - {performance_id}",
        "",
        f"- performance_id: `{performance_id}`",
        f"- segment_run_id: `{segment_run_id}`",
        f"- source_duration_seconds: `{performance_manifest.get('duration_seconds')}`",
        f"- source_artifacts:",
        f"  - performance_manifest: `{performance_manifest_path.resolve().as_posix()}`",
        f"  - active_analysis_path: `{analysis_path.resolve().as_posix() if analysis_path else None}`",
        f"  - active_segments_manifest_path: `{segments_manifest_path.resolve().as_posix()}`",
        f"  - active_merged_midi_path: `{merged_midi_path.resolve().as_posix() if merged_midi_path and merged_midi_path.exists() else None}`",
        "",
        f"- rhythm_summary: `{json.dumps(rhythm_payload.get('summary', {}), ensure_ascii=True)}`",
        f"- harmony_summary: `{json.dumps(harmony_payload.get('summary', {}), ensure_ascii=True)}`",
        f"- rhythm_record_count_by_granularity: `{json.dumps(rhythm_by_granularity, ensure_ascii=True)}`",
        f"- harmony_record_count_by_granularity: `{json.dumps(harmony_by_granularity, ensure_ascii=True)}`",
        f"- ai_record_count_by_granularity: `{json.dumps(ai_records_by_granularity, ensure_ascii=True)}`",
        f"- tag_count: `{tags_payload.get('tag_count', 0)}`",
        f"- ai_training_record_count: `{ai_record_count}`",
        "",
        "## Top Unique Tags",
    ]
    if top_unique_tags:
        for item in top_unique_tags:
            if not isinstance(item, dict):
                continue
            summary_lines.append(
                f"- `{item.get('tag')}`: max=`{item.get('confidence_max')}` "
                f"mean=`{item.get('confidence_mean')}` count=`{item.get('count')}` "
                f"example=`{item.get('example_start_seconds')}-{item.get('example_end_seconds')}`"
            )
    else:
        summary_lines.append("- none")
    summary_lines.extend(["", "## Most Frequent Tags"])
    if grouped_tags:
        for item in sorted(
            [value for value in grouped_tags if isinstance(value, dict)],
            key=lambda value: int(value.get("count", 0)),
            reverse=True,
        )[:10]:
            summary_lines.append(f"- `{item.get('tag')}` count=`{item.get('count')}` max=`{item.get('confidence_max')}`")
    else:
        summary_lines.append("- none")

    summary_lines.extend(["", "## Highest Confidence Local Tags"])
    if highest_conf_local:
        for item in highest_conf_local:
            summary_lines.append(
                f"- `{item.get('tag')}` `{item.get('start_seconds')}-{item.get('end_seconds')}` "
                f"granularity=`{item.get('granularity')}` confidence=`{item.get('confidence')}`"
            )
    else:
        summary_lines.append("- none")
    summary_lines.extend(["", "## Limitations"])
    if unique_limitations:
        for limitation in unique_limitations:
            summary_lines.append(f"- {limitation}")
    else:
        summary_lines.append("- none reported")
    summary_lines.extend(
        [
            "",
            "## Top Rhythm Regions By Density",
        ]
    )
    rhythm_records = rhythm_payload.get("records", [])
    rhythm_regions: list[dict[str, object]] = []
    if isinstance(rhythm_records, list):
        for item in rhythm_records:
            if isinstance(item, dict) and str(item.get("granularity", "")) == "rhythm_region":
                rhythm_regions.append(item)
    densest = sorted(
        rhythm_regions,
        key=lambda item: float((item.get("features", {}) or {}).get("note_on_density_per_second", 0.0) or 0.0),
        reverse=True,
    )[:5]
    sparsest = sorted(
        rhythm_regions,
        key=lambda item: float((item.get("features", {}) or {}).get("note_on_density_per_second", 0.0) or 0.0),
    )[:5]
    if densest:
        for item in densest:
            features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
            summary_lines.append(
                f"- dense `{item.get('region_id')}` `{item.get('start_seconds')}-{item.get('end_seconds')}` "
                f"density=`{features.get('note_on_density_per_second')}`"
            )
    else:
        summary_lines.append("- none")
    summary_lines.extend(["", "## Sparsest Rhythm Regions"])
    if sparsest:
        for item in sparsest:
            features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
            summary_lines.append(
                f"- sparse `{item.get('region_id')}` `{item.get('start_seconds')}-{item.get('end_seconds')}` "
                f"density=`{features.get('note_on_density_per_second')}`"
            )
    else:
        summary_lines.append("- none")

    stable_pulse = sorted(
        rhythm_regions,
        key=lambda item: abs(float((item.get("features", {}) or {}).get("syncopation_proxy_score", 0.0) or 0.0)),
    )[:5]
    irregular_pulse = sorted(
        rhythm_regions,
        key=lambda item: float((item.get("features", {}) or {}).get("syncopation_proxy_score", 0.0) or 0.0),
        reverse=True,
    )[:5]
    summary_lines.extend(["", "## Most Stable Pulse Regions"])
    if stable_pulse:
        for item in stable_pulse:
            features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
            summary_lines.append(
                f"- `{item.get('region_id')}` `{item.get('start_seconds')}-{item.get('end_seconds')}` "
                f"syncopation=`{features.get('syncopation_proxy_score')}`"
            )
    else:
        summary_lines.append("- none")
    summary_lines.extend(["", "## Most Irregular Rhythm Regions"])
    if irregular_pulse:
        for item in irregular_pulse:
            features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
            summary_lines.append(
                f"- `{item.get('region_id')}` `{item.get('start_seconds')}-{item.get('end_seconds')}` "
                f"syncopation=`{features.get('syncopation_proxy_score')}`"
            )
    else:
        summary_lines.append("- none")

    harmony_records = harmony_payload.get("records", [])
    chord_regions: list[dict[str, object]] = []
    if isinstance(harmony_records, list):
        for item in harmony_records:
            if isinstance(item, dict) and str(item.get("granularity", "")) == "chord_region":
                chord_regions.append(item)
    top_movement = sorted(
        chord_regions,
        key=lambda item: float((item.get("features", {}) or {}).get("chord_change_count", 0.0) or 0.0),
        reverse=True,
    )[:5]
    summary_lines.extend(["", "## Most Active Chord-Change Regions"])
    if top_movement:
        for item in top_movement:
            features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
            summary_lines.append(
                f"- `{item.get('region_id')}` `{item.get('start_seconds')}-{item.get('end_seconds')}` "
                f"changes=`{features.get('chord_change_count')}` "
                f"stepwise=`{features.get('stepwise_root_motion_score')}` "
                f"chromatic=`{features.get('chromatic_motion_score')}` "
                f"semitone_motion=`{features.get('semitone_motion')}` "
                f"(chromatic semitone steps are a subset of stepwise motion)"
            )
    else:
        summary_lines.append("- none")

    static_harmony = sorted(
        chord_regions,
        key=lambda item: float((item.get("features", {}) or {}).get("chord_change_count", 0.0) or 0.0),
    )[:5]
    summary_lines.extend(["", "## Most Static Harmony Regions"])
    if static_harmony:
        for item in static_harmony:
            features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
            summary_lines.append(
                f"- `{item.get('region_id')}` `{item.get('start_seconds')}-{item.get('end_seconds')}` "
                f"changes=`{features.get('chord_change_count')}` repeated_root=`{features.get('repeated_root')}`"
            )
    else:
        summary_lines.append("- none")

    movement_summary = harmony_payload.get("chord_movement_summary", {})
    repeated_vamps = movement_summary.get("repeated_chord_vamp_candidates", []) if isinstance(movement_summary, dict) else []
    if not isinstance(repeated_vamps, list):
        repeated_vamps = []
    summary_lines.extend(["", "## Repeated/Vamp Candidates"])
    if repeated_vamps:
        for item in repeated_vamps[:5]:
            if not isinstance(item, dict):
                continue
            summary_lines.append(
                f"- `{item.get('region_id')}` `{item.get('start_seconds')}-{item.get('end_seconds')}` "
                f"score=`{item.get('repeated_chord_score')}` confidence=`{item.get('confidence')}`"
            )
    else:
        summary_lines.append("- none")

    motifs_payload = rhythm_payload.get("rhythm_motifs", {})
    motifs = motifs_payload.get("motifs", []) if isinstance(motifs_payload, dict) else []
    if not isinstance(motifs, list):
        motifs = []
    summary_lines.extend(["", "## Rhythm Motif Candidates"])
    if motifs:
        for item in motifs[:10]:
            if not isinstance(item, dict):
                continue
            summary_lines.append(
                f"- `{item.get('motif_id')}` repeat_count=`{item.get('repeat_count')}` "
                f"region=`{item.get('region_id')}` window=`{item.get('window_id')}` confidence=`{item.get('confidence')}`"
            )
    else:
        summary_lines.append("- none")

    summary_lines.extend(
        [
            "",
            "## Recommended Next Analysis Steps",
            "- Compare feature pack stability across additional completed performances.",
            "- Add segment-level and phrase-region level AI training records.",
            "- Calibrate threshold heuristics with human review labels.",
        ]
    )
    feature_summary_path = target_dir / "feature_summary.md"
    feature_summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    manifest = {
        "performance_id": performance_id,
        "segment_run_id": segment_run_id,
        "created_at": now_iso(),
        "performance_manifest_path": performance_manifest_path.resolve().as_posix(),
        "feature_pack_dir": target_dir.resolve().as_posix(),
        "rhythm_features_path": rhythm_path.as_posix(),
        "harmony_features_path": harmony_path.as_posix(),
        "tags_path": tags_path.as_posix(),
        "ai_training_records_path": ai_records_path.as_posix(),
        "feature_summary_path": feature_summary_path.as_posix(),
    }
    manifest_path = target_dir / "feature_pack_manifest.json"
    save_json(manifest_path, manifest)
    return target_dir.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract full rhythm+harmony feature pack for one performance.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    parser.add_argument("--output-dir", default=None, help="Optional output folder for feature files")
    args = parser.parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else None
    pack_dir = extract_feature_pack(Path(args.performance_manifest), output_dir=output_dir)
    print(f"FEATURE_PACK_DIR={pack_dir.as_posix()}")
    print(f"FEATURE_PACK_MANIFEST_PATH={(pack_dir / 'feature_pack_manifest.json').as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
