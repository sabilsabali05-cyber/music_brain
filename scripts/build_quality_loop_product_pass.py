from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

ROOT_DIR = Path(__file__).resolve().parent.parent
RANKED_LOOPS_JSONL = ROOT_DIR / "datasets" / "source_loop_extraction" / "ranked_extracted_source_loops.jsonl"
LOCAL_PACK_ROOT = ROOT_DIR / "local_quality_loop_packs" / "quality_loop_pack_v1"
REPORT_ROOT = ROOT_DIR / "reports" / "quality_loop_product"
CLIP_COUNT_TARGET = 10
MIN_CLIPS = 8
MAX_CLIPS = 12
MIDI_IDEA_FILES = [
    "drums_overlay.mid",
    "bass_idea.mid",
    "chord_idea.mid",
    "lead_motif.mid",
    "continuation.mid",
    "mutation.mid",
    "section_b.mid",
]
PRIVATE_MARKERS = ("C:\\Users\\", "C:/Users/", "/Users/")


@dataclass(frozen=True)
class ToolStatus:
    available: bool
    reason: str


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _load_efficiency_mode_policy() -> dict[str, Any]:
    path = ROOT_DIR / "reports" / "product_core" / "efficiency_mode_policy.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()


def _redacted_source_token(row: dict[str, Any]) -> str:
    source_id = str(row.get("source_id", "unknown"))
    path_hash = str(row.get("path_hash", "missing"))
    digest = hashlib.sha256(f"{source_id}|{path_hash}".encode("utf-8")).hexdigest()
    return digest[:20]


def _resolve_source_audio_path(row: dict[str, Any]) -> Path | None:
    local_rel = str(row.get("local_clip_relpath", "")).strip()
    if local_rel:
        local_candidate = ROOT_DIR / local_rel
        if local_candidate.exists():
            return local_candidate
    redacted = str(row.get("source_redacted_path", "")).strip()
    if not redacted:
        return None
    guessed = Path(redacted.replace("<PRIVATE_LOCAL_PATH>", "C:\\Users"))
    if guessed.exists():
        return guessed
    return None


def _extract_wav_loop(source_wav: Path, target_wav: Path, *, start_seconds: float, duration_seconds: float) -> bool:
    if source_wav.suffix.lower() != ".wav":
        return False
    try:
        with wave.open(str(source_wav), "rb") as src:
            rate = src.getframerate()
            channels = src.getnchannels()
            sample_width = src.getsampwidth()
            total_frames = src.getnframes()
            start_frame = max(0, int(max(0.0, start_seconds) * rate))
            frame_count = int(max(0.5, duration_seconds) * rate)
            if start_frame >= total_frames:
                return False
            frame_count = max(1, min(frame_count, total_frames - start_frame))
            src.setpos(start_frame)
            frames = src.readframes(frame_count)
        target_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(target_wav), "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(sample_width)
            out.setframerate(rate)
            out.writeframes(frames)
        return True
    except Exception:  # noqa: BLE001
        return False


def _clip_quality_score(row: dict[str, Any]) -> float:
    rank_score = float(row.get("rank_score") or 0.0)
    loopability = float(row.get("loopability_score") or 0.0)
    rhythm_density = float(row.get("rhythm_density_score") or 0.0)
    tempo_confidence = float(row.get("tempo_confidence") or 0.0)
    duration_seconds = float(row.get("duration_seconds") or 0.0)
    duration_bonus = 1.0 if 1.2 <= duration_seconds <= 8.5 else 0.65
    return (
        rank_score * 0.45
        + loopability * 0.25
        + min(1.0, rhythm_density) * 0.15
        + min(1.0, tempo_confidence) * 0.10
        + duration_bonus * 0.05
    )


def _detect_basic_pitch() -> ToolStatus:
    try:
        from basic_pitch.inference import predict  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return ToolStatus(available=False, reason=f"import_failed:{exc.__class__.__name__}")
    return ToolStatus(available=True, reason="import_ok")


def _detect_demucs() -> ToolStatus:
    try:
        import demucs  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return ToolStatus(available=False, reason=f"import_failed:{exc.__class__.__name__}")
    return ToolStatus(available=True, reason="import_ok_but_skipped_for_runtime")


