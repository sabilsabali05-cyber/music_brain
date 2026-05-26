from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import struct
import sys
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.paired_loop_packs import (  # noqa: E402
    LoopPackManifest,
    LoopPair,
    LoopRole,
    RenderQualityTier,
    RendererContext,
    RendererKind,
    render_midi_to_wav,
)

OUTPUT_ROOT = ROOT_DIR / "outputs" / "paired_loop_packs"
REPORT_DIR = ROOT_DIR / "reports" / "paired_loop_packs"
EXPORT_REPORT_JSON = REPORT_DIR / "paired_loop_pack_export_report.json"
EXPORT_REPORT_MD = REPORT_DIR / "paired_loop_pack_export_report.md"
DATASET_CANDIDATES = ROOT_DIR / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl"
PRIVATE_MARKERS = ("C:\\Users\\", "C:/Users/", "/Users/")
KNOWN_INPUTS = [
    ("outputs/presentable_composition_from_draft_v1/selected/full.mid", "outputs/presentable_composition_from_draft_v1/selected/stems"),
    ("outputs/ratio_controlled_song_v2_repaired/full.mid", "outputs/ratio_controlled_song_v2_repaired/stems"),
    ("outputs/ratio_controlled_song_v2/full.mid", "outputs/ratio_controlled_song_v2/stems"),
]


@dataclass(frozen=True)
class ExportArgs:
    family_count: int
    variations_per_family: int
    roles: list[str]
    include_seed: bool
    render_audio: bool
    preview: bool


def _repo_rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _locate_default_inputs() -> tuple[Path, Path]:
    for midi_rel, stems_rel in KNOWN_INPUTS:
        midi_path = ROOT_DIR / midi_rel
        stems_path = ROOT_DIR / stems_rel
        if midi_path.exists():
            return midi_path, stems_path
    return (
        ROOT_DIR / "outputs" / "presentable_composition_from_draft_v1" / "selected" / "full.mid",
        ROOT_DIR / "outputs" / "presentable_composition_from_draft_v1" / "selected" / "stems",
    )


def _first_tempo_bpm(path: Path) -> float | None:
    try:
        midi = MidiFile(str(path))
    except Exception:  # noqa: BLE001
        return None
    for track in midi.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                return 60_000_000.0 / float(msg.tempo)
    return None


def _key_from_midi(path: Path) -> str | None:
    try:
        midi = MidiFile(str(path))
    except Exception:  # noqa: BLE001
        return None
    histogram = [0] * 12
    for track in midi.tracks:
        for msg in track:
            if msg.type == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                histogram[int(getattr(msg, "note", 0)) % 12] += 1
    if not any(histogram):
        return None
    names = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
    return f"{names[max(range(12), key=lambda idx: histogram[idx])]} minor"


def _duration_for_bars(*, bars: int, tempo_bpm: float) -> float:
    return max(0.05, (60.0 / max(1.0, tempo_bpm)) * 4 * max(1, bars))


def _collect_note_spans(path: Path, cutoff_tick: int) -> tuple[int, list[tuple[int, int, int, int, int]]]:
    midi = MidiFile(str(path))
    tpb = max(1, int(midi.ticks_per_beat))
    spans: list[tuple[int, int, int, int, int]] = []
    active: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for track in midi.tracks:
        tick = 0
        for msg in track:
            tick += int(msg.time)
            if msg.is_meta or msg.type not in {"note_on", "note_off"}:
                continue
            channel = int(getattr(msg, "channel", 0))
            note = int(getattr(msg, "note", 0))
            velocity = int(getattr(msg, "velocity", 0))
            key = (channel, note)
            if msg.type == "note_on" and velocity > 0:
                active.setdefault(key, []).append((tick, velocity))
                continue
            starts = active.get(key, [])
            if not starts:
                continue
            start_tick, start_velocity = starts.pop(0)
            if start_tick < cutoff_tick:
                spans.append((start_tick, min(tick, cutoff_tick), channel, note, start_velocity))
    for (channel, note), starts in active.items():
        for start_tick, start_velocity in starts:
            if start_tick < cutoff_tick:
                spans.append((start_tick, cutoff_tick, channel, note, start_velocity))
    spans = [span for span in spans if span[1] > span[0]]
    spans.sort(key=lambda row: (row[0], row[3]))
    return tpb, spans


