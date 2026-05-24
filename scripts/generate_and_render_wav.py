from __future__ import annotations

import json
import sys
from pathlib import Path

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

GENERATION_ID = "generated_wav_v1"


def _write_simple_midi(path: Path, notes: list[tuple[float, float, int, int]], channel: int = 0) -> None:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = 500000
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    timeline: list[tuple[float, Message]] = []
    for start, end, note, velocity in notes:
        timeline.append((start, Message("note_on", note=note, velocity=velocity, channel=channel, time=0)))
        timeline.append((end, Message("note_off", note=note, velocity=0, channel=channel, time=0)))
    timeline.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    prev = 0.0
    for when, msg in timeline:
        delta = int(round(second2tick(max(0.0, when - prev), midi.ticks_per_beat, tempo)))
        track.append(msg.copy(time=max(0, delta)))
        prev = when
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))


def _generate_demo_midi(output_root: Path) -> tuple[Path, Path]:
    stems_dir = output_root / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    full_midi = output_root / "full.mid"

    lead = [(0.0, 0.5, 72, 86), (0.5, 1.0, 74, 84), (1.0, 1.5, 76, 90), (1.5, 2.0, 79, 94)]
    bass = [(0.0, 1.0, 48, 88), (1.0, 2.0, 50, 88)]
    pad = [(0.0, 2.0, 60, 65), (0.0, 2.0, 64, 64), (0.0, 2.0, 67, 63)]
    drums = [(0.0, 0.1, 36, 110), (0.5, 0.6, 38, 105), (1.0, 1.1, 36, 112), (1.5, 1.6, 38, 104)]

    _write_simple_midi(stems_dir / "lead.mid", lead, channel=0)
    _write_simple_midi(stems_dir / "bass.mid", bass, channel=1)
    _write_simple_midi(stems_dir / "pad.mid", pad, channel=2)
    _write_simple_midi(stems_dir / "drums.mid", drums, channel=9)
    _write_simple_midi(full_midi, lead + bass + pad + drums, channel=0)
    return full_midi, stems_dir


