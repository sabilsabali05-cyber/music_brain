from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import ExtractedSourceLoop

FFPROBE_CMD = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format"]
FFMPEG_CMD = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]


@dataclass(frozen=True)
class WitnessAvailability:
    available: list[str]
    unavailable: list[str]


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
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _load_path_map(local_path_map_path: Path) -> dict[str, str]:
    payload = _read_json(local_path_map_path)
    rows = payload.get("path_map", [])
    if not isinstance(rows, list):
        return {}
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        path_hash = str(row.get("path_hash", "")).strip()
        absolute_path = str(row.get("absolute_path", "")).strip()
        if path_hash and absolute_path:
            out[path_hash] = absolute_path
    return out


def _extract_bpm_hint(text: str) -> tuple[float | None, float]:
    match = re.search(r"(^|[_\-\s])([6-9][0-9]|1[0-9]{2}|2[0-2][0-9])(?=([_\-\s]|$))", text)
    if not match:
        return None, 0.15
    return float(match.group(2)), 0.62


def _extract_key_hint(text: str) -> tuple[str | None, float]:
    match = re.search(r"([A-Ga-g](?:#|b)?(?:maj|min|m)?)", text)
    if not match:
        return None, 0.12
    return match.group(1).upper(), 0.48


def _probe_duration_seconds(audio_path: Path) -> float | None:
    try:
        result = subprocess.run(
            [*FFPROBE_CMD, audio_path.as_posix()],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return None
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    format_payload = payload.get("format")
    if isinstance(format_payload, dict):
        duration_text = str(format_payload.get("duration", "")).strip()
        try:
            duration = float(duration_text)
            if math.isfinite(duration) and duration > 0:
                return round(duration, 3)
        except ValueError:
            pass
    streams = payload.get("streams", [])
    if isinstance(streams, list):
        for row in streams:
            if not isinstance(row, dict):
                continue
            if str(row.get("codec_type", "")).strip() != "audio":
                continue
            duration_text = str(row.get("duration", "")).strip()
            try:
                duration = float(duration_text)
            except ValueError:
                continue
            if math.isfinite(duration) and duration > 0:
                return round(duration, 3)
    return None


def _render_preview_wav(src_path: Path, target_wav: Path, max_seconds: float = 90.0) -> bool:
    target_wav.parent.mkdir(parents=True, exist_ok=True)
    command = [
        *FFMPEG_CMD,
        "-i",
        src_path.as_posix(),
        "-t",
        f"{max_seconds:.3f}",
        "-ac",
        "1",
        "-ar",
        "22050",
        "-acodec",
        "pcm_s16le",
        target_wav.as_posix(),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return result.returncode == 0 and target_wav.exists()


def _windowed_rms(wav_path: Path, window_seconds: float = 0.1) -> tuple[list[float], float]:
    with wave.open(wav_path.as_posix(), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        frame_rate = handle.getframerate()
        total_frames = handle.getnframes()
        raw = handle.readframes(total_frames)
    if channels <= 0 or sample_width <= 0 or frame_rate <= 0:
        return [], 0.0
    frame_stride = channels * sample_width
    frames_per_window = max(1, int(frame_rate * window_seconds))
    bytes_per_window = frames_per_window * frame_stride
    if bytes_per_window <= 0:
        return [], 0.0
    rms_values: list[float] = []
    for offset in range(0, len(raw), bytes_per_window):
        chunk = raw[offset : offset + bytes_per_window]
        if not chunk:
            continue
        # Manual absolute-mean estimate to avoid optional dependencies.
        if sample_width == 2:
            # Little-endian signed 16-bit.
            sample_count = len(chunk) // 2
            if sample_count == 0:
                continue
            total = 0.0
            for idx in range(0, sample_count * 2, 2):
                value = int.from_bytes(chunk[idx : idx + 2], byteorder="little", signed=True)
                total += abs(float(value))
            rms_values.append(total / sample_count / 32768.0)
        else:
            rms_values.append(0.0)
    total_seconds = len(raw) / float(frame_rate * frame_stride) if frame_stride > 0 else 0.0
    return rms_values, total_seconds


def _estimate_tempo_from_rms(rms_values: list[float], window_seconds: float = 0.1) -> tuple[float | None, float]:
    if len(rms_values) < 8:
        return None, 0.1
    mean = sum(rms_values) / len(rms_values)
    if mean <= 0:
        return None, 0.1
    peaks = 0
    for idx in range(1, len(rms_values) - 1):
        value = rms_values[idx]
        if value > mean * 1.25 and value > rms_values[idx - 1] and value >= rms_values[idx + 1]:
            peaks += 1
    total_seconds = len(rms_values) * window_seconds
    if total_seconds <= 0:
        return None, 0.1
    peak_rate_per_second = peaks / total_seconds
    beats_per_second = peak_rate_per_second
    bpm = beats_per_second * 60.0
    if bpm < 50.0:
        bpm *= 2.0
    if bpm > 190.0:
        bpm /= 2.0
    if bpm < 50.0 or bpm > 210.0:
        return None, 0.14
    confidence = max(0.2, min(0.72, peaks / 160.0))
    return round(bpm, 3), round(confidence, 3)


def _choose_clip_start(rms_values: list[float], window_seconds: float, clip_duration_seconds: float, max_seconds: float) -> float:
    if not rms_values:
        return 0.0
    windows_per_clip = max(1, int(clip_duration_seconds / window_seconds))
    best_index = 0
    best_energy = -1.0
    for idx in range(0, max(1, len(rms_values) - windows_per_clip)):
        end_idx = min(len(rms_values), idx + windows_per_clip)
        energy = sum(rms_values[idx:end_idx])
        if energy > best_energy:
            best_energy = energy
            best_index = idx
    start = best_index * window_seconds
    start = max(0.0, min(start, max(0.0, max_seconds - clip_duration_seconds)))
    return round(start, 3)


def _estimate_roles(redacted_path: str, mean_rms: float, onset_density: float) -> tuple[str, str, str]:
    lower = redacted_path.lower()
    harmonic = "ambiguous_center"
    if any(token in lower for token in ("min", "_m", "cmin", "dmin", "emin", "fmin")):
        harmonic = "minor_pull"
    elif "maj" in lower:
        harmonic = "major_lift"
    texture = "medium_density"
    if mean_rms < 0.08:
        texture = "sparse_texture"
    elif mean_rms > 0.22:
        texture = "dense_texture"
    energy = "steady"
    if onset_density > 1.8:
        energy = "percussive_drive"
    elif onset_density < 0.6:
        energy = "sustained_pad_like"
    return harmonic, texture, energy


def _clip_duration_candidates(bpm: float | None, bpm_confidence: float, full_duration: float) -> list[tuple[int | None, float, str]]:
    bar_lengths = [1, 2, 4, 8]
    if full_duration >= 22.0:
        bar_lengths.append(16)
    if bpm is not None and bpm_confidence >= 0.35:
        candidates: list[tuple[int | None, float, str]] = []
        for bars in bar_lengths:
            seconds = (bars * 4.0 * 60.0) / bpm
            if seconds <= full_duration * 0.9 and seconds >= 1.5:
                candidates.append((bars, round(seconds, 3), "bar_aligned"))
        if candidates:
            return candidates
    fallback = [2.0, 4.0, 8.0, 16.0]
    out: list[tuple[int | None, float, str]] = []
    for seconds in fallback:
        if seconds <= full_duration * 0.9:
            out.append((None, seconds, "fallback_seconds"))
    return out if out else [(None, max(1.5, min(4.0, full_duration * 0.5)), "fallback_seconds")]


def _extract_wav_clip(src_audio: Path, target_wav: Path, start_seconds: float, duration_seconds: float) -> bool:
    target_wav.parent.mkdir(parents=True, exist_ok=True)
    command = [
        *FFMPEG_CMD,
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        src_audio.as_posix(),
        "-t",
        f"{duration_seconds:.3f}",
        "-acodec",
        "pcm_s16le",
        target_wav.as_posix(),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return result.returncode == 0 and target_wav.exists() and target_wav.stat().st_size > 128


def _candidate_id(source_id: str, path_hash: str) -> str:
    digest = hashlib.sha256(f"{source_id}:{path_hash}".encode("utf-8")).hexdigest()
    return f"clip_{digest[:12]}"


def witness_availability_from_audit(model_witness_audit_path: Path) -> WitnessAvailability:
    payload = _read_json(model_witness_audit_path)
    rows = payload.get("witnesses")
    if not isinstance(rows, list):
        return WitnessAvailability(available=[], unavailable=[])
    available: list[str] = []
    unavailable: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        witness_id = str(row.get("witness_id", "")).strip()
        if not witness_id:
            continue
        if bool(row.get("available", False)):
            available.append(witness_id)
        else:
            unavailable.append(witness_id)
    return WitnessAvailability(sorted(set(available)), sorted(set(unavailable)))


def extract_source_loops(
    *,
    controlled_batch_path: Path,
    local_path_map_path: Path,
    model_witness_audit_path: Path,
    source_taste_dossier_path: Path,
    authorization_config_path: Path,
    local_extract_root: Path,
    emit_preview_mp3: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    batch_rows = _read_jsonl(controlled_batch_path)
    path_map = _load_path_map(local_path_map_path)
    witness_availability = witness_availability_from_audit(model_witness_audit_path)
    auth_payload = _read_json(authorization_config_path)
    taste_payload = _read_json(source_taste_dossier_path)
    local_extract_root.mkdir(parents=True, exist_ok=True)

    extracted_rows: list[ExtractedSourceLoop] = []
    missing_local_path = 0
    missing_audio_file = 0
    extraction_failures = 0
    considered = 0
    for item in batch_rows:
        source_id = str(item.get("source_id", "")).strip()
        path_hash = str(item.get("path_hash", "")).strip()
        redacted = str(item.get("redacted_path", "<PRIVATE_LOCAL_PATH>/unknown"))
        if not source_id or not path_hash:
            continue
        considered += 1
        if not bool(item.get("analysis_allowed", False)) or not bool(item.get("retrieval_allowed", False)):
            continue
        absolute_path_text = path_map.get(path_hash, "")
        if not absolute_path_text:
            missing_local_path += 1
            continue
        absolute_path = Path(absolute_path_text)
        if not absolute_path.exists() or not absolute_path.is_file():
            missing_audio_file += 1
            continue

        preview_wav = local_extract_root / "_analysis_cache" / f"{source_id}_{path_hash[:8]}.wav"
        if not _render_preview_wav(absolute_path, preview_wav):
            extraction_failures += 1
            continue
        rms_values, preview_duration = _windowed_rms(preview_wav)
        mean_rms = (sum(rms_values) / len(rms_values)) if rms_values else 0.0
        onset_density = 0.0
        if rms_values:
            mean = mean_rms
            onset_density = sum(1 for x in rms_values if x > mean * 1.25) / max(1.0, preview_duration)

        duration_seconds = _probe_duration_seconds(absolute_path) or preview_duration
        if duration_seconds is None or duration_seconds <= 1.0:
            extraction_failures += 1
            continue

        bpm_file, bpm_file_conf = _extract_bpm_hint(redacted)
        bpm_audio, bpm_audio_conf = _estimate_tempo_from_rms(rms_values)
        if bpm_audio is not None and bpm_audio_conf >= bpm_file_conf:
            bpm_estimate = bpm_audio
            bpm_conf = bpm_audio_conf
        else:
            bpm_estimate = bpm_file
            bpm_conf = bpm_file_conf

        key_estimate, key_conf = _extract_key_hint(redacted)
        candidates = _clip_duration_candidates(bpm_estimate, bpm_conf, duration_seconds)
        bars_target, clip_duration, timing_basis = candidates[min(1, len(candidates) - 1)]
        clip_start = _choose_clip_start(rms_values, 0.1, clip_duration, duration_seconds)

        clip_id = _candidate_id(source_id, path_hash)
        clip_folder = local_extract_root / clip_id
        clip_wav = clip_folder / "source_loop.wav"
        clip_ok = _extract_wav_clip(absolute_path, clip_wav, clip_start, clip_duration)
        if emit_preview_mp3 and clip_ok:
            preview_mp3 = clip_folder / "preview.mp3"
            subprocess.run(
                [*FFMPEG_CMD, "-i", clip_wav.as_posix(), "-codec:a", "libmp3lame", "-q:a", "5", preview_mp3.as_posix()],
                check=False,
                capture_output=True,
                text=True,
            )

        harmonic, texture, energy = _estimate_roles(redacted, mean_rms, onset_density)
        loopability = min(0.95, max(0.18, 0.35 + bpm_conf * 0.4 + min(0.2, mean_rms)))
        rhythm_density = min(1.0, max(0.0, onset_density / 2.8))
        extraction_notes = [
            "Clip extracted from authorized local source audio file.",
            "Bar fallback policy applied automatically when BPM confidence is low.",
        ]
        extracted_rows.append(
            ExtractedSourceLoop(
                clip_id=clip_id,
                source_id=source_id,
                path_hash=path_hash,
                source_redacted_path=redacted,
                local_clip_relpath=(clip_wav.relative_to(local_extract_root.parent).as_posix() if clip_ok else ""),
                local_audio_clip_exists=clip_ok,
                bars_target=bars_target,
                start_seconds=clip_start,
                duration_seconds=clip_duration,
                timing_basis=timing_basis,
                tempo_bpm_estimate=bpm_estimate,
                tempo_confidence=bpm_conf,
                key_estimate=key_estimate,
                key_confidence=key_conf,
                loopability_score=round(loopability, 3),
                rhythm_density_score=round(rhythm_density, 3),
                harmonic_region_hint=harmonic,
                texture_role_hint=texture,
                energy_role_hint=energy,
                analysis_allowed=bool(item.get("analysis_allowed", False)),
                retrieval_allowed=bool(item.get("retrieval_allowed", False)),
                training_allowed=bool(item.get("training_allowed", False)),
                authorized_for_buddy_generation=(
                    clip_ok
                    and bool(item.get("analysis_allowed", False))
                    and bool(item.get("retrieval_allowed", False))
                    and not bool(item.get("training_allowed", False))
                ),
                witnesses_available=witness_availability.available,
                witnesses_unavailable=witness_availability.unavailable,
                extraction_notes=extraction_notes,
                diagnostics={
                    "audio_duration_seconds": duration_seconds,
                    "rms_mean": round(mean_rms, 6),
                    "onset_density_proxy": round(onset_density, 6),
                    "authorization_allow_cloud": bool(auth_payload.get("allow_cloud", False)),
                    "taste_dossier_present": bool(taste_payload),
                },
            )
        )

    rows = [row.to_dict() for row in extracted_rows]
    extracted_count = sum(1 for row in rows if bool(row.get("local_audio_clip_exists", False)))
    eligible_count = sum(1 for row in rows if bool(row.get("authorized_for_buddy_generation", False)))
    report = {
        "considered_controlled_batch_rows": considered,
        "extracted_clip_rows": len(rows),
        "actual_source_audio_snippets_extracted": extracted_count,
        "eligible_for_buddy_generation_count": eligible_count,
        "missing_local_path_count": missing_local_path,
        "missing_audio_file_count": missing_audio_file,
        "extraction_failures_count": extraction_failures,
        "witnesses_available": witness_availability.available,
        "witnesses_unavailable": witness_availability.unavailable,
        "policy": {
            "no_training": True,
            "no_cloud_default": not bool(auth_payload.get("allow_cloud", False)),
            "source_audio_modified": False,
            "source_audio_snippets_committed": False,
        },
        "hard_gate": "only clips with local_audio_clip_exists=true are eligible for buddy generation",
        "limitations": [
            "Tempo/key analysis mixes filename hints with lightweight local waveform proxies.",
            "No cloud backends were called in extraction.",
        ],
    }
    return rows, report
