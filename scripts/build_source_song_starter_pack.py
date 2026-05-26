from __future__ import annotations

import json
import struct
import sys
import wave
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.source_sample_pack import SamplePackExport

CONFIG_PATH = ROOT_DIR / "config" / "source_audio_sample_pack.local.json"
LOCAL_PATH_MAP = ROOT_DIR / "local_source_audio_study" / "source_audio_path_map.local.json"
CANDIDATES_PATH = ROOT_DIR / "datasets" / "source_sample_pack" / "source_loop_candidates.jsonl"
REPORT_DIR = ROOT_DIR / "reports" / "source_sample_pack"
REPORT_JSON = REPORT_DIR / "source_song_starter_pack_report.json"
REPORT_MD = REPORT_DIR / "source_song_starter_pack_report.md"
OUTPUT_ROOT = ROOT_DIR / "outputs" / "source_sample_packs"

PRIVATE_MARKERS = ("C:/Users/", "C:\\Users\\", "/Users/")


@dataclass(frozen=True)
class BuildConfig:
    allow_audio_loop_export: bool
    allow_reference_to_midi_starters: bool
    normalize_audio_loops: bool
    allowed_loop_lengths_bars: list[int]


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
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _load_config() -> BuildConfig:
    payload = _read_json(CONFIG_PATH)
    bars = [int(item) for item in payload.get("allowed_loop_lengths_bars", [2, 4, 8]) if int(item) > 0]
    if not bars:
        bars = [2, 4, 8]
    return BuildConfig(
        allow_audio_loop_export=bool(payload.get("allow_audio_loop_export", False)),
        allow_reference_to_midi_starters=bool(payload.get("allow_reference_to_midi_starters", False)),
        normalize_audio_loops=bool(payload.get("normalize_audio_loops", False)),
        allowed_loop_lengths_bars=sorted(set(bars)),
    )


def _load_path_map() -> dict[str, str]:
    payload = _read_json(LOCAL_PATH_MAP)
    rows = payload.get("path_map")
    if not isinstance(rows, list):
        return {}
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("path_hash", "")).strip()
        value = str(row.get("absolute_path", "")).strip()
        if key and value:
            out[key] = value
    return out


