from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import MidiFile

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

OUT_DIR = ROOT_DIR / "outputs" / "source_understood_composition_v1"
SUMMARY_JSON = OUT_DIR / "source_understood_composition_summary.json"
SUMMARY_MD = OUT_DIR / "source_understood_composition_summary.md"
COMPOSITION_MIDI = OUT_DIR / "final_source_understood.mid"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _midi_gate_passed(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing_midi_file"
    lowered = path.as_posix().lower()
    if "fixture" in lowered:
        return False, "fixture_draft_not_allowed"
    try:
        midi = MidiFile(path.as_posix())
    except Exception:  # noqa: BLE001
        return False, "midi_parse_failed"
    note_events = 0
    for track in midi.tracks:
        for msg in track:
            if msg.type == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                note_events += 1
    if note_events <= 0:
        return False, "no_note_events"
    return True, ""


def main() -> int:
    audit = _read_json(ROOT_DIR / "reports" / "model_witnesses" / "model_witness_audit.json")
    manifest = _read_json(ROOT_DIR / "reports" / "source_audio_study" / "source_audio_study_manifest_report.json")
    witness_run = _read_json(ROOT_DIR / "reports" / "model_witnesses" / "source_audio_witness_run_report.json")
    consensus = _read_json(ROOT_DIR / "reports" / "model_witnesses" / "source_audio_witness_consensus_report.json")
    dossier = _read_json(ROOT_DIR / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json")
    presentable = _read_json(ROOT_DIR / "outputs" / "presentable_composition_from_draft_v1" / "build_presentable_composition_from_draft_report.json")

    selected_rel = str(presentable.get("selected_full_midi_path", "")).strip()
    selected_midi = ROOT_DIR / selected_rel if selected_rel else Path("")
    draft_gate_passed, draft_gate_reason = _midi_gate_passed(selected_midi) if selected_rel else (False, "missing_selected_midi_path")

    artifact_gate = all(
        [
            bool(audit),
            bool(manifest),
            bool(witness_run),
            bool(consensus),
            bool(dossier),
        ]
    )
    can_generate = artifact_gate and draft_gate_passed

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    final_midi_rel = ""
    if can_generate and selected_midi.exists():
        shutil.copy2(selected_midi, COMPOSITION_MIDI)
        final_midi_rel = COMPOSITION_MIDI.relative_to(ROOT_DIR).as_posix()

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "generated" if can_generate else "blocked",
        "artifact_gate_passed": artifact_gate,
        "draft_real_midi_gate_passed": draft_gate_passed,
        "draft_real_midi_gate_reason": draft_gate_reason,
        "source_understood_composition_generated": can_generate,
        "final_midi_path": final_midi_rel,
        "source_db_principles_cited": [row.get("principle_id", "") for row in dossier.get("strongest_principles", [])][:5],
        "rejected_principles": list(dossier.get("rejected_principles", [])),
        "witness_influence": list(dossier.get("witness_influence_summary", [])),
        "weak_evidence_areas": list(dossier.get("weak_evidence_limits", [])),
        "transformation_vs_copy": str(dossier.get("transformation_vs_copy_policy", "")),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Understood Composition Summary",
        "",
        f"- status: `{summary['status']}`",
        f"- artifact_gate_passed: `{str(summary['artifact_gate_passed']).lower()}`",
        f"- draft_real_midi_gate_passed: `{str(summary['draft_real_midi_gate_passed']).lower()}`",
        f"- draft_real_midi_gate_reason: `{summary['draft_real_midi_gate_reason']}`",
        f"- source_understood_composition_generated: `{str(summary['source_understood_composition_generated']).lower()}`",
        f"- final_midi_path: `{summary['final_midi_path'] or 'not_generated'}`",
        "",
        "## Source DB Principles Cited",
        *[f"- {row}" for row in summary["source_db_principles_cited"]],
        "",
        "## Rejected Principles",
        *[f"- {row}" for row in summary["rejected_principles"]],
        "",
        "## Witness Influence",
        *[f"- {row}" for row in summary["witness_influence"]],
        "",
        "## Weak Evidence Areas",
        *[f"- {row}" for row in summary["weak_evidence_areas"]],
    ]
    SUMMARY_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"SOURCE_UNDERSTOOD_COMPOSITION_SUMMARY_JSON={SUMMARY_JSON.as_posix()}")
    print(f"SOURCE_UNDERSTOOD_COMPOSITION_SUMMARY_MD={SUMMARY_MD.as_posix()}")
    print(f"DRAFT_REAL_MIDI_GATE_PASSED={str(summary['draft_real_midi_gate_passed']).lower()}")
    print(f"SOURCE_UNDERSTOOD_COMPOSITION_GENERATED={str(summary['source_understood_composition_generated']).lower()}")
    print(f"FINAL_MIDI_PATH={summary['final_midi_path']}")
    return 0 if can_generate else 1


if __name__ == "__main__":
    raise SystemExit(main())
