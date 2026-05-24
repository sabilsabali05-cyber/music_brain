from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, second2tick

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.local_rendering.ableton_backend import create_ableton_assisted_render_pack  # noqa: E402
from features.local_rendering.midi_to_render_plan import build_render_plan_from_stems  # noqa: E402
from features.local_rendering.reaper_backend import load_local_render_config, run_reaper_auto_render  # noqa: E402
from features.local_rendering.render_plan_schema import render_plan_markdown, write_render_plan_json  # noqa: E402
from features.local_rendering.vst_registry_schema import load_registry  # noqa: E402
from features.local_rendering.wav_verifier import verify_wav_file  # noqa: E402

GENERATION_ID = "complete_song_v1"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _run_python(script_name: str, args: list[str] | None = None) -> tuple[int, str]:
    command = [sys.executable, str(ROOT_DIR / "scripts" / script_name)] + (args or [])
    result = subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True, check=False)
    combined = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
    return result.returncode, combined


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _write_simple_midi(path: Path, notes: list[tuple[float, float, int, int]], channel: int = 9, bpm: int = 100) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = int(round(60_000_000 / max(1, bpm)))
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    timeline: list[tuple[float, Message]] = []
    for start, end, note, velocity in notes:
        timeline.append((start, Message("note_on", note=note, velocity=velocity, channel=channel, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, channel=channel, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    previous = 0.0
    for when, msg in timeline:
        delta = int(round(second2tick(max(0.0, when - previous), midi.ticks_per_beat, tempo)))
        track.append(msg.copy(time=max(0, delta)))
        previous = when
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))


def _midi_exists_and_parses(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        MidiFile(path.as_posix())
    except Exception:  # noqa: BLE001
        return False
    return True


def _read_training_status() -> dict[str, Any]:
    model_path = ROOT_DIR / "artifacts" / "model_training" / "chordpotion_preset_selector" / "model.json"
    training_report_path = ROOT_DIR / "reports" / "model_training" / "chordpotion_preset_selector_training_report.md"
    outcomes_path = ROOT_DIR / "datasets" / "chordpotion" / "chordpotion_audition_outcomes.jsonl"
    rows = _read_jsonl(outcomes_path)
    labeled_count = sum(1 for row in rows if str(row.get("final_label", "")).strip())
    model_payload = _read_json(model_path)
    report_text = training_report_path.read_text(encoding="utf-8") if training_report_path.exists() else ""
    trained_artifact_exists = model_path.exists() and bool(model_payload)
    report_confirms = "trained_selector_used: `true`" in report_text.lower()
    trained_selector_used = bool(trained_artifact_exists and report_confirms and labeled_count >= 20)
    if labeled_count <= 0:
        training_status = "not_allowed_no_explicit_labels"
    elif trained_selector_used:
        training_status = "trained_selector_available"
    else:
        training_status = "labels_present_trained_selector_unconfirmed"
    return {
        "training_status": training_status,
        "labeled_examples_count": labeled_count,
        "trained_selector_used": trained_selector_used,
    }


def main() -> int:
    output_root = ROOT_DIR / "outputs" / GENERATION_ID
    stems_dir = output_root / "stems"
    output_root.mkdir(parents=True, exist_ok=True)
    stems_dir.mkdir(parents=True, exist_ok=True)

    local_config_path = ROOT_DIR / "config" / "local_render_config.local.json"
    local_registry_path = ROOT_DIR / "config" / "local_vst_registry.local.json"
    local_config = load_local_render_config(local_config_path)
    registry = load_registry(local_registry_path)
    local_config_present = local_config_path.exists()
    local_registry_present = local_registry_path.exists()

    theory_profiles = _read_jsonl(ROOT_DIR / "datasets" / "music_theory" / "generation_conditioning_profiles.jsonl")
    corpus_rows = _read_jsonl(ROOT_DIR / "datasets" / "music_theory" / "theory_understanding_records.jsonl")
    texture_context = _read_json(ROOT_DIR / "reports" / "texture_intelligence" / "sound_palette_context.json")
    texture_available = bool(texture_context)

    intent = {
        "generation_id": GENERATION_ID,
        "selected_theory_profile": "harmony_first_ballad" if theory_profiles else "default_local_profile",
        "selected_texture_profile": "warm_emotional_chord_bed" if texture_available else "default_texture_profile",
        "corpus_records_available": len(corpus_rows),
        "theory_profiles_available": len(theory_profiles),
        "texture_context_available": texture_available,
        "rules": {
            "no_cloud_calls": True,
            "no_fake_claims": True,
            "no_training_without_labels": True,
        },
    }
    (output_root / "generation_intent.json").write_text(json.dumps(intent, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    rc, message = _run_python("generate_chordpotion_ready_skeleton.py")
    if rc != 0:
        raise RuntimeError(f"generate_chordpotion_ready_skeleton.py failed: {message}")

    source_root = ROOT_DIR / "outputs" / "chordpotion_generation_v1"
    mapped = {
        "harmony_skeleton.mid": stems_dir / "skeleton.mid",
        "bass.mid": stems_dir / "bass.mid",
        "lead_guide.mid": stems_dir / "lead.mid",
    }
    for source_name, destination in mapped.items():
        source = source_root / source_name
        if source.exists():
            destination.write_bytes(source.read_bytes())

    bpm = int(local_config.get("chordpotion_default_bpm", 100) or 100)
    optional_drums = stems_dir / "drums_optional.mid"
    if not optional_drums.exists():
        _write_simple_midi(
            optional_drums,
            notes=[(0.0, 0.1, 36, 104), (0.5, 0.6, 38, 98), (1.0, 1.1, 36, 108), (1.5, 1.6, 38, 100)],
            channel=9,
            bpm=bpm,
        )

    (output_root / "harmony_skeleton.mid").write_bytes((stems_dir / "skeleton.mid").read_bytes())
    (output_root / "bass.mid").write_bytes((stems_dir / "bass.mid").read_bytes())
    (output_root / "lead_guide.mid").write_bytes((stems_dir / "lead.mid").read_bytes())

    reaper_path = str(local_config.get("reaper_executable_path", "")).strip()
    reaper_available = bool(reaper_path and Path(reaper_path).exists())
    chordpotion_plugin_id = str(local_config.get("preferred_chordpotion_plugin_id", "")).strip()
    chordpotion_plugin = registry.get_plugin(chordpotion_plugin_id) if chordpotion_plugin_id else None
    chordpotion_configured = bool(chordpotion_plugin_id and chordpotion_plugin is not None)
    chordpotion_available = bool(chordpotion_plugin and chordpotion_plugin.available and chordpotion_plugin.category == "midi_fx")

    chordpotion_attempted = False
    chordpotion_status = "missing_config"
    transformed_midi_path = output_root / "transformed_harmony.mid"
    chordpotion_missing_config: list[str] = []

    if not chordpotion_configured:
        chordpotion_missing_config.append("preferred_chordpotion_plugin_id")
    if chordpotion_configured and not chordpotion_available:
        chordpotion_missing_config.append("chordpotion_plugin_unavailable")
    if chordpotion_configured and chordpotion_available:
        chordpotion_attempted = True
        _run_python("build_chordpotion_transform_plan.py", ["--generation-id", GENERATION_ID])
        _run_python("audition_chordpotion_presets.py", ["--generation-id", GENERATION_ID, "--audition-id", f"{GENERATION_ID}_audition"])
        _run_python("render_chordpotion_with_reaper.py", ["--generation-id", GENERATION_ID])
        if transformed_midi_path.exists():
            chordpotion_status = "attempted"
        else:
            chordpotion_status = "attempted_no_transform_capture"

    render_plan = build_render_plan_from_stems(
        generation_id=GENERATION_ID,
        stems_dir=stems_dir,
        registry=registry,
        default_backend="reaper_auto_render",
    )
    write_render_plan_json(output_root / "render_plan.json", render_plan)
    (output_root / "render_plan.md").write_text(render_plan_markdown(render_plan), encoding="utf-8")

    render_report = run_reaper_auto_render(
        generation_id=GENERATION_ID,
        plan=render_plan,
        reaper_executable_path=reaper_path,
        vst_registry_configured=registry.configured,
        local_render_root=ROOT_DIR / "renders" / GENERATION_ID,
    )

    final_wav = ROOT_DIR / "renders" / GENERATION_ID / "final.wav"
    verification = verify_wav_file(
        final_wav,
        render_backend="reaper_auto_render",
        source_midi_provenance=(Path("outputs") / GENERATION_ID / "harmony_skeleton.mid").as_posix(),
    )
    wav_rendered = bool(
        verification.exists and verification.readable and verification.duration_seconds > 0 and verification.nonzero_samples
    )
    assisted_pack_path = ""
    if not wav_rendered:
        reason = "reaper_or_registry_unavailable" if not reaper_available or not registry.configured else "render_not_verified"
        assisted_pack = create_ableton_assisted_render_pack(
            generation_id=GENERATION_ID,
            stems_dir=stems_dir,
            plan=render_plan,
            reason=reason,
        )
        assisted_pack_path = assisted_pack.pack_path

    transformed_midi_captured = _midi_exists_and_parses(transformed_midi_path)
    training = _read_training_status()
    final_wav_path = _repo_rel(final_wav) if wav_rendered else ""
    wav_status = "rendered_wav_available" if wav_rendered else "assisted_render_pack_created"
    (output_root / "wav_status.md").write_text(wav_status + "\n", encoding="utf-8")

    blockers: list[str] = []
    if not wav_rendered:
        if not reaper_available:
            blockers.append("reaper_executable_path_missing_or_unavailable")
        if not registry.configured:
            blockers.append("vst_registry_missing_or_empty")
        if not blockers:
            blockers.append("final_wav_not_verified")
    if chordpotion_status == "missing_config":
        blockers.extend(chordpotion_missing_config)

    integration_status = {
        "generation_id": GENERATION_ID,
        "local_mode_only": True,
        "cloud_called": False,
        "load_local_config": {
            "local_render_config_present": local_config_present,
            "local_vst_registry_present": local_registry_present,
        },
        "profiles_loaded": {
            "corpus_records_count": len(corpus_rows),
            "theory_profiles_count": len(theory_profiles),
            "texture_profiles_available": texture_available,
        },
        "generation_intent_path": _repo_rel(output_root / "generation_intent.json"),
        "stems_generated": {
            "skeleton": _midi_exists_and_parses(stems_dir / "skeleton.mid"),
            "bass": _midi_exists_and_parses(stems_dir / "bass.mid"),
            "lead": _midi_exists_and_parses(stems_dir / "lead.mid"),
            "optional_drums": _midi_exists_and_parses(optional_drums),
        },
        "chordpotion": {
            "configured": chordpotion_configured,
            "available": chordpotion_available,
            "attempted": chordpotion_attempted,
            "status": chordpotion_status,
            "transformed_midi_captured": transformed_midi_captured,
        },
        "render": {
            "reaper_status": "available" if reaper_available else "missing_config",
            "vst_status": "configured" if registry.configured else "missing_config",
            "render_backend_status": render_report.render_backend_status,
            "wav_rendered": wav_rendered,
            "final_wav_path": final_wav_path,
            "assisted_pack_path": assisted_pack_path,
        },
        "selector": {
            "selector_status": "trained_selector_used" if training["trained_selector_used"] else "heuristic_or_unconfirmed",
            "trained_selector_used": bool(training["trained_selector_used"]),
        },
        "training": {
            "training_status": training["training_status"],
            "labeled_examples_count": int(training["labeled_examples_count"]),
        },
        "fallback_paths": {
            "direct_stems_render_fallback_used": not wav_rendered,
            "assisted_pack_created": bool(assisted_pack_path),
        },
        "blockers": blockers,
    }

    reports_dir = ROOT_DIR / "reports" / "integration"
    reports_dir.mkdir(parents=True, exist_ok=True)
    status_json_path = reports_dir / "complete_song_pipeline_status.json"
    status_md_path = reports_dir / "complete_song_pipeline_status.md"
    status_json_path.write_text(json.dumps(integration_status, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    status_md_lines = [
        "# Complete Song Pipeline Status",
        "",
        f"- generation_id: `{GENERATION_ID}`",
        "- cloud_called: `false`",
        f"- wav_rendered: `{str(wav_rendered).lower()}`",
        f"- final_wav_path: `{final_wav_path or 'none'}`",
        f"- chordpotion_status: `{chordpotion_status}`",
        f"- transformed_midi_captured: `{str(transformed_midi_captured).lower()}`",
        f"- reaper_status: `{integration_status['render']['reaper_status']}`",
        f"- vst_status: `{integration_status['render']['vst_status']}`",
        f"- selector_status: `{integration_status['selector']['selector_status']}`",
        f"- training_status: `{integration_status['training']['training_status']}`",
        "",
        "## Blockers",
    ]
    if blockers:
        status_md_lines.extend([f"- {item}" for item in blockers])
    else:
        status_md_lines.append("- none")
    status_md_lines.append("")
    status_md_path.write_text("\n".join(status_md_lines), encoding="utf-8")

    review_sheet = output_root / "review_sheet.md"
    review_sheet.write_text(
        "\n".join(
            [
                "# Complete Song Review Sheet",
                "",
                "- [ ] Verify stem balance: skeleton, bass, lead, optional drums.",
                "- [ ] Confirm no fake ChordPotion or fake WAV claims.",
                f"- [ ] Verify wav_status (`{wav_status}`) and blocker list.",
                "- [ ] If assisted pack exists, perform manual render and update status.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    feedback_template = ROOT_DIR / "reports" / "review_queue" / "complete_song_v1_feedback_template.json"
    feedback_template.parent.mkdir(parents=True, exist_ok=True)
    feedback_template.write_text(
        json.dumps(
            {
                "generation_id": GENERATION_ID,
                "reviewed_by": "",
                "accepted": False,
                "notes": "",
                "issues": [],
                "requested_changes": [
                    "arrangement",
                    "sound_selection",
                    "mix_balance",
                    "render_validation",
                ],
                "status_files": {
                    "wav_status": _repo_rel(output_root / "wav_status.md"),
                    "pipeline_status_json": _repo_rel(status_json_path),
                },
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (output_root / "pipeline_execution_log.json").write_text(
        json.dumps(
            {
                "steps_completed": [
                    "load_local_config",
                    "load_profiles",
                    "build_generation_intent",
                    "generate_stems",
                    "chordpotion_optional_attempt",
                    "build_vst_render_plan",
                    "attempt_local_render_or_fallback",
                    "write_status_and_review_outputs",
                ],
                "render_report": asdict(render_report),
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"COMPLETE_COMMAND=scripts/dev.cmd generate-complete-song-wav")
    print(f"WAV_RENDERED={str(wav_rendered).lower()}")
    print(f"FINAL_WAV_PATH={final_wav_path or 'none'}")
    print(f"CHORDPOTION_STATUS={chordpotion_status}")
    print(f"REAPER_STATUS={integration_status['render']['reaper_status']}")
    print(f"VST_STATUS={integration_status['render']['vst_status']}")
    print(f"SELECTOR_STATUS={integration_status['selector']['selector_status']}")
    print(f"TRAINING_STATUS={integration_status['training']['training_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