def _try_basic_pitch(wav_path: Path, out_dir: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": "unavailable",
        "notes_count": 0,
        "midi_path": "",
        "error": "",
    }
    basic_pitch_status = _detect_basic_pitch()
    if not basic_pitch_status.available:
        summary["error"] = basic_pitch_status.reason
        return summary

    try:
        from basic_pitch.inference import predict

        model_output, midi_data, note_events = predict(str(wav_path))
        out_dir.mkdir(parents=True, exist_ok=True)
        midi_path = out_dir / "basic_pitch.mid"
        midi_data.write(str(midi_path))
        parsed = MidiFile(str(midi_path))
        note_count = 0
        for track in parsed.tracks:
            for msg in track:
                if msg.type == "note_on" and int(getattr(msg, "velocity", 0)) > 0:
                    note_count += 1
        summary.update(
            {
                "status": "ok",
                "notes_count": int(note_count),
                "midi_path": _safe_rel(midi_path),
                "error": "",
                "raw_note_events": int(len(note_events) if isinstance(note_events, list) else note_count),
                "frames_in_model_output": int(getattr(model_output, "shape", [0])[0] if model_output is not None else 0),
            }
        )
        return summary
    except Exception as exc:  # noqa: BLE001
        summary["status"] = "failed"
        summary["error"] = f"{exc.__class__.__name__}: {exc}"
        return summary


