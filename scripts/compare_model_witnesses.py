from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.external_analyzer_common import external_output_dir, resolve_performance_context
from scripts.feature_dataset_common import load_json, save_json


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = load_json(path)
    except Exception:  # noqa: BLE001
        return {}
    return payload


def compare_model_witnesses(performance_manifest_path: Path) -> dict[str, Any]:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    witness_dir = external_output_dir(feature_dir)
    rhythm = _safe_json(feature_dir / "rhythm_features.json")
    harmony = _safe_json(feature_dir / "harmony_features.json")
    meter_time = _safe_json(feature_dir / "rhythm_time" / "meter_time_features.json")
    pitch_harmony = _safe_json(feature_dir / "pitch_harmony" / "pitch_harmony_features.json")
    tags = _safe_json(feature_dir / "tags.json")
    essentia = _safe_json(witness_dir / "essentia_features.json")
    musicnn = _safe_json(witness_dir / "musicnn_features.json")
    beat = _safe_json(witness_dir / "beat_tracker_features.json")
    music21 = _safe_json(witness_dir / "music21_features.json")

    internal_tempo = rhythm.get("summary", {}).get("estimated_bpm") if isinstance(rhythm.get("summary"), dict) else None
    if internal_tempo is None:
        window_bpms = []
        for rec in rhythm.get("records", []) if isinstance(rhythm.get("records"), list) else []:
            if not isinstance(rec, dict):
                continue
            feat = rec.get("features", {})
            if isinstance(feat, dict) and feat.get("estimated_bpm") is not None:
                try:
                    window_bpms.append(float(feat.get("estimated_bpm")))
                except Exception:  # noqa: BLE001
                    pass
        internal_tempo = (sum(window_bpms) / len(window_bpms)) if window_bpms else None

    external_tempo = None
    if isinstance(beat.get("features"), dict):
        tempos = beat["features"].get("tempo_candidates_bpm", [])
        if isinstance(tempos, list) and tempos:
            try:
                external_tempo = float(tempos[0])
            except Exception:  # noqa: BLE001
                external_tempo = None
    if external_tempo is None and isinstance(essentia.get("rhythm_descriptors"), dict):
        for key in ["rhythm.bpm", "rhythm_bpm", "tempo", "bpm"]:
            if key in essentia["rhythm_descriptors"]:
                try:
                    external_tempo = float(essentia["rhythm_descriptors"][key])
                    break
                except Exception:  # noqa: BLE001
                    continue

    internal_key = None
    if isinstance(pitch_harmony.get("macro_record"), dict):
        hypotheses = pitch_harmony["macro_record"].get("key_hypotheses", [])
        if isinstance(hypotheses, list) and hypotheses and isinstance(hypotheses[0], dict):
            internal_key = hypotheses[0].get("key")
    if internal_key is None:
        for rec in harmony.get("records", []) if isinstance(harmony.get("records"), list) else []:
            if not isinstance(rec, dict):
                continue
            feat = rec.get("features", {})
            if isinstance(feat, dict) and feat.get("estimated_key"):
                internal_key = feat.get("estimated_key")
                break

    external_key = None
    if isinstance(music21.get("features"), dict):
        k = music21["features"].get("key_candidates", [])
        if isinstance(k, list) and k and isinstance(k[0], dict):
            external_key = k[0].get("key")
    if external_key is None and isinstance(essentia.get("tonal_descriptors"), dict):
        for key in ["tonal.key_key", "estimated_key", "key"]:
            if key in essentia["tonal_descriptors"]:
                external_key = essentia["tonal_descriptors"][key]
                break

    internal_top_tags = [str(item.get("tag")) for item in tags.get("top_unique_tags", [])[:10] if isinstance(item, dict) and item.get("tag")] if isinstance(tags.get("top_unique_tags"), list) else []
    external_top_tags = [str(item) for item in musicnn.get("top_tags", [])[:10]] if isinstance(musicnn.get("top_tags"), list) else []
    overlap = sorted(set(internal_top_tags).intersection(set(external_top_tags)))

    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "tempo_alignment": {
            "internal_tempo_bpm": internal_tempo,
            "external_tempo_bpm": external_tempo,
            "delta_bpm": (abs(float(internal_tempo) - float(external_tempo)) if internal_tempo is not None and external_tempo is not None else None),
        },
        "tonal_alignment": {
            "internal_key_candidate": internal_key,
            "external_key_candidate": external_key,
            "agreement": bool(internal_key and external_key and str(internal_key).lower() == str(external_key).lower()),
        },
        "tag_alignment": {
            "internal_top_tags": internal_top_tags,
            "external_top_tags": external_top_tags,
            "overlap": overlap,
        },
        "meter_alignment": {
            "internal_meter_hypotheses": meter_time.get("beat_meter_hypotheses", [])[:3] if isinstance(meter_time.get("beat_meter_hypotheses"), list) else [],
            "external_meter_hypotheses": beat.get("features", {}).get("meter_hypotheses", []) if isinstance(beat.get("features"), dict) else [],
        },
        "provider_status": {
            "essentia": essentia.get("status", "missing"),
            "musicnn": musicnn.get("status", "missing"),
            "beat_tracker": beat.get("status", "missing"),
            "music21": music21.get("status", "missing"),
        },
    }
    out_json = witness_dir / "model_witness_comparison.json"
    save_json(out_json, payload)
    out_md = witness_dir / "model_witness_comparison.md"
    out_md.write_text(
        "\n".join(
            [
                f"# Model Witness Comparison - {ctx['performance_id']}",
                "",
                f"- tempo_alignment: `{json.dumps(payload['tempo_alignment'], ensure_ascii=True)}`",
                f"- tonal_alignment: `{json.dumps(payload['tonal_alignment'], ensure_ascii=True)}`",
                f"- tag_overlap_count: `{len(overlap)}`",
                f"- provider_status: `{json.dumps(payload['provider_status'], ensure_ascii=True)}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare internal model outputs with external witness outputs.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    payload = compare_model_witnesses(Path(args.performance_manifest))
    print("MODEL_WITNESS_COMPARISON_JSON=" + json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
