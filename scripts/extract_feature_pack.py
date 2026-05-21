from __future__ import annotations

import argparse
from pathlib import Path

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
    segments_manifest_path, _, _ = get_active_paths(performance_manifest)
    performance_id, _, segment_run_id = performance_metadata(performance_manifest, segments_manifest_path)
    target_dir = output_dir or default_feature_dir(performance_id, segment_run_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    rhythm_path = extract_rhythm_features(performance_manifest_path, output_dir=target_dir)
    harmony_path = extract_harmony_features(performance_manifest_path, output_dir=target_dir)
    tags_path = tag_performance_features(performance_manifest_path, output_dir=target_dir)
    ai_records_path = build_ai_training_records(performance_manifest_path, output_dir=target_dir)

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
