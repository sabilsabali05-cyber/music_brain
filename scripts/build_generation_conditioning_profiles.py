from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.music_theory_understanding.theory_to_generation import to_generation_profile_row


PROFILE_NAMES = [
    "harmony_first_ballad",
    "dark_gospel_progression",
    "weird_but_musical_chromatic_motion",
    "sparse_rap_pocket",
    "dense_experimental_rhythm",
    "emotional_piano_skeleton",
    "bass_motion_driven",
    "motif_development",
    "texture_atmosphere",
    "through_composed_story",
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _pick(records: list[dict[str, Any]], predicate) -> list[dict[str, Any]]:
    chosen = [row for row in records if predicate(row)]
    if chosen:
        return chosen[:12]
    return sorted(records, key=lambda r: float(r.get("generation_usefulness_score", 0.0)), reverse=True)[:6]


def main() -> int:
    source_path = ROOT_DIR / "datasets" / "music_theory" / "theory_understanding_records.jsonl"
    out_path = ROOT_DIR / "datasets" / "music_theory" / "generation_conditioning_profiles.jsonl"
    report_json = ROOT_DIR / "reports" / "music_theory" / "generation_conditioning_profiles_report.json"
    report_md = ROOT_DIR / "reports" / "music_theory" / "generation_conditioning_profiles_report.md"
    records = _read_jsonl(source_path)
    packs = {
        "harmony_first_ballad": _pick(records, lambda r: r.get("harmonic_interest_score", 0) > 0.45),
        "dark_gospel_progression": _pick(records, lambda r: "gospel" in " ".join(r.get("theory_notes", [])).lower()),
        "weird_but_musical_chromatic_motion": _pick(
            records,
            lambda r: r.get("harmony_understanding", {}).get("valuable_weirdness")
            and r.get("random_note_penalty", 1) < 0.5,
        ),
        "sparse_rap_pocket": _pick(records, lambda r: r.get("rhythm_understanding", {}).get("loop_friendliness", 0) > 0.5),
        "dense_experimental_rhythm": _pick(records, lambda r: r.get("rhythm_understanding", {}).get("syncopation_hint", 0) > 0.55),
        "emotional_piano_skeleton": _pick(records, lambda r: r.get("voice_leading_score", 0) > 0.4),
        "bass_motion_driven": _pick(records, lambda r: r.get("voice_leading_understanding", {}).get("bass_support_quality", 0) > 0.45),
        "motif_development": _pick(records, lambda r: r.get("motif_reusability_score", 0) > 0.4),
        "texture_atmosphere": _pick(records, lambda r: r.get("texture_role_understanding", {}).get("atmosphere_weight", 0) > 0.4),
        "through_composed_story": _pick(records, lambda r: r.get("form_understanding", {}).get("through_composed_tendency", 0) > 0.5),
    }
    profiles: list[dict[str, Any]] = []
    for name in PROFILE_NAMES:
        selection = packs.get(name, [])
        profile = to_generation_profile_row(name, [])
        if selection:
            profile = to_generation_profile_row(name, [])
            first = selection[0]
            profile.update(
                {
                    "target_tempo_range": first.get("generation_hooks", {}).get("target_tempo_range", [70, 90]),
                    "target_key_or_mode": first.get("generation_hooks", {}).get("target_key_or_mode", "ambiguous_mode_allowed"),
                    "chord_movement_strategy": first.get("generation_hooks", {}).get("chord_movement_strategy", "modal"),
                    "bass_motion_strategy": first.get("generation_hooks", {}).get("bass_motion_strategy", "root_support"),
                    "voice_leading_strategy": first.get("generation_hooks", {}).get("voice_leading_strategy", "stepwise"),
                    "motif_development_strategy": first.get("generation_hooks", {}).get("motif_development_strategy", "repeat_transform"),
                    "rhythm_strategy": first.get("generation_hooks", {}).get("rhythm_strategy", "pocket_first"),
                    "form_strategy": first.get("generation_hooks", {}).get("form_strategy", "hybrid"),
                    "texture_strategy": first.get("generation_hooks", {}).get("texture_strategy", "layered"),
                    "avoid_list": first.get("generation_hooks", {}).get("avoid_list", ["random-note clusters"]),
                    "preserve_list": first.get("generation_hooks", {}).get("preserve_list", []),
                    "tension_curve": first.get("generation_hooks", {}).get("tension_curve", [0.2, 0.3, 0.4, 0.35, 0.25]),
                    "density_curve": first.get("generation_hooks", {}).get("density_curve", [0.2, 0.3, 0.35, 0.32, 0.28]),
                    "confidence": round(sum(float(r.get("generation_usefulness_score", 0.0)) for r in selection) / len(selection), 4),
                    "source_records_used": [r.get("item_id") for r in selection[:25]],
                }
            )
        profile["policy_limits"] = {
            "no_cloud_calls": True,
            "no_model_training": True,
            "no_raw_media_processing": True,
        }
        profile["retrieval_training_status"] = {
            "retrieval_allowed_count": sum(1 for r in selection if r.get("retrieval_allowed")),
            "training_allowed_count": sum(1 for r in selection if r.get("training_allowed")),
        }
        profile["theory_summary"] = {
            "records_count": len(selection),
            "avg_harmonic_interest": round(sum(float(r.get("harmonic_interest_score", 0.0)) for r in selection) / max(1, len(selection)), 4),
        }
        profiles.append(profile)
    _write_jsonl(out_path, profiles)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "profiles_created": len(profiles),
        "profile_names": PROFILE_NAMES,
        "source_records_available": len(records),
        "profiles": profiles,
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = ["# Generation Conditioning Profiles Report", ""]
    for row in profiles:
        lines.append(f"- `{row['profile_name']}` | confidence=`{row['confidence']}` | source_records=`{len(row['source_records_used'])}`")
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"GENERATION_CONDITIONING_PROFILES={out_path.as_posix()}")
    print(f"GENERATION_CONDITIONING_REPORT_JSON={report_json.as_posix()}")
    print(f"GENERATION_CONDITIONING_REPORT_MD={report_md.as_posix()}")
    print(f"PROFILES_CREATED={len(profiles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
