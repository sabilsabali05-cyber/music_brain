from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mido import MidiFile, tick2second

from .loop_pack_schema import RenderQualityTier, RendererKind


class RendererUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class RendererContext:
    repo_root: Path
    renderer_override: str = ""
    sample_rate: int = 44_100
    bit_depth: int = 16
    micro_fade_ms: float = 8.0
    duration_tolerance_seconds: float = 0.03


@dataclass(frozen=True)
class RenderResult:
    renderer_used: RendererKind
    render_quality: RenderQualityTier
    preview_limited: bool
    render_verified: bool
    duration_seconds: float
    notes: list[str] = field(default_factory=list)


def render_midi_to_wav(
    *,
    midi_path: Path,
    wav_path: Path,
    role: str,
    target_duration_seconds: float,
    context: RendererContext,
) -> RenderResult:
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    configured_result = _try_configured_renderer(
        midi_path=midi_path,
        wav_path=wav_path,
        target_duration_seconds=target_duration_seconds,
        context=context,
    )
    if configured_result:
        return configured_result

    soundfont_result = _try_soundfont_renderer(
        midi_path=midi_path,
        wav_path=wav_path,
        target_duration_seconds=target_duration_seconds,
        context=context,
    )
    if soundfont_result:
        return soundfont_result

    return _render_with_python_preview_synth(
        midi_path=midi_path,
        wav_path=wav_path,
        role=role,
        target_duration_seconds=target_duration_seconds,
        context=context,
    )


def _read_local_render_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _configured_renderer_command(context: RendererContext) -> str:
    if context.renderer_override.strip():
        return context.renderer_override.strip()
    env_cmd = os.environ.get("PAIRED_LOOP_PACK_RENDER_CMD", "").strip()
    if env_cmd:
        return env_cmd
    config = _read_local_render_config(context.repo_root / "config" / "local_render_config.local.json")
    cmd = str(config.get("paired_loop_pack_renderer_command", "")).strip()
    return cmd


def _configured_soundfont_path(context: RendererContext) -> str:
    env_sf = os.environ.get("PAIRED_LOOP_SOUND_FONT", "").strip()
    if env_sf:
        return env_sf
    config = _read_local_render_config(context.repo_root / "config" / "local_render_config.local.json")
    sf = str(config.get("paired_loop_pack_soundfont_path", "")).strip()
    return sf


def _try_configured_renderer(
    *,
    midi_path: Path,
    wav_path: Path,
    target_duration_seconds: float,
    context: RendererContext,
) -> RenderResult | None:
    command_template = _configured_renderer_command(context)
    if not command_template:
        return None
    rendered_command = command_template.format(
        input_midi=str(midi_path),
        output_wav=str(wav_path),
        duration_seconds=f"{target_duration_seconds:.6f}",
        sample_rate=str(context.sample_rate),
    )
    completed = subprocess.run(rendered_command, shell=True, check=False, capture_output=True, text=True)
    if completed.returncode != 0 or not wav_path.exists() or wav_path.stat().st_size <= 0:
        return None
    duration = _wav_duration_seconds(wav_path)
    verified = _duration_matches(duration, target_duration_seconds, context.duration_tolerance_seconds)
    return RenderResult(
        renderer_used=RendererKind.CONFIGURED_LOCAL,
        render_quality=RenderQualityTier.HIGH,
        preview_limited=False,
        render_verified=verified,
        duration_seconds=duration,
        notes=["Configured local renderer command executed."],
    )


