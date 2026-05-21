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
    if ai_records_path.exists():
        ai_record_count = len([line for line in ai_records_path.read_text(encoding="utf-8").splitlines() if line.strip()])

    top_tags: list[tuple[str, float]] = []
    tags = tags_payload.get("tags", [])
    if isinstance(tags, list):
        parsed: list[tuple[str, float]] = []
        for item in tags:
            if not isinstance(item, dict):
                continue
            parsed.append((str(item.get("tag", "")), float(item.get("confidence", 0.0) or 0.0)))
        top_tags = sorted(parsed, key=lambda pair: pair[1], reverse=True)[:10]

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
        f"- tag_count: `{tags_payload.get('tag_count', 0)}`",
        f"- ai_training_record_count: `{ai_record_count}`",
        "",
        "## Top Tags",
    ]
    if top_tags:
        for tag_name, confidence in top_tags:
            summary_lines.append(f"- `{tag_name}`: `{round(confidence, 6)}`")
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
