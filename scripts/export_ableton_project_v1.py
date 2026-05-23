from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.ableton_export.ableton_export_schema import (  # noqa: E402
    AbletonExportReport,
    AbletonMidiClipAssignment,
    AbletonProjectExportPlan,
    AbletonPureDataPlaceholder,
    AbletonSampleAssignment,
    AbletonSynplantSeedInstruction,
    AbletonTrackExportPlan,
)

DEFAULT_EXPORT_DIR = ROOT_DIR / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project"
EXPECTED_MIDI = [
    "generated_song.mid",
    "generated_drums.mid",
    "generated_bass.mid",
    "generated_chords.mid",
    "generated_lead.mid",
    "generated_texture_motifs.mid",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _to_repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def export_ableton_project_v1(
    tangible_output_folder: Path,
    *,
    copy_local_samples: bool = False,
    export_project_path: Path | None = None,
) -> dict[str, Any]:
    tangible_output_folder = tangible_output_folder.resolve()
    export_project_path = (export_project_path or DEFAULT_EXPORT_DIR).resolve()
    midi_out = export_project_path / "MIDI"
    samples_out = export_project_path / "Samples"
    export_project_path.mkdir(parents=True, exist_ok=True)
    midi_out.mkdir(parents=True, exist_ok=True)

    plan_json = _read_json(tangible_output_folder / "demo_composition_plan.json")
    report_json = _read_json(tangible_output_folder / "generation_report.json")
    seed_suggestions = _read_json_list(tangible_output_folder / "synplant_seed_suggestions.json")

    midi_files_copied: list[str] = []
    for midi_name in EXPECTED_MIDI:
        source = tangible_output_folder / midi_name
        if not source.exists():
            continue
        target = midi_out / midi_name
        shutil.copy2(source, target)
        midi_files_copied.append(_to_repo_relative(target))

    section_rows = plan_json.get("sections", []) if isinstance(plan_json.get("sections"), list) else []
    first_section = section_rows[0] if section_rows and isinstance(section_rows[0], dict) else {}
    section_name = str(first_section.get("section_id", "full_song"))
    section_start = float(first_section.get("start_seconds", 0.0) or 0.0)
    section_end = float(first_section.get("end_seconds", report_json.get("ratio_timing", {}).get("duration_seconds", 180.0)) or 180.0)

    track_seed_map = {
        "drums": "drum_break_or_loop",
        "bass": "bass_or_synth_seed",
        "chords": "chord_stab_or_pad_seed",
        "lead": "vocal_or_synth_seed",
        "texture_bed": "texture_or_drone_seed",
        "transition_fx": "fx_or_riser_seed",
    }
    track_midi_map = {
        "drums": "generated_drums.mid",
        "bass": "generated_bass.mid",
        "chords": "generated_chords.mid",
        "lead": "generated_lead.mid",
        "texture_bed": "generated_texture_motifs.mid",
        "transition_fx": "generated_texture_motifs.mid",
    }

    track_plans: list[AbletonTrackExportPlan] = []
    midi_assignments: list[AbletonMidiClipAssignment] = []
    sample_assignments: list[AbletonSampleAssignment] = []
    seed_instructions: list[AbletonSynplantSeedInstruction] = []
    pd_placeholders: list[AbletonPureDataPlaceholder] = []

    for role, midi_name in track_midi_map.items():
        track_name = role.replace("_", " ").title()
        midi_rel = f"MIDI/{midi_name}"
        track_plans.append(
            AbletonTrackExportPlan(
                track_name=track_name,
                role=role,
                track_type="midi",
                midi_file=midi_rel,
                device_suggestion="Ableton MIDI track",
                notes="Drag MIDI clip onto track timeline manually.",
                arrangement_start_seconds=section_start,
                arrangement_end_seconds=section_end,
                section_name=section_name,
                limitations="No .als generation in v1.",
            )
        )
        midi_assignments.append(
            AbletonMidiClipAssignment(
                track_name=track_name,
                role=role,
                midi_file=midi_rel,
                arrangement_start_seconds=section_start,
                arrangement_end_seconds=section_end,
                section_name=section_name,
                notes="Drop clip in Arrangement View.",
                limitations="Clip warp and quantization must be reviewed manually.",
            )
        )
        pd_placeholders.append(
            AbletonPureDataPlaceholder(
                track_name=track_name,
                role=role,
                device_suggestion="Future Max for Live / Pure Data bridge",
                notes="Placeholder lane for future control-routing experiments.",
            )
        )

    copied_audio_sample_count = 0
    private_seed_rows: list[dict[str, Any]] = []
    public_seed_rows: list[dict[str, Any]] = []
    for item in seed_suggestions:
        role = str(item.get("track_role", "unknown"))
        sample_id = str(item.get("sample_id", "unknown"))
        source_path = str(item.get("source_path", ""))
        asset_type = str(item.get("asset_type_guess", "unknown"))
        public_id = f"sample_{hashlib.sha1(sample_id.encode('utf-8')).hexdigest()[:10]}"
        label = f"{public_id} ({asset_type})"
        private_seed_rows.append(
            {
                "track_role": role,
                "sample_id": sample_id,
                "source_path": source_path,
                "asset_type_guess": asset_type,
                "note": "Use manually in Synplant; no automation performed.",
            }
        )
        public_seed_rows.append(
            {
                "track_role": role,
                "sample_id": sample_id,
                "public_safe_sample_label": label,
                "asset_type_guess": asset_type,
                "instruction": "Manually drag this sample into Synplant / Ableton if desired.",
            }
        )
        sample_assignments.append(
            AbletonSampleAssignment(
                track_name=role.replace("_", " ").title(),
                role=role,
                selected_sample_ref=public_id,
                local_source_path_private="private_local_only",
                public_safe_sample_label=label,
                device_suggestion="Synplant seed input (manual)",
                notes="Keep private local path in ignored private file only.",
            )
        )
        seed_instructions.append(
            AbletonSynplantSeedInstruction(
                track_name=role.replace("_", " ").title(),
                role=role,
                selected_sample_ref=public_id,
                local_source_path_private="private_local_only",
                public_safe_sample_label=label,
                device_suggestion=track_seed_map.get(role, "manual_seed"),
            )
        )
        if copy_local_samples and source_path:
            src = Path(source_path)
            if src.exists() and src.is_file():
                samples_out.mkdir(parents=True, exist_ok=True)
                target = samples_out / src.name
                shutil.copy2(src, target)
                copied_audio_sample_count += 1

    project_plan = AbletonProjectExportPlan(
        project_name="AI_Generated_Song_Project",
        source_tangible_output=_to_repo_relative(tangible_output_folder),
        export_root=_to_repo_relative(export_project_path),
        tracks=track_plans,
        midi_clip_assignments=midi_assignments,
        sample_assignments=sample_assignments,
        synplant_seed_instructions=seed_instructions,
        puredata_placeholders=pd_placeholders,
    )
    export_report = AbletonExportReport(
        status="success",
        export_project_path=_to_repo_relative(export_project_path),
        midi_files_copied=midi_files_copied,
        copy_local_samples_enabled=copy_local_samples,
        copied_audio_sample_count=copied_audio_sample_count,
        limitations=[
            "ALS generation is not implemented in v1.",
            "Synplant automation is not implemented.",
            "Pure Data and Max for Live tracks are placeholders only.",
        ],
    )

    track_setup_path = export_project_path / "track_setup.json"
    report_path = export_project_path / "export_report.json"
    plan_md_path = export_project_path / "Ableton_Project_Plan.md"
    instructions_path = export_project_path / "Open_In_Ableton_Instructions.md"
    readme_path = export_project_path / "README_FIRST.md"
    public_seed_summary_path = export_project_path / "synplant_seed_summary.md"
    private_seed_json = export_project_path / "private_synplant_seed_paths.json"
    private_seed_md = export_project_path / "private_synplant_seed_paths.md"

    track_setup_path.write_text(json.dumps(asdict(project_plan), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(asdict(export_report), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    plan_md_lines = [
        "# Ableton Project Plan (v1)",
        "",
        "- als_generation_status: `not_implemented_experimental_future`",
        "- This export creates a project folder + MIDI + setup metadata.",
        "- It does not create a guaranteed valid `.als` session file.",
        "",
        "## Track Plan",
    ]
    for track in track_plans:
        plan_md_lines.append(f"- `{track.track_name}` ({track.role}): load `{track.midi_file}`")
    plan_md_path.write_text("\n".join(plan_md_lines) + "\n", encoding="utf-8")

    instructions_path.write_text(
        "\n".join(
            [
                "# Open In Ableton Instructions",
                "",
                "1. Open Ableton Live and create a new Set.",
                "2. Create MIDI tracks matching `track_setup.json`.",
                "3. Drag MIDI clips from `MIDI/` into corresponding tracks.",
                "4. Review `synplant_seed_summary.md` and manually choose seeds.",
                "5. Optionally use placeholder lanes for Max for Live / Pure Data routing.",
                "",
                "ALS generation status: `not_implemented_experimental_future`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    readme_path.write_text(
        "\n".join(
            [
                "# README FIRST",
                "",
                "This folder is an Ableton-ready project scaffold.",
                "- Includes copied MIDI from tangible demo outputs.",
                "- Includes track setup metadata and manual load instructions.",
                "- Does not include a generated `.als` file (future experimental work).",
                "- Synplant usage is manual only.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    if public_seed_rows:
        summary_lines = ["# Synplant Seed Summary (Public Safe)", ""]
        for row in public_seed_rows:
            summary_lines.append(
                f"- `{row['track_role']}` -> `{row['public_safe_sample_label']}` ({row['instruction']})"
            )
        public_seed_summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    else:
        public_seed_summary_path.write_text(
            "# Synplant Seed Summary (Public Safe)\n\nNo seed suggestions were found in tangible outputs.\n",
            encoding="utf-8",
        )

    if private_seed_rows:
        private_seed_json.write_text(json.dumps(private_seed_rows, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        private_seed_md.write_text(
            "\n".join(
                ["# Private Synplant Seed Paths", ""]
                + [f"- `{row['track_role']}` -> `{row['sample_id']}` path `{row['source_path']}`" for row in private_seed_rows]
            )
            + "\n",
            encoding="utf-8",
        )

    public_safe_files = [
        _to_repo_relative(plan_md_path),
        _to_repo_relative(track_setup_path),
        _to_repo_relative(instructions_path),
        _to_repo_relative(readme_path),
        _to_repo_relative(public_seed_summary_path),
        _to_repo_relative(report_path),
    ]
    private_files = []
    if private_seed_json.exists():
        private_files.append(_to_repo_relative(private_seed_json))
    if private_seed_md.exists():
        private_files.append(_to_repo_relative(private_seed_md))

    report_payload = asdict(export_report)
    report_payload["public_safe_files_created"] = public_safe_files
    report_payload["private_files_created"] = private_files
    report_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"ABLETON_EXPORT_PROJECT_PATH={_to_repo_relative(export_project_path)}")
    print(f"MIDI_FILES_COPIED={len(midi_files_copied)}")
    print(f"PUBLIC_SAFE_FILES_CREATED={len(public_safe_files)}")
    print(f"PRIVATE_FILES_CREATED={len(private_files)}")
    print(f"AUDIO_SAMPLES_COPIED={copied_audio_sample_count}")
    print("ALS_GENERATION_STATUS=not_implemented_experimental_future")
    return {
        "export_project_path": _to_repo_relative(export_project_path),
        "midi_files_copied": midi_files_copied,
        "public_safe_files_created": public_safe_files,
        "private_files_created": private_files,
        "audio_samples_copied": copied_audio_sample_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export tangible demo outputs into an Ableton-ready project scaffold (v1).")
    parser.add_argument("tangible_output_folder", help="Path to tangible demo output folder, e.g. outputs/tangible_generation_v1")
    parser.add_argument(
        "--copy-local-samples",
        action="store_true",
        help="Optionally copy local sample files referenced by seed suggestions into Samples/ (default: off).",
    )
    args = parser.parse_args()
    export_ableton_project_v1(Path(args.tangible_output_folder), copy_local_samples=args.copy_local_samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
