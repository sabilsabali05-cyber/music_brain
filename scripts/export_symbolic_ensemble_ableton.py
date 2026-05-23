from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _to_repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def export_symbolic_ensemble_ableton(
    source_dir: Path = ROOT_DIR / "outputs" / "symbolic_ensemble_v1",
    target_dir: Path = ROOT_DIR / "outputs" / "ableton_project_symbolic_ensemble_v1",
) -> dict:
    source_dir = source_dir.resolve()
    target_dir = target_dir.resolve()
    source_midi = source_dir / "selected_candidate.mid"
    if not source_midi.exists():
        raise FileNotFoundError(f"Missing selected candidate MIDI: {source_midi.as_posix()}")

    target_dir.mkdir(parents=True, exist_ok=True)
    midi_dir = target_dir / "MIDI"
    midi_dir.mkdir(parents=True, exist_ok=True)
    target_midi = midi_dir / "selected_candidate.mid"
    shutil.copy2(source_midi, target_midi)

    report = {}
    report_json = source_dir / "ensemble_generation_report.json"
    if report_json.exists():
        try:
            report = json.loads(report_json.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            report = {}
    fallback_used = bool(report.get("example_retrieval_fallback", False))
    no_real = bool(report.get("no_real_symbolic_backend_available", False))

    track_setup = {
        "project_name": "symbolic_ensemble_v1",
        "midi_files": ["MIDI/selected_candidate.mid"],
        "notes": [
            "Manual import into Ableton arrangement required.",
            "No .als generation claim.",
            "No Synplant automation claim.",
        ],
        "fallback_used": fallback_used,
        "no_real_symbolic_backend_available": no_real,
    }
    (target_dir / "track_setup.json").write_text(json.dumps(track_setup, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (target_dir / "README_FIRST.md").write_text(
        "\n".join(
            [
                "# Symbolic Ensemble Ableton Export",
                "",
                "- Import `MIDI/selected_candidate.mid` into a MIDI track.",
                "- This export is a scaffold only; no `.als` file is generated.",
                f"- fallback_used: `{fallback_used}`",
                f"- no_real_symbolic_backend_available: `{no_real}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    export_report = {
        "status": "ok",
        "source_selected_midi": _to_repo_relative(source_midi),
        "target_selected_midi": _to_repo_relative(target_midi),
        "fallback_used": fallback_used,
        "no_real_symbolic_backend_available": no_real,
        "limitations": [
            "Scaffold export only; no Ableton session file generation.",
            "No model training claim.",
        ],
    }
    (target_dir / "export_report.json").write_text(json.dumps(export_report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return export_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Export symbolic ensemble output to Ableton-ready scaffold.")
    parser.add_argument("--source-dir", default="outputs/symbolic_ensemble_v1")
    parser.add_argument("--target-dir", default="outputs/ableton_project_symbolic_ensemble_v1")
    args = parser.parse_args()
    report = export_symbolic_ensemble_ableton(ROOT_DIR / args.source_dir, ROOT_DIR / args.target_dir)
    print(f"SYMBOLIC_ABLETON_EXPORT_STATUS={report['status']}")
    print(f"SYMBOLIC_ABLETON_EXPORT_MIDI={report['target_selected_midi']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