def _round_robin_by_role(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    for candidate in candidates:
        role = str(candidate.get("role", "unknown"))
        buckets[role].append(candidate)
    out: list[dict[str, Any]] = []
    keys = sorted(buckets.keys())
    while True:
        progressed = False
        for key in keys:
            if buckets[key]:
                out.append(buckets[key].popleft())
                progressed = True
        if not progressed:
            break
    return out


def _apply_fade_pcm(raw: bytes, sample_width: int, channels: int, frame_count: int, sample_rate: int) -> bytes:
    if frame_count <= 0:
        return raw
    fade_frames = max(1, min(frame_count // 4, int(sample_rate * 0.01)))
    if fade_frames <= 0:
        return raw
    if sample_width != 2:
        return raw

    samples = list(struct.unpack("<" + "h" * (frame_count * channels), raw))
    for frame_idx in range(fade_frames):
        gain = frame_idx / float(fade_frames)
        for ch in range(channels):
            idx = frame_idx * channels + ch
            samples[idx] = int(samples[idx] * gain)

    for fade_idx in range(fade_frames):
        gain = (fade_frames - fade_idx - 1) / float(fade_frames)
        frame_idx = frame_count - fade_frames + fade_idx
        if frame_idx < 0:
            continue
        for ch in range(channels):
            idx = frame_idx * channels + ch
            samples[idx] = int(samples[idx] * gain)
    return struct.pack("<" + "h" * len(samples), *samples)


def _normalize_pcm(raw: bytes, sample_width: int) -> bytes:
    if sample_width != 2:
        return raw
    if not raw:
        return raw
    samples = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    peak = max(abs(value) for value in samples)
    if peak <= 0:
        return raw
    max_value = float((1 << (sample_width * 8 - 1)) - 1)
    target = max_value * 0.92
    gain = target / float(peak)
    if gain <= 1.0:
        return raw
    scaled = [max(-32768, min(32767, int(round(value * gain)))) for value in samples]
    return struct.pack("<" + "h" * len(scaled), *scaled)


def _cut_wav_loop(
    source_path: Path,
    output_path: Path,
    *,
    start_seconds: float,
    duration_seconds: float,
    normalize: bool,
) -> bool:
    try:
        with wave.open(str(source_path), "rb") as in_wav:
            channels = in_wav.getnchannels()
            sample_width = in_wav.getsampwidth()
            sample_rate = in_wav.getframerate()
            total_frames = in_wav.getnframes()
            start_frame = int(max(start_seconds, 0.0) * sample_rate)
            length_frames = int(max(duration_seconds, 0.01) * sample_rate)
            if start_frame >= total_frames:
                return False
            end_frame = min(total_frames, start_frame + max(length_frames, 1))
            read_frames = max(1, end_frame - start_frame)
            in_wav.setpos(start_frame)
            raw = in_wav.readframes(read_frames)
    except (OSError, wave.Error):
        return False

    faded = _apply_fade_pcm(
        raw,
        sample_width=sample_width,
        channels=channels,
        frame_count=read_frames,
        sample_rate=sample_rate,
    )
    final = _normalize_pcm(faded, sample_width) if normalize else faded

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with wave.open(str(output_path), "wb") as out_wav:
            out_wav.setnchannels(channels)
            out_wav.setsampwidth(sample_width)
            out_wav.setframerate(sample_rate)
            out_wav.writeframes(final)
    except (OSError, wave.Error):
        return False
    return True


def _var_len(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(out)


def _write_simple_midi(path: Path, note: int = 60) -> None:
    tpq = 480
    note_on = _var_len(0) + bytes([0x90, note, 100])
    note_off = _var_len(tpq) + bytes([0x80, note, 0])
    end_track = _var_len(0) + bytes([0xFF, 0x2F, 0x00])
    track_data = note_on + note_off + end_track
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, tpq)
    track = b"MTrk" + struct.pack(">I", len(track_data)) + track_data
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + track)


def _safe_rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()


def build_pack() -> tuple[dict[str, Any], dict[str, Any]]:
    config = _load_config()
    path_map = _load_path_map()
    candidates = _read_jsonl(CANDIDATES_PATH)
    selected = _round_robin_by_role(candidates)

    pack_id = datetime.now(UTC).strftime("source_song_starter_pack_%Y%m%dT%H%M%SZ")
    pack_root = OUTPUT_ROOT / pack_id
    audio_dir = pack_root / "audio_loops"
    midi_dir = pack_root / "midi_starters"
    recipes_dir = pack_root / "recipes"

    audio_exports: list[dict[str, Any]] = []
    midi_exports: list[dict[str, Any]] = []
    recipe_exports: list[dict[str, Any]] = []
    policy_violations: list[str] = []
    reference_only_skips = 0

    for idx, candidate in enumerate(selected):
        candidate_id = str(candidate.get("candidate_id", f"candidate_{idx}"))
        path_hash = str(candidate.get("path_hash", "")).strip()
        source_id = str(candidate.get("source_id", "")).strip()
        role = str(candidate.get("role", "unknown"))
        bar_length = int(candidate.get("bar_length", 4))
        if bar_length not in config.allowed_loop_lengths_bars:
            policy_violations.append(f"{candidate_id}:bar_length_not_allowed")
            continue
        source_path_raw = path_map.get(path_hash)
        is_reference_only = bool(candidate.get("reference_only", False))
        export_allowed = bool(candidate.get("export_allowed", False))
        duration_seconds = candidate.get("duration_seconds")
        duration = float(duration_seconds) if duration_seconds is not None else None

        if is_reference_only:
            reference_only_skips += 1
            if config.allow_reference_to_midi_starters:
                midi_path = midi_dir / f"{idx:03d}_{candidate_id}.mid"
                _write_simple_midi(midi_path, note=60 + (idx % 12))
                midi_exports.append(
                    {
                        "candidate_id": candidate_id,
                        "source_id": source_id,
                        "role": role,
                        "path": _safe_rel(midi_path),
                    }
                )
            recipe_path = recipes_dir / f"{idx:03d}_{candidate_id}.txt"
            recipe_path.parent.mkdir(parents=True, exist_ok=True)
            recipe_path.write_text(
                "\n".join(
                    [
                        f"candidate_id: {candidate_id}",
                        f"source_id: {source_id}",
                        f"role: {role}",
                        f"bar_length: {bar_length}",
                        "reference_only: true",
                        "instruction: Build a transformed phrase; do not copy source audio.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            recipe_exports.append({"candidate_id": candidate_id, "path": _safe_rel(recipe_path)})
            continue

        if not config.allow_audio_loop_export or not export_allowed:
            policy_violations.append(f"{candidate_id}:missing_export_permission")
            continue
        if not source_path_raw:
            policy_violations.append(f"{candidate_id}:missing_local_path_map")
            continue
        if duration is None or duration <= 0:
            policy_violations.append(f"{candidate_id}:missing_duration")
            continue
        source_path = Path(source_path_raw)
        if source_path.suffix.lower() != ".wav":
            policy_violations.append(f"{candidate_id}:unsupported_source_format")
            continue

        out_wav = audio_dir / f"{idx:03d}_{role}_{bar_length}bar_{candidate_id}.wav"
        ok = _cut_wav_loop(
            source_path,
            out_wav,
            start_seconds=float(candidate.get("start_seconds", 0.0)),
            duration_seconds=duration,
            normalize=config.normalize_audio_loops,
        )
        if not ok:
            policy_violations.append(f"{candidate_id}:audio_export_failed")
            continue
        audio_exports.append(
            {
                "candidate_id": candidate_id,
                "source_id": source_id,
                "role": role,
                "bar_length": bar_length,
                "path": _safe_rel(out_wav),
            }
        )
        recipe_path = recipes_dir / f"{idx:03d}_{candidate_id}.txt"
        recipe_path.parent.mkdir(parents=True, exist_ok=True)
        recipe_path.write_text(
            "\n".join(
                [
                    f"candidate_id: {candidate_id}",
                    f"source_id: {source_id}",
                    f"role: {role}",
                    f"bar_length: {bar_length}",
                    f"audio_loop: {_safe_rel(out_wav)}",
                    "instruction: Layer with original MIDI to create transformed starter.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        recipe_exports.append({"candidate_id": candidate_id, "path": _safe_rel(recipe_path)})

    manifest = {
        "pack_id": pack_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_items_considered": len({str(row.get("source_id", "")) for row in selected if row.get("source_id")}),
        "loop_candidates_found": len(selected),
        "audio_loops": audio_exports,
        "midi_starters": midi_exports,
        "recipes": recipe_exports,
        "policy": {
            "allow_audio_loop_export": config.allow_audio_loop_export,
            "allow_reference_to_midi_starters": config.allow_reference_to_midi_starters,
            "allowed_loop_lengths_bars": config.allowed_loop_lengths_bars,
            "no_training_performed": True,
            "no_cloud_calls_performed": True,
            "source_files_modified": False,
        },
        "policy_violations": sorted(set(policy_violations)),
    }
    pack_root.mkdir(parents=True, exist_ok=True)
    manifest_path = pack_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    readme_path = pack_root / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Source Song Starter Pack",
                "",
                f"- pack_id: `{pack_id}`",
                f"- audio_loops_exported: `{len(audio_exports)}`",
                f"- midi_starters_created: `{len(midi_exports)}`",
                f"- recipe_starters_created: `{len(recipe_exports)}`",
                f"- reference_only_audio_skipped: `{reference_only_skips}`",
                "",
                "Policy: source audio export is local-only and permission-gated.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    private_path_detected = any(
        marker in json.dumps({"manifest": manifest, "exports": [audio_exports, midi_exports, recipe_exports]})
        for marker in PRIVATE_MARKERS
    )

    export_summary = SamplePackExport(
        pack_id=pack_id,
        generated_at=datetime.now(UTC).isoformat(),
        source_items_considered=manifest["source_items_considered"],
        loop_candidates_found=manifest["loop_candidates_found"],
        audio_loops_exported=len(audio_exports),
        midi_starters_created=len(midi_exports),
        recipe_starters_created=len(recipe_exports),
        reference_only_audio_skipped=reference_only_skips,
        export_violations=bool(policy_violations),
        reaper_bridge_export_supported=True,
        private_paths_detected=private_path_detected,
        output_folder=_safe_rel(pack_root),
        manifest_path=_safe_rel(manifest_path),
        notes=[
            "Source audio is never modified.",
            "Reference-only rows never export audio.",
        ],
    ).to_dict()
    return manifest, export_summary


def write_reports(manifest: dict[str, Any], export_summary: dict[str, Any]) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(export_summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Source Song Starter Pack Report",
        "",
        f"- pack_id: `{export_summary['pack_id']}`",
        f"- source_items_considered: `{export_summary['source_items_considered']}`",
        f"- loop_candidates_found: `{export_summary['loop_candidates_found']}`",
        f"- audio_loops_exported: `{export_summary['audio_loops_exported']}`",
        f"- midi_starters_created: `{export_summary['midi_starters_created']}`",
        f"- recipe_starters_created: `{export_summary['recipe_starters_created']}`",
        f"- reference_only_audio_skipped: `{export_summary['reference_only_audio_skipped']}`",
        f"- export_violations: `{export_summary['export_violations']}`",
        f"- private_paths_detected: `{export_summary['private_paths_detected']}`",
        "",
        "## Policy checks",
        f"- allow_audio_loop_export: `{manifest['policy']['allow_audio_loop_export']}`",
        f"- allow_reference_to_midi_starters: `{manifest['policy']['allow_reference_to_midi_starters']}`",
        f"- source_files_modified: `{manifest['policy']['source_files_modified']}`",
        "",
        "## Evidence limits",
        "- Tempo/key come from candidate heuristics only when available.",
        "- No witness/model availability is fabricated in this export stage.",
    ]
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return REPORT_JSON, REPORT_MD


def main() -> int:
    manifest, export_summary = build_pack()
    report_json, report_md = write_reports(manifest, export_summary)
    print(f"SOURCE_SONG_STARTER_PACK_ID={export_summary['pack_id']}")
    print(f"SOURCE_SONG_STARTER_PACK_PATH={export_summary['output_folder']}")
    print(f"SOURCE_SONG_STARTER_PACK_MANIFEST={export_summary['manifest_path']}")
    print(f"SOURCE_SONG_STARTER_PACK_REPORT_JSON={report_json.as_posix()}")
    print(f"SOURCE_SONG_STARTER_PACK_REPORT_MD={report_md.as_posix()}")
    print(f"SOURCE_ITEMS_CONSIDERED={export_summary['source_items_considered']}")
    print(f"LOOP_CANDIDATES_FOUND={export_summary['loop_candidates_found']}")
    print(f"AUDIO_LOOPS_EXPORTED={export_summary['audio_loops_exported']}")
    print(f"MIDI_STARTERS_CREATED={export_summary['midi_starters_created']}")
    print(f"RECIPE_STARTERS_CREATED={export_summary['recipe_starters_created']}")
    print(f"REFERENCE_ONLY_AUDIO_SKIPPED={export_summary['reference_only_audio_skipped']}")
    print(f"EXPORT_VIOLATIONS={export_summary['export_violations']}")
    print(f"PRIVATE_PATHS_DETECTED={export_summary['private_paths_detected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
