from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_REPORT_JSON = ROOT_DIR / "reports" / "texture_intelligence" / "texture_analysis_plan.public.json"
PRIVATE_REPORT_JSON = ROOT_DIR / "reports" / "texture_intelligence" / "private_texture_analysis_plan.json"
PRIVATE_REPORT_MD = ROOT_DIR / "reports" / "texture_intelligence" / "private_texture_analysis_plan.md"
REPORT_MD = ROOT_DIR / "reports" / "texture_intelligence" / "texture_analysis_plan.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _analysis_needs_for_asset_type(asset_type: str) -> list[str]:
    mapping = {
        "drum_break": ["rhythm_slicing_groove_analysis"],
        "drum_loop": ["rhythm_slicing_groove_analysis"],
        "percussion_loop": ["rhythm_slicing_groove_analysis"],
        "drum_one_shot": ["transient_punch_analysis"],
        "synth_one_shot": ["pitch_envelope_analysis", "synplant_seed_fit_analysis"],
        "bass_one_shot": ["pitch_envelope_analysis", "synplant_seed_fit_analysis"],
        "chord_stab": ["pitch_envelope_analysis", "synplant_seed_fit_analysis"],
        "texture": ["spectral_motion_noise_analysis"],
        "drone": ["spectral_motion_noise_analysis"],
        "fx": ["transition_envelope_analysis"],
        "riser": ["transition_envelope_analysis"],
        "vocal_chop": ["formant_choir_seed_analysis", "synplant_seed_fit_analysis"],
    }
    return mapping.get(asset_type, ["manual_texture_review"])


def _load_sample_records() -> tuple[list[dict[str, Any]], list[str]]:
    records_file = "sample_seed_" + "records.jsonl"
    records_paths = sorted((ROOT_DIR / "datasets" / "sample_libraries").glob("**/" + records_file))
    records: list[dict[str, Any]] = []
    refs: list[str] = []
    for path in records_paths:
        refs.append(path.resolve().relative_to(ROOT_DIR.resolve()).as_posix())
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    records.append(payload)
    return records, refs


def build_texture_analysis_plan() -> tuple[Path, Path, dict[str, Any]]:
    rows, refs = _load_sample_records()
    asset_counts: dict[str, int] = {}
    planned_categories: set[str] = set()
    private_plan_items: list[dict[str, Any]] = []
    for row in rows:
        asset_type = str(row.get("asset_type_guess", "unknown"))
        asset_counts[asset_type] = asset_counts.get(asset_type, 0) + 1
        analysis_needed = _analysis_needs_for_asset_type(asset_type)
        planned_categories.update(analysis_needed)
        private_plan_items.append(
            {
                "sample_id": str(row.get("sample_id", "unknown")),
                "asset_type_guess": asset_type,
                "duration_seconds": row.get("duration_seconds"),
                "analysis_needed": analysis_needed,
                "analysis_status": "planned",
                "notes": [
                    "Planner uses sample index metadata and filename hints only.",
                    "No deep audio processing performed by this step.",
                ],
            }
        )

    public_payload = {
        "status": "ok",
        "created_at": now_iso(),
        "records_found": len(rows),
        "source_refs_count": len(refs),
        "asset_type_counts": dict(sorted(asset_counts.items())),
        "planned_analysis_categories": sorted(planned_categories),
        "limitations": [
            "Planning only; no transcription, no Modal calls, no model training, no new audio processing.",
            "Public plan intentionally excludes per-sample IDs, filenames, and local paths.",
        ],
    }
    private_payload = {
        "status": "private_local_only",
        "created_at": now_iso(),
        "records_found": len(rows),
        "source_refs": refs,
        "analysis_plan": private_plan_items,
        "limitations": [
            "Contains per-sample planning detail and must remain local/ignored.",
            "No deep audio processing performed by this step.",
        ],
    }

    PUBLIC_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_REPORT_JSON.write_text(json.dumps(public_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    PRIVATE_REPORT_JSON.write_text(json.dumps(private_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    PRIVATE_REPORT_MD.write_text(
        "\n".join(
            [
                "# Private Texture Analysis Plan",
                "",
                "This file contains per-sample local planning detail.",
                "Keep local-only and do not commit.",
                f"- records_found: `{private_payload['records_found']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lines = [
        "# Texture Analysis Plan",
        "",
        f"- status: `{public_payload['status']}`",
        f"- records_found: `{public_payload['records_found']}`",
        f"- source_refs_count: `{len(refs)}`",
        "",
        "## Asset Type Counts",
    ]
    if public_payload["asset_type_counts"]:
        for key, value in public_payload["asset_type_counts"].items():
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- none (sample library records not found)")
    lines.extend(["", "## Planned Analysis Categories"])
    for need in public_payload["planned_analysis_categories"]:
        lines.append(f"- `{need}`")
    if not public_payload["planned_analysis_categories"]:
        lines.append("- none")
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in public_payload["limitations"]])
    lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return PUBLIC_REPORT_JSON, REPORT_MD, public_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan texture analysis work from indexed local sample metadata.")
    parser.parse_args()
    json_path, md_path, payload = build_texture_analysis_plan()
    print(f"TEXTURE_ANALYSIS_PLAN_PUBLIC_JSON={json_path.as_posix()}")
    print(f"TEXTURE_ANALYSIS_PLAN_PRIVATE_JSON={PRIVATE_REPORT_JSON.as_posix()}")
    print(f"TEXTURE_ANALYSIS_PLAN_MD={md_path.as_posix()}")
    print(f"TEXTURE_ASSETS_PLANNED={payload['records_found']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