def _write_generation_docs(output_root: Path, plan_md: str) -> None:
    (output_root / "render_plan.md").write_text(plan_md, encoding="utf-8")
    (output_root / "generation_report.md").write_text(
        "\n".join(
            [
                "# Generation Report",
                "",
                "- source: deterministic local MIDI scaffold",
                "- cloud_calls: false",
                "- model_training: false",
                "- model_downloads: false",
                "- unauthorized_audio_processed: false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_root / "provenance_report.md").write_text(
        "\n".join(
            [
                "# Provenance Report",
                "",
                "- full.mid was created locally by `scripts/generate_and_render_wav.py`.",
                "- stems are derived from deterministic in-script note patterns.",
                "- no external audio ingestion occurred.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_root / "review_sheet.md").write_text(
        "\n".join(
            [
                "# Review Sheet",
                "",
                "- Validate composition intent per stem.",
                "- Validate VST assignment manually if needed.",
                "- Confirm WAV status and backend reason.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    output_root = ROOT_DIR / "outputs" / GENERATION_ID
    output_root.mkdir(parents=True, exist_ok=True)

    full_midi, stems_dir = _generate_demo_midi(output_root)
    registry = load_registry(ROOT_DIR / "config" / "local_vst_registry.local.json")
    local_config = load_local_render_config(ROOT_DIR / "config" / "local_render_config.local.json")
    backend = str(local_config.get("default_render_backend", "dry_run_plan_only"))
    if backend not in {
        "reaper_auto_render",
        "ableton_assisted_render",
        "preview_synth_render",
        "dry_run_plan_only",
    }:
        backend = "dry_run_plan_only"

    plan = build_render_plan_from_stems(
        generation_id=GENERATION_ID,
        stems_dir=stems_dir,
        registry=registry,
        default_backend=backend,
    )
    write_render_plan_json(output_root / "render_plan.json", plan)
    plan_md = render_plan_markdown(plan)
    _write_generation_docs(output_root, plan_md)

    report = run_reaper_auto_render(
        generation_id=GENERATION_ID,
        plan=plan,
        reaper_executable_path=str(local_config.get("reaper_executable_path", "")),
        vst_registry_configured=registry.configured,
        local_render_root=ROOT_DIR / "renders" / GENERATION_ID,
    )
    final_wav = ROOT_DIR / "renders" / GENERATION_ID / "final.wav"
    full_midi_rel = full_midi.relative_to(ROOT_DIR).as_posix()
    final_wav_rel = final_wav.relative_to(ROOT_DIR).as_posix()
    wav_result = verify_wav_file(
        final_wav,
        render_backend="reaper_auto_render",
        source_midi_provenance=full_midi_rel,
    )

    missing_config: list[str] = []
    if not Path(str(local_config.get("reaper_executable_path", ""))).exists():
        missing_config.append("reaper_executable_path")
    if not registry.configured:
        missing_config.append("local_vst_registry.local.json")

    assisted_pack = ""
    wav_status = "render_failed"
    if wav_result.exists and wav_result.readable and wav_result.duration_seconds > 0 and wav_result.nonzero_samples:
        wav_status = "rendered_wav_available"
    else:
        reason = "render_backend_missing" if "reaper_executable_path" in missing_config else "vst_config_missing"
        if report.render_backend_status == "planned_not_executed":
            assisted = create_ableton_assisted_render_pack(
                generation_id=GENERATION_ID,
                stems_dir=stems_dir,
                plan=plan,
                reason="reaper_not_executed_or_unavailable",
            )
            assisted_pack = assisted.pack_path
            wav_status = "assisted_render_pack_created"
            if reason == "render_backend_missing":
                wav_status = "render_backend_missing"
            if reason == "vst_config_missing":
                wav_status = "vst_config_missing"

    wav_status_path = output_root / "wav_status.md"
    wav_status_path.write_text(f"{wav_status}\n", encoding="utf-8")

    verification_md = ROOT_DIR / "reports" / "local_rendering" / f"{GENERATION_ID}_render_verification.md"
    verification_md.parent.mkdir(parents=True, exist_ok=True)
    verification_md.write_text(
        "\n".join(
            [
                "# Generated WAV Verification",
                "",
                f"- wav_rendered: `{str(wav_result.exists and wav_result.readable and wav_result.duration_seconds > 0 and wav_result.nonzero_samples).lower()}`",
                f"- final_wav_path: `{final_wav_rel if wav_result.exists else 'none'}`",
                f"- duration_seconds: `{wav_result.duration_seconds:.3f}`",
                f"- sample_rate: `{wav_result.sample_rate}`",
                f"- channels: `{wav_result.channels}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    status_payload = {
        "generation_id": GENERATION_ID,
        "render_backend_status": report.render_backend_status,
        "reaper_available": report.reaper_available,
        "vst_registry_configured": registry.configured,
        "wav_rendered": bool(wav_result.exists and wav_result.readable and wav_result.duration_seconds > 0 and wav_result.nonzero_samples),
        "vst_render_used": bool(report.vst_render_used),
        "fallback_preview_used": False,
        "render_plan_only": bool(report.render_plan_only),
        "final_wav_path": final_wav_rel if wav_result.exists else "",
        "assisted_render_pack": assisted_pack,
        "missing_config": missing_config,
        "wav_status": wav_status,
    }
    (output_root / "render_result.json").write_text(json.dumps(status_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"OUTPUT_DIR={output_root.as_posix()}")
    print(f"WAV_STATUS={wav_status}")
    print(f"WAV_RENDERED={str(status_payload['wav_rendered']).lower()}")
    if assisted_pack:
        print(f"ASSISTED_RENDER_PACK={assisted_pack}")
    if missing_config:
        print(f"MISSING_CONFIG={','.join(missing_config)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
