from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mido import MidiFile

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "generation_iterations"
REPORT_JSON = REPORT_DIR / "iteration_comparison_report.json"
REPORT_MD = REPORT_DIR / "iteration_comparison_report.md"

TRACK_FILES = {
    "song": "generated_song.mid",
    "drums": "generated_drums.mid",
    "bass": "generated_bass.mid",
    "chords": "generated_chords.mid",
    "lead": "generated_lead.mid",
    "texture": "generated_texture_motifs.mid",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _count_notes(path: Path) -> int:
    if not path.exists():
        return 0
    midi = MidiFile(str(path))
    return sum(1 for track in midi.tracks for msg in track if msg.type == "note_on" and getattr(msg, "velocity", 0) > 0)


def _section_summary(output_dir: Path) -> list[dict[str, Any]]:
    plan = _read_json(output_dir / "demo_composition_plan.json")
    sections = plan.get("sections", [])
    if not isinstance(sections, list):
        return []
    summary: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        summary.append(
            {
                "section_id": str(section.get("section_id", "")),
                "start_seconds": float(section.get("start_seconds", 0.0)),
                "end_seconds": float(section.get("end_seconds", 0.0)),
            }
        )
    return summary


def _source_diversity(output_dir: Path) -> int:
    report = _read_json(output_dir / "generation_report.json")
    source_ids = report.get("source_example_ids", [])
    if not isinstance(source_ids, list):
        return 0
    return len({str(item) for item in source_ids if str(item).strip()})


def _ableton_export_available(output_dir: Path) -> bool:
    candidate = output_dir.parent / "ableton_project_v1" / "AI_Generated_Song_Project" / "track_setup.json"
    return candidate.exists()


def compare_generation_iterations(old_output: Path, new_output: Path) -> dict[str, Any]:
    old_notes = {role: _count_notes(old_output / name) for role, name in TRACK_FILES.items()}
    new_notes = {role: _count_notes(new_output / name) for role, name in TRACK_FILES.items()}
    note_delta = {role: new_notes.get(role, 0) - old_notes.get(role, 0) for role in TRACK_FILES}

    old_roles = sorted([role for role, count in old_notes.items() if count > 0])
    new_roles = sorted([role for role, count in new_notes.items() if count > 0])

    payload = {
        "status": "ok",
        "old_output": old_output.as_posix(),
        "new_output": new_output.as_posix(),
        "note_counts": {
            "old": old_notes,
            "new": new_notes,
            "delta_new_minus_old": note_delta,
        },
        "track_role_coverage": {
            "old": old_roles,
            "new": new_roles,
        },
        "section_timing": {
            "old": _section_summary(old_output),
            "new": _section_summary(new_output),
        },
        "source_example_diversity": {
            "old_unique_source_example_ids": _source_diversity(old_output),
            "new_unique_source_example_ids": _source_diversity(new_output),
        },
        "ableton_export_availability": {
            "old": _ableton_export_available(old_output),
            "new": _ableton_export_available(new_output),
        },
        "provenance": {
            "script": "scripts/compare_generation_iterations.py",
            "audio_processing_performed": False,
        },
        "limitations": [
            "Comparison is structural and metadata-driven; it does not evaluate musical quality.",
            "Ableton availability check uses default export folder convention only.",
        ],
    }
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Generation Iteration Comparison Report",
        "",
        f"- old_output: `{payload['old_output']}`",
        f"- new_output: `{payload['new_output']}`",
        "",
        "## Note Count Delta",
    ]
    for role, value in payload["note_counts"]["delta_new_minus_old"].items():
        lines.append(f"- {role}: `{value}`")
    lines.extend(["", "## Track Role Coverage"])
    lines.append(f"- old: `{', '.join(payload['track_role_coverage']['old']) or 'none'}`")
    lines.append(f"- new: `{', '.join(payload['track_role_coverage']['new']) or 'none'}`")
    lines.extend(["", "## Source Diversity"])
    lines.append(
        "- old_unique_source_example_ids: "
        f"`{payload['source_example_diversity']['old_unique_source_example_ids']}`"
    )
    lines.append(
        "- new_unique_source_example_ids: "
        f"`{payload['source_example_diversity']['new_unique_source_example_ids']}`"
    )
    lines.extend(["", "## Ableton Export Availability"])
    lines.append(f"- old: `{payload['ableton_export_availability']['old']}`")
    lines.append(f"- new: `{payload['ableton_export_availability']['new']}`")
    lines.extend(["", "## Limitations"])
    lines.extend([f"- {item}" for item in payload["limitations"]])
    lines.append("")
    return "\n".join(lines)


def write_comparison_report(old_output: Path, new_output: Path) -> tuple[Path, Path, dict[str, Any]]:
    payload = compare_generation_iterations(old_output=old_output, new_output=new_output)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(payload), encoding="utf-8")
    return REPORT_JSON, REPORT_MD, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare tangible generation output iterations.")
    parser.add_argument("old_output", help="Previous tangible output folder")
    parser.add_argument("new_output", help="New tangible output folder")
    args = parser.parse_args()
    json_path, md_path, payload = write_comparison_report(Path(args.old_output), Path(args.new_output))
    print(f"ITERATION_COMPARISON_JSON={json_path.as_posix()}")
    print(f"ITERATION_COMPARISON_MD={md_path.as_posix()}")
    print(f"ITERATION_COMPARISON_STATUS={payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