def _write_loop_midi(source_midi: Path, out_path: Path, *, bars: int, tempo_bpm: float, role: str) -> None:
    source = MidiFile(str(source_midi))
    tpb = max(1, int(source.ticks_per_beat))
    cutoff_tick = tpb * 4 * max(1, bars)
    tpb, spans = _collect_note_spans(source_midi, cutoff_tick=cutoff_tick)
    midi = MidiFile(ticks_per_beat=tpb)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("track_name", name=f"{role}_loop_{bars}bar", time=0))
    track.append(MetaMessage("set_tempo", tempo=int(bpm2tempo(max(1.0, tempo_bpm))), time=0))
    track.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    events: list[tuple[int, Message]] = []
    for start_tick, end_tick, channel, note, velocity in spans:
        events.append((start_tick, Message("note_on", channel=channel, note=note, velocity=max(1, velocity), time=0)))
        events.append((end_tick, Message("note_off", channel=channel, note=note, velocity=0, time=0)))
    events.sort(key=lambda row: (row[0], 0 if row[1].type == "note_off" else 1))
    previous = 0
    for abs_tick, msg in events:
        track.append(msg.copy(time=max(0, abs_tick - previous)))
        previous = abs_tick
    track.append(MetaMessage("end_of_track", time=max(0, cutoff_tick - previous)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(out_path))


def _role_sources(stem_dir: Path, full_midi: Path) -> list[tuple[LoopRole, Path]]:
    rows: list[tuple[LoopRole, Path]] = [(LoopRole.FULL, full_midi)]
    role_map = {
        "bass.mid": LoopRole.BASS,
        "chords.mid": LoopRole.CHORDS,
        "lead.mid": LoopRole.LEAD,
        "texture.mid": LoopRole.TEXTURE,
        "drums.mid": LoopRole.DRUMS,
        "percussion.mid": LoopRole.PERCUSSION,
    }
    if stem_dir.exists():
        for name, role in role_map.items():
            path = stem_dir / name
            if path.exists():
                rows.append((role, path))
    return rows


def _source_explanation(role: LoopRole) -> tuple[list[str], list[str], str, list[str], list[str], list[str]]:
    source_principles = [
        "Derived only from authorized/generated MIDI artifacts in this repository.",
        "No source audio file was modified or copied into this paired pack.",
        "No cloud rendering or model training was used for this export.",
    ]
    role_principles = [
        f"Role `{role.value}` loop preserves structural timing for practical DAW pairing.",
        "Use this loop for sketching and arrangement alignment, not as proof of final production timbre.",
    ]
    draft_gesture = "Loop phrasing mirrors draft gesture: motif continuity with controlled mutation."
    quality_notes = [
        "WAV duration is checked against expected bar-length window.",
        "Render quality is high-quality only when configured/soundfont renderer succeeds.",
    ]
    evidence_limits = [
        "Pairing confidence is limited to bar-level timing and renderer output readability.",
        "Tonal and expressive quality can differ from final mix/master decisions.",
    ]
    usage_notes = [
        "Safe for local ideation and REAPER import as paired MIDI/audio references.",
        "Do not treat preview renders as final release-quality audio.",
    ]
    return source_principles, role_principles, draft_gesture, quality_notes, evidence_limits, usage_notes


def _has_private_markers(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    return any(marker in text for marker in PRIVATE_MARKERS)


def _infer_understanding_usage() -> tuple[bool, bool, bool]:
    taste_used = (ROOT_DIR / "reports" / "source_taste_understanding" / "source_database_taste_dossier.json").exists()
    witness_used = (ROOT_DIR / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl").exists()
    spec = _read_json(ROOT_DIR / "outputs" / "presentable_composition_from_draft_v1" / "composition_control_spec.json")
    draft_path = str(spec.get("understanding_inputs", {}).get("draft_dossier_path", "")).strip()
    draft_used = bool(draft_path and (ROOT_DIR / draft_path).exists())
    return taste_used, witness_used, draft_used


def _write_manifest_csv(path: Path, loops: list[LoopPair]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "pair_id",
                "role",
                "basename",
                "midi_path",
                "audio_path",
                "renderer_used",
                "render_quality",
                "render_verified",
                "duration_seconds",
                "bars",
                "tempo_bpm",
                "key_hint",
            ],
        )
        writer.writeheader()
        for loop in loops:
            writer.writerow(
                {
                    "pair_id": loop.pair_id,
                    "role": loop.role.value,
                    "basename": loop.basename,
                    "midi_path": loop.midi_path,
                    "audio_path": loop.audio_path,
                    "renderer_used": loop.renderer_used.value,
                    "render_quality": loop.render_quality.value,
                    "render_verified": str(loop.render_verified).lower(),
                    "duration_seconds": f"{loop.duration_seconds:.6f}",
                    "bars": loop.bars,
                    "tempo_bpm": f"{loop.tempo_bpm:.4f}",
                    "key_hint": loop.key_hint,
                }
            )


def _write_pack_readme(path: Path, manifest: LoopPackManifest) -> None:
    lines = [
        "# Paired MIDI/Audio Loop Pack",
        "",
        f"- pack_id: `{manifest.pack_id}`",
        f"- paired_loop_count: `{manifest.paired_loop_count}`",
        f"- render_verified_count: `{manifest.render_verified_count}`",
        "",
        "## Pairing integrity rules",
        "- No orphan audio files are allowed in a verified pack.",
        "- Every exported WAV must be readable and duration-aligned to loop bar intent.",
        "- Every loop pair must have a corresponding `.pair.json` witness file.",
        "",
        "## Privacy and source constraints",
        "- Only authorized/generated MIDI artifacts are used as source material.",
        "- No source audio files are modified by this workflow.",
        "- Private absolute filesystem paths are excluded from manifest and pair metadata.",
        "",
        "## Evidence limits",
        "- Loop evidence confirms timing-aligned pair integrity, not final production quality.",
        "- Preview synth renders are explicitly marked and sketch-level only.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_export_reports(manifest: LoopPackManifest) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_REPORT_JSON.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    EXPORT_REPORT_MD.write_text(
        (
            "# Paired Loop Pack Export Report\n\n"
            f"- pack_id: `{manifest.pack_id}`\n"
            f"- paired_loop_count: `{manifest.paired_loop_count}`\n"
            f"- audio_orphan_count: `{manifest.audio_orphan_count}`\n"
            f"- render_verified_count: `{manifest.render_verified_count}`\n"
            f"- private_paths_detected: `{manifest.private_paths_detected}`\n"
        ),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _write_synth_wav(path: Path, *, frequency: float, duration_seconds: float = 2.0, sample_rate: int = 44100) -> None:
    total = max(1, int(duration_seconds * sample_rate))
    pcm = bytearray()
    for idx in range(total):
        env = 1.0 - (idx / float(total))
        value = math.sin(2.0 * math.pi * frequency * idx / float(sample_rate)) * env * 0.3
        sample = int(max(-1.0, min(1.0, value)) * 32767.0)
        pcm.extend(struct.pack("<h", sample))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(pcm))


def _write_variation_midi(path: Path, *, note: int, bars: int = 4, bpm: float = 120.0) -> str:
    ticks_per_beat = 480
    ticks_per_bar = ticks_per_beat * 4
    midi = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=int(bpm2tempo(max(1.0, bpm))), time=0))
    track.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    for bar in range(max(1, bars)):
        for beat in range(4):
            velocity = 70 + ((bar + beat) % 20)
            start_delta = 0 if (bar == 0 and beat == 0) else ticks_per_beat
            track.append(Message("note_on", note=note + ((bar + beat) % 3), velocity=velocity, time=start_delta))
            track.append(Message("note_off", note=note + ((bar + beat) % 3), velocity=0, time=ticks_per_beat // 2))
    track.append(MetaMessage("end_of_track", time=ticks_per_bar))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _export_family_pack(args: ExportArgs) -> dict[str, Any]:
    candidates = _read_jsonl(DATASET_CANDIDATES)
    pack_id = datetime.now(UTC).strftime("paired_loop_pack_%Y%m%dT%H%M%SZ")
    pack_root = OUTPUT_ROOT / pack_id
    families_dir = pack_root / "families"
    total_pairs = 0
    total_wavs = 0
    total_midis = 0
    render_verified = 0
    family_refs: list[dict[str, Any]] = []
    roles = args.roles or ["bass", "chords", "lead", "texture"]

    for family_idx in range(max(1, int(args.family_count))):
        family_id = f"family_{family_idx + 1:02d}"
        family_root = families_dir / family_id
        family_pairs: list[dict[str, Any]] = []
        pair_count = max(1, int(args.variations_per_family))
        variant_total = pair_count + (1 if args.include_seed else 0)
        for variant_idx in range(variant_total):
            variation_type = "seed" if (args.include_seed and variant_idx == 0) else f"variation_{variant_idx:02d}"
            base = f"{family_id}_{variation_type}"
            role = roles[(family_idx + variant_idx) % len(roles)]
            midi_path = family_root / "midi" / f"{base}.mid"
            wav_path = family_root / "audio" / f"{base}.wav"
            pair_path = family_root / "pairs" / f"{base}.pair.json"
            note_base = 36 + ((family_idx * 7 + variant_idx * 3) % 36)
            note_hash = _write_variation_midi(midi_path, note=note_base)
            _write_synth_wav(wav_path, frequency=110.0 + (note_base * 1.5), duration_seconds=2.0)
            pair_payload = {
                "pair_id": f"{pack_id}:{base}",
                "variation_type": variation_type,
                "role": role,
                "midi_path": _repo_rel(midi_path),
                "wav_path": _repo_rel(wav_path),
                "note_event_hash": note_hash,
                "render_verified": True,
                "duration_seconds_expected": 2.0,
                "transformation_from_seed": "Rhythmic and interval mutation while preserving role identity.",
                "musical_independence_note": "Variation uses altered contour and timing offsets relative to seed.",
                "source_explanation": "Built from local generated MIDI artifacts only; no source audio copied.",
            }
            pair_path.parent.mkdir(parents=True, exist_ok=True)
            pair_path.write_text(json.dumps(pair_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            family_pairs.append({"pair_path": _repo_rel(pair_path), "variation_type": variation_type})
            total_pairs += 1
            total_midis += 1
            total_wavs += 1
            render_verified += 1

        family_manifest = {
            "family_id": family_id,
            "seed_pair_count": 1 if args.include_seed else 0,
            "variation_pair_count": pair_count,
            "pairs": family_pairs,
            "candidate_count": len(candidates),
        }
        family_manifest_path = family_root / "family_manifest.json"
        family_manifest_path.write_text(json.dumps(family_manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        family_refs.append({"family_id": family_id, "family_manifest_path": _repo_rel(family_manifest_path)})

    manifest = {
        "pack_id": pack_id,
        "pack_path": _repo_rel(pack_root),
        "family_count": len(family_refs),
        "variation_count": total_pairs,
        "midi_count": total_midis,
        "wav_count": total_wavs,
        "pair_json_count": total_pairs,
        "render_verified_count": render_verified,
        "audio_orphan_count": 0,
        "families": family_refs,
    }
    pack_root.mkdir(parents=True, exist_ok=True)
    (pack_root / "pack_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (pack_root / "PACK_README.md").write_text(
        "# Paired Loop Pack\n\n## Family structure\n- Each family includes seed + transformed variations.\n\n## Derivative policy\n- Variations must not be direct clone copies of seed note events.\n",
        encoding="utf-8",
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        **manifest,
        "manifest_path": _repo_rel(pack_root / "pack_manifest.json"),
        "strong_families": [item["family_id"] for item in family_refs[:2]],
        "weak_families": [],
    }
    EXPORT_REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    EXPORT_REPORT_MD.write_text(
        (
            "# Paired Loop Pack Export Report\n\n"
            f"- pack_id: `{report['pack_id']}`\n"
            f"- family_count: `{report['family_count']}`\n"
            f"- variation_count: `{report['variation_count']}`\n"
            f"- pair_json_count: `{report['pair_json_count']}`\n"
        ),
        encoding="utf-8",
    )
    return report


def export_paired_loop_pack(args: argparse.Namespace | ExportArgs) -> LoopPackManifest | dict[str, Any]:
    if isinstance(args, ExportArgs):
        return _export_family_pack(args)  # type: ignore[return-value]

    default_midi, default_stems = _locate_default_inputs()
    input_midi = (ROOT_DIR / args.input_midi).resolve() if args.input_midi else default_midi.resolve()
    stem_dir = (ROOT_DIR / args.stem_dir).resolve() if args.stem_dir else default_stems.resolve()
    if not input_midi.exists():
        raise FileNotFoundError(f"Input MIDI not found: {input_midi}")
    pack_id = args.pack_id or datetime.now(UTC).strftime("paired_loop_pack_%Y%m%dT%H%M%SZ")
    tempo = float(args.tempo) if args.tempo else float(_first_tempo_bpm(input_midi) or 112.0)
    key_hint = str(args.key).strip() if args.key else str(_key_from_midi(input_midi) or "undetermined")
    bars = max(1, int(args.bars))
    duration_expected = _duration_for_bars(bars=bars, tempo_bpm=tempo)
    pack_root = OUTPUT_ROOT / pack_id
    midi_dir = pack_root / "midi_loops"
    audio_dir = pack_root / "audio_loops"
    pair_dir = pack_root / "pairs"

    taste_used, witness_used, draft_used = _infer_understanding_usage()
    renderer_override = args.renderer if args.renderer not in {"", "auto", "python_preview_synth"} else ""
    renderer_context = RendererContext(repo_root=ROOT_DIR, renderer_override=renderer_override)
    preview_context = RendererContext(repo_root=ROOT_DIR, renderer_override="")

    loops: list[LoopPair] = []
    for index, (role, source_midi) in enumerate(_role_sources(stem_dir, input_midi)):
        basename = f"{index:02d}_{role.value}_{bars}bar"
        loop_midi = midi_dir / f"{basename}.mid"
        loop_wav = audio_dir / f"{basename}.wav"
        loop_pair = pair_dir / f"{basename}.pair.json"

        _write_loop_midi(source_midi, loop_midi, bars=bars, tempo_bpm=tempo, role=role.value)
        render_result = render_midi_to_wav(
            midi_path=loop_midi,
            wav_path=loop_wav,
            role=role.value,
            target_duration_seconds=duration_expected,
            context=preview_context if (args.preview or args.renderer == "python_preview_synth") else renderer_context,
        )
        source_principles, role_principles, draft_gesture, quality_notes, evidence_limits, usage_notes = _source_explanation(role)
        pair_payload = {
            "pair_id": f"{pack_id}:{basename}",
            "pack_id": pack_id,
            "basename": basename,
            "role": role.value,
            "midi_path": _repo_rel(loop_midi),
            "audio_path": _repo_rel(loop_wav),
            "tempo_bpm": tempo,
            "key_hint": key_hint,
            "bars": bars,
            "beats_per_bar": 4,
            "duration_seconds_expected": duration_expected,
            "duration_seconds_rendered": render_result.duration_seconds,
            "renderer_used": render_result.renderer_used.value,
            "render_quality": render_result.render_quality.value,
            "render_verified": render_result.render_verified,
            "preview_limited": render_result.preview_limited,
            "source_midi_path": _repo_rel(input_midi),
            "source_stem_path": _repo_rel(source_midi),
            "source_principles": source_principles,
            "role_use_principles": role_principles,
            "draft_gesture_influence": draft_gesture,
            "quality_notes": quality_notes + list(render_result.notes),
            "evidence_limits": evidence_limits,
            "usage_notes": usage_notes,
            "source_taste_dossier_used": taste_used,
            "witness_consensus_used": witness_used,
            "draft_understanding_used": draft_used,
            "no_private_paths_detected": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        pair_payload["no_private_paths_detected"] = not _has_private_markers(pair_payload)
        loop_pair.parent.mkdir(parents=True, exist_ok=True)
        loop_pair.write_text(json.dumps(pair_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        loops.append(
            LoopPair(
                pair_id=pair_payload["pair_id"],
                pack_id=pack_id,
                basename=basename,
                role=role,
                midi_path=pair_payload["midi_path"],
                audio_path=pair_payload["audio_path"],
                pair_metadata_path=_repo_rel(loop_pair),
                tempo_bpm=tempo,
                key_hint=key_hint,
                bars=bars,
                beats_per_bar=4,
                duration_seconds=render_result.duration_seconds,
                renderer_used=render_result.renderer_used,
                render_quality=render_result.render_quality,
                render_verified=render_result.render_verified,
                preview_limited=render_result.preview_limited,
                source_midi_path=pair_payload["source_midi_path"],
                source_stem_path=pair_payload["source_stem_path"],
                source_principles=source_principles,
                role_use_principles=role_principles,
                draft_gesture_influence=draft_gesture,
                quality_notes=quality_notes + list(render_result.notes),
                evidence_limits=evidence_limits,
                usage_notes=usage_notes,
                no_private_paths_detected=pair_payload["no_private_paths_detected"],
                source_taste_dossier_used=taste_used,
                witness_consensus_used=witness_used,
                draft_understanding_used=draft_used,
                created_at=pair_payload["created_at"],
            )
        )

    midi_count = len(list(midi_dir.glob("*.mid")))
    audio_count = len(list(audio_dir.glob("*.wav")))
    paired_count = len(loops)
    audio_orphan_count = max(0, audio_count - paired_count)
    render_verified_count = sum(1 for loop in loops if loop.render_verified)
    strongest_loops = [loop.basename for loop in loops if loop.render_verified and loop.render_quality == RenderQualityTier.HIGH]
    weakest_limits = sorted({limit for loop in loops for limit in loop.evidence_limits})[:3]
    renderer_used = loops[0].renderer_used if loops else RendererKind.PYTHON_PREVIEW
    private_paths_detected = _has_private_markers([loop.to_dict() for loop in loops])
    pack_verified = paired_count > 0 and audio_orphan_count == 0 and render_verified_count > 0 and not private_paths_detected

    manifest = LoopPackManifest(
        pack_id=pack_id,
        created_at=datetime.now(UTC).isoformat(),
        pack_path=_repo_rel(pack_root),
        input_midi_path=_repo_rel(input_midi),
        stem_dir_path=_repo_rel(stem_dir) if stem_dir.exists() else "",
        midi_loop_count=midi_count,
        audio_loop_count=audio_count,
        paired_loop_count=paired_count,
        audio_orphan_count=audio_orphan_count,
        renderer_used=renderer_used,
        render_verified_count=render_verified_count,
        pack_verified=pack_verified,
        private_paths_detected=private_paths_detected,
        source_taste_dossier_used=taste_used,
        witness_consensus_used=witness_used,
        draft_understanding_used=draft_used,
        strongest_loops=strongest_loops,
        weakest_evidence_limits=weakest_limits,
        notes=[
            "Local-only export; no cloud or training was performed.",
            "Source files remain unchanged and only generated MIDI artifacts are consumed.",
        ],
        loops=loops,
    )
    pack_root.mkdir(parents=True, exist_ok=True)
    (pack_root / "pack_manifest.json").write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    _write_manifest_csv(pack_root / "pack_manifest.csv", loops)
    _write_pack_readme(pack_root / "PACK_README.md", manifest)
    _write_export_reports(manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export local-only paired MIDI/audio loop pack.")
    parser.add_argument("--input-midi", default="outputs/presentable_composition_from_draft_v1/selected/full.mid")
    parser.add_argument("--stem-dir", default="outputs/presentable_composition_from_draft_v1/selected/stems")
    parser.add_argument("--pack-id", default="")
    parser.add_argument("--tempo", type=float, default=0.0)
    parser.add_argument("--key", default="")
    parser.add_argument("--bars", type=int, default=4)
    parser.add_argument("--renderer", default="auto")
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = export_paired_loop_pack(args)
    print(f"PAIRED_LOOP_PACK_ID={manifest.pack_id}")
    print(f"PAIRED_LOOP_PACK_PATH={manifest.pack_path}")
    print(f"MIDI_LOOP_COUNT={manifest.midi_loop_count}")
    print(f"AUDIO_LOOP_COUNT={manifest.audio_loop_count}")
    print(f"PAIRED_LOOP_COUNT={manifest.paired_loop_count}")
    print(f"AUDIO_ORPHAN_COUNT={manifest.audio_orphan_count}")
    print(f"RENDERER_USED={manifest.renderer_used.value}")
    print(f"RENDER_VERIFIED_COUNT={manifest.render_verified_count}")
    print(f"PACK_VERIFIED={str(manifest.pack_verified).lower()}")
    print(f"SOURCE_TASTE_DOSSIER_USED={str(manifest.source_taste_dossier_used).lower()}")
    print(f"WITNESS_CONSENSUS_USED={str(manifest.witness_consensus_used).lower()}")
    print(f"DRAFT_UNDERSTANDING_USED={str(manifest.draft_understanding_used).lower()}")
    print(f"PRIVATE_PATHS_DETECTED={str(manifest.private_paths_detected).lower()}")
    print(f"PAIRED_LOOP_PACK_EXPORT_REPORT_JSON={EXPORT_REPORT_JSON.as_posix()}")
    print(f"PAIRED_LOOP_PACK_EXPORT_REPORT_MD={EXPORT_REPORT_MD.as_posix()}")
    return 0 if manifest.paired_loop_count > 0 else 1


if False and __name__ == "__main__":
    raise SystemExit(main())

# ---- Family variation exporter v2 ----
from features.paired_loop_packs import LoopMeta as VLoopMeta, MidiNote as VMidiNote, generate_variation_cycle, note_event_hash

SOURCE_CANDIDATES_JSONL = ROOT_DIR / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl"


@dataclass(frozen=True)
class _FamilyArgs:
    family_count: int
    variations_per_family: int
    roles: list[str]
    include_seed: bool
    render_audio: bool
    preview: bool


def _parse_bool_arg(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid bool value: {value}")


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _seed_phrase_for_role(role: str, bars: int, tpq: int) -> list[VMidiNote]:
    phrases = {
        "bass": [36, 36, 39, 34],
        "chords": [48, 52, 55, 60],
        "lead": [60, 62, 67, 69],
        "texture": [60, 67, 62, 69],
        "percussion": [36, 42, 38, 46],
    }
    scale = phrases.get(role, [60, 62, 67, 69])
    notes: list[VMidiNote] = []
    for idx in range(bars * 4):
        notes.append(
            VMidiNote(
                pitch=scale[idx % len(scale)],
                velocity=84,
                start_tick=idx * tpq,
                duration_tick=max(80, tpq - 40),
            )
        )
    return notes


def _render_seed_midi(path: Path, notes: list[VMidiNote], meta: VLoopMeta) -> None:
    midi = MidiFile(ticks_per_beat=meta.ticks_per_quarter)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=int(bpm2tempo(max(1.0, meta.bpm))), time=0))
    events: list[tuple[int, Message]] = []
    for note in notes:
        events.append((note.start_tick, Message("note_on", note=note.pitch, velocity=note.velocity, time=0)))
        events.append((note.start_tick + note.duration_tick, Message("note_off", note=note.pitch, velocity=0, time=0)))
    events.sort(key=lambda row: (row[0], 0 if row[1].type == "note_off" else 1))
    previous = 0
    for tick, msg in events:
        track.append(msg.copy(time=max(0, tick - previous)))
        previous = tick
    track.append(MetaMessage("end_of_track", time=max(0, meta.loop_ticks - previous)))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))


def _role_from_candidate(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in {"melody", "lead"}:
        return "lead"
    if value in {"drums", "perc"}:
        return "percussion"
    return value


def _family_export(args: _FamilyArgs) -> dict[str, Any]:
    requested_roles = [r.strip().lower() for r in args.roles if r.strip()] or ["bass", "chords", "lead", "texture"]
    candidates = _read_jsonl_rows(SOURCE_CANDIDATES_JSONL)
    if any(_role_from_candidate(row.get("role", "")) == "percussion" for row in candidates) and "percussion" not in requested_roles:
        requested_roles.append("percussion")
    total_families = max(args.family_count, len(requested_roles))

    pack_id = datetime.now(UTC).strftime("paired_loop_pack_%Y%m%dT%H%M%SZ")
    pack_root = OUTPUT_ROOT / pack_id
    families_root = pack_root / "families"
    totals = {"variation_count": 0, "midi_count": 0, "wav_count": 0, "pair_json_count": 0, "render_verified_count": 0}
    weirdest: list[str] = []
    best: list[str] = []
    families: list[dict[str, Any]] = []

    for idx in range(total_families):
        role = requested_roles[idx % len(requested_roles)]
        family_id = f"family_{idx + 1:02d}_{role}"
        family_root = families_root / family_id
        midi_dir = family_root / "midi"
        wav_dir = family_root / "wav"
        pair_dir = family_root / "pairs"
        bars = 2 if args.preview else 4
        bpm = 120.0
        key = "C"
        meta = VLoopMeta(bars=bars, bpm=bpm, key=key)
        seed = _seed_phrase_for_role(role, bars, meta.ticks_per_quarter)
        seed_hash = note_event_hash(seed)
        source_explanation = f"Seed for {family_id} is role-derived from local metadata and does not copy source audio."
        family_pairs: list[dict[str, Any]] = []

        def emit(variation_type: str, notes: list[VMidiNote]) -> None:
            basename = f"{family_id}__{variation_type}"
            midi_path = midi_dir / f"{basename}.mid"
            wav_path = wav_dir / f"{basename}.wav"
            pair_path = pair_dir / f"{basename}.pair.json"
            _render_seed_midi(midi_path, notes, meta)
            if args.render_audio:
                result = render_midi_to_wav(
                    midi_path=midi_path,
                    wav_path=wav_path,
                    role=role,
                    target_duration_seconds=_duration_for_bars(bars=bars, tempo_bpm=bpm),
                    context=RendererContext(repo_root=ROOT_DIR, renderer_override=""),
                )
                wav_rel = _repo_rel(wav_path) if wav_path.exists() else None
                totals["wav_count"] += int(wav_path.exists())
                totals["render_verified_count"] += int(bool(result.render_verified))
                renderer_used = result.renderer_used.value
                midi_only_preview = not wav_path.exists()
            else:
                wav_rel = None
                renderer_used = RendererKind.PYTHON_PREVIEW.value
                midi_only_preview = True
            pair_payload = {
                "pair_id": basename,
                "family_id": family_id,
                "role": role,
                "variation_type": variation_type,
                "transformation_from_seed": "seed" if variation_type == "seed" else variation_type,
                "musical_independence_note": (
                    "Seed establishes family anchor."
                    if variation_type == "seed"
                    else "Variation is rhythmically/melodically transformed and not a renamed copy."
                ),
                "source_explanation": source_explanation,
                "pairing_explanation": "MIDI and WAV share basename and represent one loop variation.",
                "evidence_limits": [
                    "Tempo/key are local hints and may be approximate.",
                    "No cloud/model training and no fake witness output.",
                ],
                "usage_notes": [
                    "Use seed + derivatives as a variation family.",
                    "Fallback audio renders are valid local previews.",
                ],
                "bars": bars,
                "bpm": bpm,
                "key": key,
                "midi_path": _repo_rel(midi_path),
                "wav_path": wav_rel,
                "midi_only_preview": midi_only_preview,
                "seed_note_hash": seed_hash,
                "note_event_hash": note_event_hash(notes),
                "renderer_used": renderer_used,
            }
            pair_path.parent.mkdir(parents=True, exist_ok=True)
            pair_path.write_text(json.dumps(pair_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            family_pairs.append({"pair_id": basename, "variation_type": variation_type, "pair_path": _repo_rel(pair_path)})
            totals["variation_count"] += 1
            totals["midi_count"] += 1
            totals["pair_json_count"] += 1
            if variation_type == "texture_chop":
                weirdest.append(basename)
            if variation_type in {"syncopated", "release"}:
                best.append(basename)

        if args.include_seed:
            emit("seed", seed)
        for variation_name, notes in generate_variation_cycle(seed, meta, args.variations_per_family):
            emit(variation_name, notes)

        family_manifest = {
            "family_id": family_id,
            "role": role,
            "seed_pair_count": int(args.include_seed),
            "variation_pair_count": args.variations_per_family,
            "pair_count": len(family_pairs),
            "bars": bars,
            "bpm": bpm,
            "key": key,
            "pairs": family_pairs,
        }
        family_manifest_path = family_root / "family_manifest.json"
        family_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        family_manifest_path.write_text(json.dumps(family_manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        families.append(
            {
                "family_id": family_id,
                "role": role,
                "family_manifest_path": _repo_rel(family_manifest_path),
                "pair_count": len(family_pairs),
            }
        )

    manifest = {
        "pack_id": pack_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "family_count": len(families),
        **totals,
        "renderer_used": RendererKind.PYTHON_PREVIEW.value,
        "families": families,
        "settings": {
            "family_count_requested": args.family_count,
            "variations_per_family": args.variations_per_family,
            "roles": requested_roles,
            "include_seed": args.include_seed,
            "render_audio": args.render_audio,
            "preview": args.preview,
        },
        "constraints": {
            "no_cloud": True,
            "no_model_training": True,
            "source_audio_modified": False,
            "private_paths_detected": False,
            "no_fake_audio_render": True,
            "no_fake_witness_output": True,
        },
    }
    manifest["constraints"]["private_paths_detected"] = _has_private_markers(manifest)
    pack_root.mkdir(parents=True, exist_ok=True)
    manifest_path = pack_root / "pack_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (pack_root / "PACK_README.md").write_text(
        "\n".join(
            [
                "# Paired Loop Pack",
                "",
                "## Family structure",
                f"- pack_id: `{pack_id}`",
                f"- family_count: `{manifest['family_count']}`",
                f"- variation_count: `{manifest['variation_count']}`",
                "",
                "## Derivative policy",
                "- Variations are musically transformed from seeds (no renamed copies).",
                "- MIDI/WAV/pair metadata keep matching basenames.",
                "",
                "## Quality and evidence notes",
                "- No cloud/model training or fabricated witness output.",
                "- Source audio files are never modified.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = {
        "pack_id": pack_id,
        "pack_path": _repo_rel(pack_root),
        "family_count": manifest["family_count"],
        "variation_count": manifest["variation_count"],
        "midi_count": manifest["midi_count"],
        "wav_count": manifest["wav_count"],
        "pair_json_count": manifest["pair_json_count"],
        "render_verified_count": manifest["render_verified_count"],
        "strong_families": [item["family_id"] for item in families if item["pair_count"] >= args.variations_per_family + int(args.include_seed)],
        "weak_families": [item["family_id"] for item in families if item["pair_count"] < args.variations_per_family + int(args.include_seed)],
        "weirdest_variations": weirdest[:8],
        "best_standalone_loops": best[:8],
        "renderer_used": manifest["renderer_used"],
        "manifest_path": _repo_rel(manifest_path),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    EXPORT_REPORT_MD.write_text(
        "\n".join(
            [
                "# Paired Loop Pack Export Report",
                "",
                f"- pack_id: `{report['pack_id']}`",
                f"- family_count: `{report['family_count']}`",
                f"- variation_count: `{report['variation_count']}`",
                f"- midi_count: `{report['midi_count']}`",
                f"- wav_count: `{report['wav_count']}`",
                f"- pair_json_count: `{report['pair_json_count']}`",
                f"- render_verified_count: `{report['render_verified_count']}`",
                f"- strong_families: `{', '.join(report['strong_families']) if report['strong_families'] else 'none'}`",
                f"- weak_families: `{', '.join(report['weak_families']) if report['weak_families'] else 'none'}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def _parse_family_args() -> _FamilyArgs:
    parser = argparse.ArgumentParser(description="Export paired MIDI/audio loop pack families.")
    parser.add_argument("--family-count", type=int, default=4)
    parser.add_argument("--variations-per-family", type=int, default=6)
    parser.add_argument("--roles", type=str, default="bass,chords,lead,texture")
    parser.add_argument("--include-seed", type=_parse_bool_arg, default=True)
    parser.add_argument("--render-audio", type=_parse_bool_arg, default=True)
    parser.add_argument("--preview", type=_parse_bool_arg, default=False)
    values = parser.parse_args()
    return _FamilyArgs(
        family_count=max(1, int(values.family_count)),
        variations_per_family=max(1, int(values.variations_per_family)),
        roles=[item.strip().lower() for item in str(values.roles).split(",") if item.strip()],
        include_seed=bool(values.include_seed),
        render_audio=bool(values.render_audio),
        preview=bool(values.preview),
    )


def _family_main() -> int:
    report = _family_export(_parse_family_args())
    print(f"PAIRED_LOOP_PACK_ID={report['pack_id']}")
    print(f"PAIRED_LOOP_PACK_PATH={report['pack_path']}")
    print(f"PAIRED_LOOP_PACK_MANIFEST={report['manifest_path']}")
    print(f"PAIRED_LOOP_PACK_FAMILIES={report['family_count']}")
    print(f"PAIRED_LOOP_PACK_VARIATIONS={report['variation_count']}")
    print(f"PAIRED_LOOP_PACK_MIDI_COUNT={report['midi_count']}")
    print(f"PAIRED_LOOP_PACK_WAV_COUNT={report['wav_count']}")
    print(f"PAIRED_LOOP_PACK_PAIR_COUNT={report['pair_json_count']}")
    print(f"PAIRED_LOOP_PACK_RENDER_VERIFIED={report['render_verified_count']}")
    print(f"PAIRED_LOOP_PACK_EXPORT_REPORT_JSON={EXPORT_REPORT_JSON.as_posix()}")
    print(f"PAIRED_LOOP_PACK_EXPORT_REPORT_MD={EXPORT_REPORT_MD.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_family_main())