def _write_midi_idea(path: Path, *, bpm: float, note_seed: int, bars: int, channel: int, program: int) -> int:
    midi = MidiFile(ticks_per_beat=480)
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=int(bpm2tempo(max(45.0, min(195.0, bpm)))), time=0))
    if channel != 9:
        track.append(Message("program_change", program=program % 128, channel=channel, time=0))

    events: list[tuple[int, Message]] = []
    beats = max(4, bars * 4)
    complexity = max(1, min(4, (note_seed % 4) + 1))
    for beat in range(beats):
        if ((beat + note_seed) % (3 + complexity)) == 0:
            continue
        start_tick = beat * 480
        length = 240 if channel == 9 else (180 + ((beat + note_seed) % 220))
        pitch_center = 36 if channel == 9 else 48 + ((note_seed + beat) % 16)
        velocity = 62 + ((note_seed + beat * 11) % 50)
        pitch = max(24, min(96, pitch_center))
        events.append((start_tick, Message("note_on", note=pitch, velocity=velocity, channel=channel, time=0)))
        events.append((start_tick + length, Message("note_off", note=pitch, velocity=0, channel=channel, time=0)))
    if not events:
        events.append((0, Message("note_on", note=60, velocity=80, channel=channel, time=0)))
        events.append((240, Message("note_off", note=60, velocity=0, channel=channel, time=0)))
    events.sort(key=lambda item: (item[0], 0 if item[1].type == "note_off" else 1))
    prev = 0
    note_on_count = 0
    for tick, msg in events:
        msg.time = max(0, tick - prev)
        prev = tick
        if msg.type == "note_on" and msg.velocity > 0:
            note_on_count += 1
        track.append(msg)
    track.append(MetaMessage("end_of_track", time=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(str(path))
    _ = MidiFile(str(path))
    return note_on_count


def _score_midi_idea(filename: str, note_count: int) -> float:
    density_target = {
        "drums_overlay.mid": 14,
        "bass_idea.mid": 9,
        "chord_idea.mid": 8,
        "lead_motif.mid": 10,
        "continuation.mid": 9,
        "mutation.mid": 11,
        "section_b.mid": 12,
    }.get(filename, 10)
    distance = abs(note_count - density_target)
    return max(0.0, 1.0 - (distance / max(4.0, float(density_target))))


def _markdown_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none"


def run_quality_pass() -> dict[str, Any]:
    efficiency_policy = _load_efficiency_mode_policy()
    privacy_scan_blocks_normal_dev = bool(efficiency_policy.get("privacy_scan_blocks_normal_dev", True))
    privacy_scan_blocks_release = bool(efficiency_policy.get("privacy_scan_blocks_release", True))
    rows = _read_jsonl(RANKED_LOOPS_JSONL)
    ranked = []
    for row in rows:
        if not bool(row.get("authorized_for_buddy_generation", False)):
            continue
        if not bool(row.get("local_audio_clip_exists", False)):
            continue
        source_path = _resolve_source_audio_path(row)
        if source_path is None:
            continue
        ranked.append((row, _clip_quality_score(row)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    selected_rows = ranked[:CLIP_COUNT_TARGET]

    if LOCAL_PACK_ROOT.exists():
        shutil.rmtree(LOCAL_PACK_ROOT)
    LOCAL_PACK_ROOT.mkdir(parents=True, exist_ok=True)
    clips_root = LOCAL_PACK_ROOT / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)

    selection_rows: list[dict[str, Any]] = []
    clip_manifests: list[dict[str, Any]] = []
    basic_pitch_successes = 0
    demucs_successes = 0
    midi_files_created = 0
    usable_midi_ideas = 0
    all_private_scan_payloads: list[Any] = []

    for idx, (row, score) in enumerate(selected_rows, start=1):
        clip_id = str(row.get("clip_id", f"clip_{idx:03d}"))
        bars = int(row.get("bars_target") or 4)
        bpm = float(row.get("tempo_bpm_estimate") or 92.0)
        source_path = _resolve_source_audio_path(row)
        if source_path is None:
            continue
        clip_dir = clips_root / f"clip_{idx:03d}_{clip_id}"
        clip_dir.mkdir(parents=True, exist_ok=True)
        clip_source_wav = clip_dir / "source_loop.wav"
        start_seconds = float(row.get("start_seconds") or 0.0)
        duration_seconds = float(row.get("duration_seconds") or 4.0)
        extracted = _extract_wav_loop(
            source_path,
            clip_source_wav,
            start_seconds=start_seconds,
            duration_seconds=duration_seconds,
        )
        if not extracted:
            if source_path.suffix.lower() == ".wav":
                shutil.copy2(source_path, clip_source_wav)
            else:
                continue

        redacted_token = _redacted_source_token(row)
        analysis_payload = {
            "clip_id": clip_id,
            "clip_folder": _safe_rel(clip_dir),
            "source_identity_redacted": redacted_token,
            "source_id_hash": hashlib.sha256(str(row.get("source_id", "")).encode("utf-8")).hexdigest()[:16],
            "path_hash": str(row.get("path_hash", "")),
            "quality_score": round(score, 6),
            "rank_score": float(row.get("rank_score") or 0.0),
            "loopability_score": float(row.get("loopability_score") or 0.0),
            "rhythm_density_score": float(row.get("rhythm_density_score") or 0.0),
            "tempo_bpm_estimate": bpm,
            "tempo_confidence": float(row.get("tempo_confidence") or 0.0),
            "duration_seconds": float(row.get("duration_seconds") or 0.0),
            "bars_target": bars,
            "source_resolution": {
                "used_local_clip_cache": str(row.get("local_clip_relpath", "")).strip() and (ROOT_DIR / str(row.get("local_clip_relpath"))).exists(),
                "used_redacted_source_guess": str(source_path).lower().startswith("c:\\users\\"),
                "loop_extracted_from_source_audio": extracted,
            },
            "texture_role_hint": str(row.get("texture_role_hint", "unknown")),
            "energy_role_hint": str(row.get("energy_role_hint", "unknown")),
        }
        (clip_dir / "analysis.json").write_text(json.dumps(analysis_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        clip_notes = [
            f"# Clip Notes: {clip_id}",
            "",
            f"- source_identity_redacted: `{redacted_token}`",
            f"- quality_score: `{analysis_payload['quality_score']}`",
            f"- bpm_estimate: `{round(bpm, 3)}`",
            f"- bars_target: `{bars}`",
            "- selection_basis: authorized local cache + quality-focused rubric",
            "- privacy: no absolute local path persisted in committed reports",
        ]
        (clip_dir / "clip_notes.md").write_text("\n".join(clip_notes).rstrip() + "\n", encoding="utf-8")

        transcription_dir = clip_dir / "transcription"
        transcription_dir.mkdir(parents=True, exist_ok=True)
        basic_pitch_summary = _try_basic_pitch(clip_source_wav, transcription_dir)
        if basic_pitch_summary["status"] == "ok":
            basic_pitch_successes += 1
        (transcription_dir / "basic_pitch_summary.json").write_text(
            json.dumps(basic_pitch_summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )

        stems_dir = clip_dir / "stems"
        stems_dir.mkdir(parents=True, exist_ok=True)
        demucs_status = _detect_demucs()
        if demucs_status.available:
            stem_summary = {
                "status": "skipped",
                "reason": "demucs importable but skipped as not reasonable for this bounded local quality pass runtime",
                "stems_rendered": [],
            }
        else:
            stem_summary = {
                "status": "unavailable",
                "reason": demucs_status.reason,
                "stems_rendered": [],
            }
        (stems_dir / "stem_summary.json").write_text(json.dumps(stem_summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        if stem_summary["status"] == "ok":
            demucs_successes += 1

        midi_dir = clip_dir / "midi_ideas"
        midi_dir.mkdir(parents=True, exist_ok=True)
        midi_scores: list[dict[str, Any]] = []
        seed_value = int(hashlib.sha256(clip_id.encode("utf-8")).hexdigest()[:8], 16)
        for idea_index, idea_name in enumerate(MIDI_IDEA_FILES):
            idea_path = midi_dir / idea_name
            if "drums" in idea_name:
                channel = 9
                program = 0
            elif "bass" in idea_name:
                channel = 1
                program = 34
            elif "chord" in idea_name:
                channel = 2
                program = 48
            elif "lead" in idea_name:
                channel = 3
                program = 80
            elif "section" in idea_name:
                channel = 4
                program = 52
            elif "mutation" in idea_name:
                channel = 5
                program = 60
            else:
                channel = 6
                program = 72
            note_count = _write_midi_idea(
                idea_path,
                bpm=bpm,
                note_seed=seed_value + (idea_index * 7),
                bars=max(2, bars),
                channel=channel,
                program=program,
            )
            quality = _score_midi_idea(idea_name, note_count)
            parseable = True
            score_row = {
                "file": idea_name,
                "path": _safe_rel(idea_path),
                "note_count": note_count,
                "parseable": parseable,
                "quality_score": round(quality, 6),
                "tags": [],
            }
            if quality >= 0.55:
                usable_midi_ideas += 1
                score_row["tags"].append("usable")
            midi_scores.append(score_row)
            midi_files_created += 1

        midi_scores_sorted = sorted(midi_scores, key=lambda item: item["quality_score"], reverse=True)
        best = midi_scores_sorted[0]["file"]
        safest = sorted(midi_scores, key=lambda item: (item["note_count"], -item["quality_score"]))[0]["file"]
        weirdest_useful = sorted(midi_scores, key=lambda item: (abs(item["note_count"] - 11), -item["quality_score"]))[0]["file"]
        midi_summary = {
            "clip_id": clip_id,
            "best_idea": best,
            "safest_idea": safest,
            "weirdest_useful_idea": weirdest_useful,
            "ideas": midi_scores,
        }
        (midi_dir / "midi_scores.json").write_text(json.dumps(midi_summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        reaper_manifest = {
            "clip_id": clip_id,
            "source_loop_wav": _safe_rel(clip_source_wav),
            "midi_ideas": [_safe_rel(midi_dir / name) for name in MIDI_IDEA_FILES],
            "transcription_midi": basic_pitch_summary.get("midi_path", ""),
            "stems_summary": _safe_rel(stems_dir / "stem_summary.json"),
            "drag_order": [
                _safe_rel(clip_source_wav),
                _safe_rel(midi_dir / "drums_overlay.mid"),
                _safe_rel(midi_dir / "bass_idea.mid"),
                _safe_rel(midi_dir / "chord_idea.mid"),
                _safe_rel(midi_dir / "lead_motif.mid"),
            ],
        }
        (clip_dir / "reaper_manifest.json").write_text(json.dumps(reaper_manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        clip_manifest = {
            "clip_folder": _safe_rel(clip_dir),
            "clip_id": clip_id,
            "quality_score": round(score, 6),
            "source_identity_redacted": redacted_token,
            "analysis_path": _safe_rel(clip_dir / "analysis.json"),
            "notes_path": _safe_rel(clip_dir / "clip_notes.md"),
            "transcription_summary_path": _safe_rel(transcription_dir / "basic_pitch_summary.json"),
            "stems_summary_path": _safe_rel(stems_dir / "stem_summary.json"),
            "midi_scores_path": _safe_rel(midi_dir / "midi_scores.json"),
            "reaper_manifest_path": _safe_rel(clip_dir / "reaper_manifest.json"),
            "best_midi_idea": best,
            "safest_midi_idea": safest,
            "weirdest_useful_midi_idea": weirdest_useful,
        }
        clip_manifests.append(clip_manifest)
        selection_rows.append(
            {
                "clip_id": clip_id,
                "clip_folder": _safe_rel(clip_dir),
                "rank_score": float(row.get("rank_score") or 0.0),
                "quality_score": round(score, 6),
                "authorized_for_buddy_generation": bool(row.get("authorized_for_buddy_generation", False)),
                "local_audio_clip_exists": bool(row.get("local_audio_clip_exists", False)),
                "source_identity_redacted": redacted_token,
            }
        )
        all_private_scan_payloads.append(
            {
                "analysis": analysis_payload,
                "clip_manifest": clip_manifest,
                "midi_summary": midi_summary,
                "reaper_manifest": reaper_manifest,
            }
        )

    top_three = sorted(clip_manifests, key=lambda row: row["quality_score"], reverse=True)[:3]
    best_clip = top_three[0] if top_three else {}
    best_midi_idea = best_clip.get("best_midi_idea", "")
    pack_manifest = {
        "pack_id": "quality_loop_pack_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_ranked_manifest": _safe_rel(RANKED_LOOPS_JSONL),
        "selected_clip_count": len(clip_manifests),
        "clip_target_count": CLIP_COUNT_TARGET,
        "clip_manifests": clip_manifests,
        "top_3_clip_folders": [row["clip_folder"] for row in top_three],
        "best_overall_loop": best_clip.get("clip_folder", ""),
        "best_midi_idea": best_midi_idea,
        "basic_pitch_successes": basic_pitch_successes,
        "demucs_successes": demucs_successes,
        "midi_files_created": midi_files_created,
        "usable_midi_ideas": usable_midi_ideas,
    }
    (LOCAL_PACK_ROOT / "pack_manifest.json").write_text(json.dumps(pack_manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    selection_audit = {
        "generated_at": datetime.now(UTC).isoformat(),
        "selection_count": len(selection_rows),
        "selection_rows": selection_rows,
        "rubric_weights": {
            "rank_score": 0.45,
            "loopability_score": 0.25,
            "rhythm_density_score": 0.15,
            "tempo_confidence": 0.10,
            "duration_bonus": 0.05,
        },
    }
    (LOCAL_PACK_ROOT / "selection_audit.json").write_text(json.dumps(selection_audit, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (LOCAL_PACK_ROOT / "selection_audit.md").write_text(
        "\n".join(
            [
                "# Selection Audit",
                "",
                f"- selected_count: `{selection_audit['selection_count']}`",
                f"- source_manifest: `{selection_audit['source_manifest'] if 'source_manifest' in selection_audit else _safe_rel(RANKED_LOOPS_JSONL)}`",
                "",
                "## Selected clips",
                _markdown_list([f"`{row['clip_folder']}` score={row['quality_score']}" for row in selection_rows]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    midi_score_rows: list[str] = []
    midi_score_json_rows: list[dict[str, Any]] = []
    for clip in clip_manifests:
        midi_summary_path = ROOT_DIR / clip["midi_scores_path"]
        summary = json.loads(midi_summary_path.read_text(encoding="utf-8"))
        for idea in summary.get("ideas", []):
            midi_score_json_rows.append(
                {
                    "clip_id": clip["clip_id"],
                    "clip_folder": clip["clip_folder"],
                    "file": idea["file"],
                    "quality_score": idea["quality_score"],
                    "parseable": idea["parseable"],
                    "usable": "usable" in idea["tags"],
                }
            )
            midi_score_rows.append(
                f"- `{clip['clip_id']}` `{idea['file']}` score={idea['quality_score']} parseable={idea['parseable']} usable={'usable' in idea['tags']}"
            )
    midi_scores_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rows": midi_score_json_rows,
        "usable_midi_ideas": usable_midi_ideas,
        "midi_files_created": midi_files_created,
    }
    (LOCAL_PACK_ROOT / "midi_quality_scores.json").write_text(
        json.dumps(midi_scores_payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (LOCAL_PACK_ROOT / "midi_quality_scores.md").write_text(
        "\n".join(["# MIDI Quality Scores", "", *midi_score_rows[:500]]) + "\n",
        encoding="utf-8",
    )

    audition_lines = [
        "# Audition Guide",
        "",
        "## Top 3 loops",
        _markdown_list([f"`{row['clip_folder']}`" for row in top_three]),
        "",
        "## Suggested audition order",
        "1. source_loop.wav",
        "2. drums_overlay.mid + bass_idea.mid",
        "3. chord_idea.mid + lead_motif.mid",
        "4. continuation.mid then mutation.mid",
        "5. section_b.mid",
    ]
    (LOCAL_PACK_ROOT / "audition_guide.md").write_text("\n".join(audition_lines).rstrip() + "\n", encoding="utf-8")

    private_paths_detected = any(marker in json.dumps(all_private_scan_payloads, ensure_ascii=True) for marker in PRIVATE_MARKERS)
    reaper_ready = bool(clip_manifests) and all((ROOT_DIR / clip["reaper_manifest_path"]).exists() for clip in clip_manifests)
    gate = {
        "pack_id": "quality_loop_pack_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "efficiency_mode": {
            "privacy_scan_blocks_normal_dev": privacy_scan_blocks_normal_dev,
            "privacy_scan_blocks_release": privacy_scan_blocks_release,
            "privacy_scan_run_mode": "commit_or_release_only",
        },
        "thresholds": {
            "selected_clip_count_min": MIN_CLIPS,
            "selected_clip_count_max": MAX_CLIPS,
            "midi_files_expected": len(clip_manifests) * len(MIDI_IDEA_FILES),
            "usable_midi_min_ratio": 0.7,
            "reaper_ready_required": True,
            "private_paths_detected_required": False,
        },
        "actuals": {
            "selected_clip_count": len(clip_manifests),
            "midi_files_created": midi_files_created,
            "usable_midi_ideas": usable_midi_ideas,
            "usable_midi_ratio": round(usable_midi_ideas / max(1, midi_files_created), 6),
            "reaper_ready": reaper_ready,
            "private_paths_detected": private_paths_detected,
            "basic_pitch_successes": basic_pitch_successes,
            "demucs_successes": demucs_successes,
        },
    }
    gate["pack_passed"] = (
        MIN_CLIPS <= gate["actuals"]["selected_clip_count"] <= MAX_CLIPS
        and gate["actuals"]["midi_files_created"] == gate["thresholds"]["midi_files_expected"]
        and gate["actuals"]["usable_midi_ratio"] >= gate["thresholds"]["usable_midi_min_ratio"]
        and gate["actuals"]["reaper_ready"]
        and not gate["actuals"]["private_paths_detected"]
    )
    gate["blockers"] = []
    if basic_pitch_successes == 0:
        gate["blockers"].append("basic_pitch unavailable_or_failed_for_all_clips")
    if demucs_successes == 0:
        gate["blockers"].append("demucs unavailable_or_skipped")

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_payload = {
        "pack_manifest_path": _safe_rel(LOCAL_PACK_ROOT / "pack_manifest.json"),
        "selection_audit_path": _safe_rel(LOCAL_PACK_ROOT / "selection_audit.json"),
        "midi_quality_scores_path": _safe_rel(LOCAL_PACK_ROOT / "midi_quality_scores.json"),
        "audition_guide_path": _safe_rel(LOCAL_PACK_ROOT / "audition_guide.md"),
        "top_3_clip_folders": [row["clip_folder"] for row in top_three],
        "best_overall_loop": best_clip.get("clip_folder", ""),
        "best_midi_idea": best_midi_idea,
        "basic_pitch_successes": basic_pitch_successes,
        "demucs_successes": demucs_successes,
        "midi_files_created": midi_files_created,
        "usable_midi_ideas": usable_midi_ideas,
        "reaper_ready": reaper_ready,
        "private_paths_detected": private_paths_detected,
        "pack_passed": gate["pack_passed"],
        "blockers": gate["blockers"],
        "privacy_scan_run_mode": "commit_or_release_only",
        "privacy_scan_blocking_local_dev": privacy_scan_blocks_normal_dev,
        "privacy_scan_blocking_release": privacy_scan_blocks_release,
    }
    (REPORT_ROOT / "quality_loop_pack_v1_report.json").write_text(
        json.dumps(report_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (REPORT_ROOT / "quality_loop_pack_v1_report.md").write_text(
        "\n".join(
            [
                "# Quality Loop Pack v1 Report",
                "",
                f"- pack_manifest_path: `{report_payload['pack_manifest_path']}`",
                f"- top_3_clip_folders: `{', '.join(report_payload['top_3_clip_folders'])}`",
                f"- best_overall_loop: `{report_payload['best_overall_loop']}`",
                f"- best_midi_idea: `{report_payload['best_midi_idea']}`",
                f"- basic_pitch_successes: `{report_payload['basic_pitch_successes']}`",
                f"- demucs_successes: `{report_payload['demucs_successes']}`",
                f"- midi_files_created: `{report_payload['midi_files_created']}`",
                f"- usable_midi_ideas: `{report_payload['usable_midi_ideas']}`",
                f"- reaper_ready: `{report_payload['reaper_ready']}`",
                f"- private_paths_detected: `{report_payload['private_paths_detected']}`",
                f"- pack_passed: `{report_payload['pack_passed']}`",
                "",
                "## Blockers",
                _markdown_list(report_payload["blockers"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (REPORT_ROOT / "quality_loop_pack_v1_gate.json").write_text(json.dumps(gate, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (REPORT_ROOT / "quality_loop_pack_v1_gate.md").write_text(
        "\n".join(
            [
                "# Quality Loop Pack v1 Gate",
                "",
                f"- pack_passed: `{gate['pack_passed']}`",
                f"- selected_clip_count: `{gate['actuals']['selected_clip_count']}`",
                f"- midi_files_created: `{gate['actuals']['midi_files_created']}`",
                f"- usable_midi_ratio: `{gate['actuals']['usable_midi_ratio']}`",
                f"- reaper_ready: `{gate['actuals']['reaper_ready']}`",
                f"- private_paths_detected: `{gate['actuals']['private_paths_detected']}`",
                "",
                "## Blockers",
                _markdown_list(gate["blockers"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "pack_manifest": pack_manifest,
        "report": report_payload,
        "gate": gate,
        "local_pack_folder": _safe_rel(LOCAL_PACK_ROOT),
    }


def main() -> int:
    payload = run_quality_pass()
    report = payload["report"]
    gate = payload["gate"]
    print(f"LOCAL_PACK_FOLDER={payload['local_pack_folder']}")
    print(f"PACK_PASSED={str(gate['pack_passed']).lower()}")
    print(f"TOP_3={','.join(report['top_3_clip_folders'])}")
    print(f"BEST_OVERALL_LOOP={report['best_overall_loop']}")
    print(f"BEST_MIDI_IDEA={report['best_midi_idea']}")
    print(f"BASICPITCH_SUCCESSES={report['basic_pitch_successes']}")
    print(f"DEMUCS_SUCCESSES={report['demucs_successes']}")
    print(f"MIDI_FILES_CREATED={report['midi_files_created']}")
    print(f"USABLE_MIDI_IDEAS={report['usable_midi_ideas']}")
    print(f"REAPER_READY={str(report['reaper_ready']).lower()}")
    print(f"PRIVATE_PATHS_DETECTED={str(report['private_paths_detected']).lower()}")
    print(f"REPORT_JSON={_safe_rel(REPORT_ROOT / 'quality_loop_pack_v1_report.json')}")
    print(f"GATE_JSON={_safe_rel(REPORT_ROOT / 'quality_loop_pack_v1_gate.json')}")
    return 0 if bool(gate.get("pack_passed", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
