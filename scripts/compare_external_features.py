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


def _internal_summary(feature_dir: Path) -> dict[str, Any]:
    rhythm = _safe_json(feature_dir / "rhythm_features.json")
    harmony = _safe_json(feature_dir / "harmony_features.json")
    tags = _safe_json(feature_dir / "tags.json")
    top_tags: list[str] = []
    for item in tags.get("top_unique_tags", []):
        if isinstance(item, dict) and item.get("tag"):
            top_tags.append(str(item["tag"]))
    window_bpms: list[float] = []
    for item in rhythm.get("records", []):
        if not isinstance(item, dict) or str(item.get("granularity")) != "window":
            continue
        features = item.get("features", {})
        if not isinstance(features, dict):
            continue
        try:
            window_bpms.append(float(features.get("estimated_bpm", 0.0) or 0.0))
        except Exception:  # noqa: BLE001
            continue
    internal_tempo = round(sum(window_bpms) / len(window_bpms), 3) if window_bpms else None
    internal_key = None
    for item in harmony.get("records", []):
        if not isinstance(item, dict):
            continue
        features = item.get("features", {})
        if isinstance(features, dict) and features.get("estimated_key"):
            internal_key = str(features["estimated_key"])
            break
    return {"top_tags": top_tags[:10], "tempo_bpm": internal_tempo, "key": internal_key}


def build_external_comparison(performance_manifest_path: Path) -> dict[str, Any]:
    ctx = resolve_performance_context(performance_manifest_path)
    feature_dir = ctx["feature_dir"]
    output_dir = external_output_dir(feature_dir)
    essentia = _safe_json(output_dir / "essentia_features.json")
    musicnn = _safe_json(output_dir / "musicnn_features.json")
    internal = _internal_summary(feature_dir)

    external_tempo = None
    rhythm_desc = essentia.get("rhythm_descriptors", {})
    if isinstance(rhythm_desc, dict):
        for key in ["rhythm.bpm", "rhythm_bpm", "tempo", "bpm"]:
            if key in rhythm_desc:
                try:
                    external_tempo = float(rhythm_desc[key])
                    break
                except Exception:  # noqa: BLE001
                    continue

    external_key = None
    tonal = essentia.get("tonal_descriptors", {})
    if isinstance(tonal, dict):
        for key in ["tonal.key_key", "estimated_key", "key"]:
            if key in tonal:
                external_key = str(tonal[key])
                break

    external_tags: list[str] = []
    if isinstance(musicnn.get("top_tags"), list):
        external_tags = [str(item) for item in musicnn["top_tags"][:10]]

    agreements: list[str] = []
    disagreements: list[str] = []
    if internal["key"] and external_key:
        if str(internal["key"]).lower() == str(external_key).lower():
            agreements.append(f"key agrees at `{internal['key']}`")
        else:
            disagreements.append(f"key differs: internal `{internal['key']}` vs external `{external_key}`")
    if internal["tempo_bpm"] and external_tempo:
        delta = abs(float(internal["tempo_bpm"]) - float(external_tempo))
        if delta <= 8.0:
            agreements.append(f"tempo within tolerance ({delta:.2f} BPM)")
        else:
            disagreements.append(f"tempo differs by {delta:.2f} BPM")
    tag_overlap = sorted(set(internal["top_tags"]).intersection(set(external_tags)))
    if tag_overlap:
        agreements.append(f"tag overlap: {', '.join(tag_overlap[:6])}")
    elif external_tags:
        disagreements.append("no tag overlap between internal and musicnn top tags")

    payload = {
        "performance_id": ctx["performance_id"],
        "segment_run_id": ctx["segment_run_id"],
        "internal_summary": internal,
        "external_summary": {
            "essentia_status": essentia.get("status", "missing"),
            "musicnn_status": musicnn.get("status", "missing"),
            "tempo_bpm": external_tempo,
            "key": external_key,
            "top_tags": external_tags,
        },
        "agreements": agreements,
        "disagreements": disagreements,
        "warnings": [
            "External providers are witness signals and do not override YourMT3-led analysis.",
        ],
    }
    save_json(output_dir / "external_feature_comparison.json", payload)
    md_lines = [
        f"# External Feature Comparison - {ctx['performance_id']}",
        "",
        f"- segment_run_id: `{ctx['segment_run_id']}`",
        f"- essentia_status: `{essentia.get('status', 'missing')}`",
        f"- musicnn_status: `{musicnn.get('status', 'missing')}`",
        "",
        "## Agreements",
    ]
    if agreements:
        md_lines.extend([f"- {item}" for item in agreements])
    else:
        md_lines.append("- none")
    md_lines.extend(["", "## Disagreements"])
    if disagreements:
        md_lines.extend([f"- {item}" for item in disagreements])
    else:
        md_lines.append("- none")
    md_lines.extend(["", "## Warnings", "- External signals are witness-not-truth."])
    (output_dir / "external_feature_comparison.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare internal features against external analyzer outputs.")
    parser.add_argument("performance_manifest", help="Path to performance_manifest.json")
    args = parser.parse_args()
    payload = build_external_comparison(Path(args.performance_manifest))
    print("EXTERNAL_COMPARISON_JSON=" + json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
