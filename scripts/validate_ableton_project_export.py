from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_PATH = Path("outputs/ableton_project_v1/AI_Generated_Song_Project")
MIDI_REQUIRED = [
    "generated_song.mid",
    "generated_drums.mid",
    "generated_bass.mid",
    "generated_chords.mid",
    "generated_lead.mid",
    "generated_texture_motifs.mid",
]
PRIVATE_FILE_NAMES = {"private_synplant_seed_paths.json", "private_synplant_seed_paths.md"}
PUBLIC_FILES = {
    "Ableton_Project_Plan.md",
    "track_setup.json",
    "Open_In_Ableton_Instructions.md",
    "README_FIRST.md",
    "synplant_seed_summary.md",
    "export_report.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_gitignored(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "check-ignore", str(path.as_posix())],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return False
    return result.returncode == 0


def _is_in_current_repo(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return False
    if result.returncode != 0:
        return False
    repo_root = Path(result.stdout.strip()).resolve()
    try:
        path.resolve().relative_to(repo_root)
    except Exception:  # noqa: BLE001
        return False
    return True


def validate_ableton_project_export(project_path: Path, *, allow_copied_samples: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    project_path = project_path.resolve()
    if not project_path.exists():
        raise ValueError(f"Missing export project folder: {project_path.as_posix()}")

    midi_dir = project_path / "MIDI"
    if not midi_dir.exists():
        errors.append(f"Missing MIDI folder: {midi_dir.as_posix()}")
    midi_found: list[str] = []
    for name in MIDI_REQUIRED:
        path = midi_dir / name
        if not path.exists():
            errors.append(f"Missing copied MIDI file: {path.as_posix()}")
        else:
            midi_found.append(path.as_posix())

    for file_name in PUBLIC_FILES:
        if not (project_path / file_name).exists():
            errors.append(f"Missing required public file: {(project_path / file_name).as_posix()}")

    report = _read_json(project_path / "export_report.json")
    if report.get("als_generation_status") != "not_implemented_experimental_future":
        errors.append("Report must include als_generation_status=not_implemented_experimental_future")

    # Ensure no private local paths leak into public files.
    for file_name in PUBLIC_FILES:
        path = project_path / file_name
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if "C:\\Users" in content or "C:/Users" in content:
            errors.append(f"Public file contains private local path: {path.as_posix()}")
        if ".als generated" in content.lower() or "generated .als" in content.lower():
            errors.append(f"Public file incorrectly claims .als generation: {path.as_posix()}")

    private_files = [project_path / name for name in PRIVATE_FILE_NAMES if (project_path / name).exists()]
    for private_path in private_files:
        if not _is_in_current_repo(private_path):
            continue
        if not _is_gitignored(private_path):
            errors.append(f"Private file is not gitignored: {private_path.as_posix()}")

    samples_dir = project_path / "Samples"
    copied_audio = []
    if samples_dir.exists():
        copied_audio = [p for p in samples_dir.rglob("*") if p.is_file()]
    if copied_audio and not allow_copied_samples:
        errors.append("Audio samples were copied but validator was run without allow_copied_samples.")

    if errors:
        raise ValueError("\n".join(errors))

    return {
        "status": "ok",
        "project_path": project_path.as_posix(),
        "midi_files_count": len(midi_found),
        "private_files_count": len(private_files),
        "copied_audio_count": len(copied_audio),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Ableton project export v1 outputs.")
    parser.add_argument(
        "project_path",
        nargs="?",
        default=DEFAULT_PROJECT_PATH.as_posix(),
        help="Export project path (default: outputs/ableton_project_v1/AI_Generated_Song_Project)",
    )
    parser.add_argument("--allow-copied-samples", action="store_true", help="Allow copied sample files in Samples/")
    args = parser.parse_args()
    result = validate_ableton_project_export(Path(args.project_path), allow_copied_samples=args.allow_copied_samples)
    print(f"ABLETON_EXPORT_VALIDATION_STATUS={result['status']}")
    print(f"MIDI_FILES_COUNT={result['midi_files_count']}")
    print(f"PRIVATE_FILES_COUNT={result['private_files_count']}")
    print(f"COPIED_AUDIO_COUNT={result['copied_audio_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