def _try_soundfont_renderer(
    *,
    midi_path: Path,
    wav_path: Path,
    target_duration_seconds: float,
    context: RendererContext,
) -> RenderResult | None:
    fluidsynth = shutil.which("fluidsynth")
    soundfont_path = _configured_soundfont_path(context)
    if not fluidsynth or not soundfont_path:
        return None
    if not Path(soundfont_path).exists():
        return None
    cmd = [
        fluidsynth,
        "-ni",
        soundfont_path,
        str(midi_path),
        "-F",
        str(wav_path),
        "-r",
        str(context.sample_rate),
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0 or not wav_path.exists() or wav_path.stat().st_size <= 0:
        return None

    _force_wav_duration(
        wav_path=wav_path,
        target_duration_seconds=target_duration_seconds,
        sample_rate=context.sample_rate,
    )
    duration = _wav_duration_seconds(wav_path)
    verified = _duration_matches(duration, target_duration_seconds, context.duration_tolerance_seconds)
    return RenderResult(
        renderer_used=RendererKind.SOUNDFONT,
        render_quality=RenderQualityTier.HIGH,
        preview_limited=False,
        render_verified=verified,
        duration_seconds=duration,
        notes=["Rendered with local soundfont renderer (fluidsynth)."],
    )


def _render_with_python_preview_synth(
    *,
    midi_path: Path,
    wav_path: Path,
    role: str,
    target_duration_seconds: float,
    context: RendererContext,
) -> RenderResult:
    midi = MidiFile(str(midi_path))
    tempo = _first_tempo(midi)
    events = _collect_note_events(midi, tempo)
    sample_count = max(1, int(round(target_duration_seconds * context.sample_rate)))
    buffer = [0.0] * sample_count
    for start_sec, end_sec, note, velocity in events:
        if end_sec <= start_sec:
            continue
        _synthesize_note(
            buffer=buffer,
            sample_rate=context.sample_rate,
            role=role,
            start_sec=start_sec,
            end_sec=end_sec,
            note=note,
            velocity=velocity,
        )

    _apply_edge_fades(buffer, sample_rate=context.sample_rate, fade_ms=context.micro_fade_ms)
    pcm = _to_pcm16(buffer, peak_target=0.92)
    _write_pcm16_wav(wav_path, pcm=pcm, sample_rate=context.sample_rate)
    _force_wav_duration(wav_path=wav_path, target_duration_seconds=target_duration_seconds, sample_rate=context.sample_rate)
    duration = _wav_duration_seconds(wav_path)
    verified = _duration_matches(duration, target_duration_seconds, context.duration_tolerance_seconds)
    return RenderResult(
        renderer_used=RendererKind.PYTHON_PREVIEW,
        render_quality=RenderQualityTier.PREVIEW,
        preview_limited=True,
        render_verified=verified,
        duration_seconds=duration,
        notes=[
            "Python preview synth fallback used because no high-quality local renderer was available.",
            "Preview timbre is approximate and intended for pairing verification, not final production sound.",
        ],
    )


def _first_tempo(midi: MidiFile) -> int:
    for track in midi.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                return int(msg.tempo)
    return 500_000


def _collect_note_events(midi: MidiFile, tempo: int) -> list[tuple[float, float, int, int]]:
    events: list[tuple[float, float, int, int]] = []
    ticks_per_beat = max(1, int(midi.ticks_per_beat))
    active: dict[tuple[int, int], list[tuple[float, int]]] = {}
    for track in midi.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += int(msg.time)
            if msg.type not in {"note_on", "note_off"}:
                continue
            now_sec = float(tick2second(abs_tick, ticks_per_beat, tempo))
            channel = int(getattr(msg, "channel", 0))
            note = int(getattr(msg, "note", 0))
            velocity = int(getattr(msg, "velocity", 0))
            key = (channel, note)
            is_note_on = msg.type == "note_on" and velocity > 0
            if is_note_on:
                active.setdefault(key, []).append((now_sec, velocity))
                continue
            starts = active.get(key, [])
            if not starts:
                continue
            start_sec, start_velocity = starts.pop(0)
            events.append((max(0.0, start_sec), max(start_sec, now_sec), note, max(1, start_velocity)))
    return events


def _synthesize_note(
    *,
    buffer: list[float],
    sample_rate: int,
    role: str,
    start_sec: float,
    end_sec: float,
    note: int,
    velocity: int,
) -> None:
    start = max(0, int(start_sec * sample_rate))
    end = min(len(buffer), int(end_sec * sample_rate))
    if end <= start:
        return
    freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
    amp = min(1.0, max(0.0, velocity / 127.0)) * 0.22
    attack = max(1, int(0.004 * sample_rate))
    release = max(1, int(0.012 * sample_rate))
    role_key = role.lower()
    for idx in range(start, end):
        t = idx / float(sample_rate)
        phase = 2.0 * math.pi * freq * t
        if "bass" in role_key:
            sample = math.sin(phase) + 0.3 * math.sin(phase * 0.5)
        elif "chord" in role_key or "texture" in role_key:
            sample = 0.7 * math.sin(phase) + 0.25 * math.sin(phase * 2.0) + 0.15 * math.sin(phase * 3.0)
        elif "drum" in role_key or "percussion" in role_key:
            sample = math.sin(phase * 1.5) * (0.7 - 0.7 * (idx - start) / max(1, end - start))
        else:
            sample = math.sin(phase) + 0.2 * math.sin(phase * 2.0)
        env = 1.0
        elapsed = idx - start
        left = end - idx
        if elapsed < attack:
            env *= elapsed / float(attack)
        if left < release:
            env *= left / float(release)
        buffer[idx] += sample * env * amp


def _apply_edge_fades(buffer: list[float], *, sample_rate: int, fade_ms: float) -> None:
    if not buffer:
        return
    fade_samples = max(1, int(sample_rate * max(0.0, fade_ms) / 1000.0))
    fade_samples = min(fade_samples, len(buffer) // 4 if len(buffer) > 4 else 1)
    if fade_samples <= 0:
        return
    for i in range(fade_samples):
        gain = i / float(fade_samples)
        buffer[i] *= gain
        buffer[-i - 1] *= gain


def _to_pcm16(buffer: list[float], *, peak_target: float) -> bytes:
    if not buffer:
        return b""
    peak = max(abs(x) for x in buffer)
    gain = 1.0 if peak <= 0 else min(1.0, peak_target / peak)
    out = bytearray()
    for sample in buffer:
        v = max(-1.0, min(1.0, sample * gain))
        i = int(round(v * 32767.0))
        out.extend(i.to_bytes(2, byteorder="little", signed=True))
    return bytes(out)


def _write_pcm16_wav(path: Path, *, pcm: bytes, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as wav_handle:
        wav_handle.setnchannels(1)
        wav_handle.setsampwidth(2)
        wav_handle.setframerate(sample_rate)
        wav_handle.writeframes(pcm)


def _wav_duration_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav_handle:
            rate = wav_handle.getframerate()
            frames = wav_handle.getnframes()
    except Exception:  # noqa: BLE001
        return 0.0
    if rate <= 0:
        return 0.0
    return frames / float(rate)


def _force_wav_duration(*, wav_path: Path, target_duration_seconds: float, sample_rate: int) -> None:
    try:
        with wave.open(str(wav_path), "rb") as wav_handle:
            channels = wav_handle.getnchannels()
            sample_width = wav_handle.getsampwidth()
            src_rate = wav_handle.getframerate()
            frames = wav_handle.readframes(wav_handle.getnframes())
    except Exception:  # noqa: BLE001
        return
    if src_rate <= 0:
        return
    frame_width = max(1, channels * sample_width)
    target_frames = max(1, int(round(target_duration_seconds * sample_rate)))
    if src_rate != sample_rate:
        return
    current_frames = len(frames) // frame_width
    if current_frames < target_frames:
        frames += b"\x00" * (target_frames - current_frames) * frame_width
    elif current_frames > target_frames:
        frames = frames[: target_frames * frame_width]
    with wave.open(str(wav_path), "wb") as wav_handle:
        wav_handle.setnchannels(channels)
        wav_handle.setsampwidth(sample_width)
        wav_handle.setframerate(sample_rate)
        wav_handle.writeframes(frames)


def _duration_matches(actual: float, expected: float, tolerance: float) -> bool:
    return actual > 0 and abs(actual - expected) <= max(0.001, tolerance)
