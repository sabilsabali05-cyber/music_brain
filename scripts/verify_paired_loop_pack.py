from __future__ import annotations

import argparse
import hashlib
import json
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = ROOT_DIR / "outputs" / "paired_loop_packs"
REPORT_DIR = ROOT_DIR / "reports" / "paired_loop_packs"
VERIFY_REPORT_JSON = REPORT_DIR / "paired_loop_pack_verification_report.json"
VERIFY_REPORT_MD = REPORT_DIR / "paired_loop_pack_verification_report.md"
PRIVATE_MARKERS = ("C:\\Users\\", "C:/Users/", "/Users/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_pack_manifest_path() -> Path | None:
    if not OUTPUT_ROOT.exists():
        return None
    manifests = [item / "pack_manifest.json" for item in OUTPUT_ROOT.iterdir() if item.is_dir() and (item / "pack_manifest.json").exists()]
    if not manifests:
        return None
    manifests.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return manifests[0]


def _wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
    except Exception:  # noqa: BLE001
        return 0.0
    return frames / float(rate) if rate > 0 else 0.0


def _has_private_markers(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    return any(marker in text for marker in PRIVATE_MARKERS)


def verify_pack(manifest_path: Path, duration_tolerance_seconds: float = 0.03) -> dict[str, Any]:
    if manifest_path.is_dir():
        manifest_path = manifest_path / "pack_manifest.json"
    manifest = _read_json(manifest_path)
    loops = manifest.get("loops", [])
    if not isinstance(loops, list):
        loops = []
    pack_root = manifest_path.parent
    midi_dir = pack_root / "midi_loops"
    audio_dir = pack_root / "audio_loops"
    pairs_dir = pack_root / "pairs"
    midi_files = sorted(midi_dir.glob("*.mid")) if midi_dir.exists() else []
    audio_files = sorted(audio_dir.glob("*.wav")) if audio_dir.exists() else []
    pair_files = sorted(pairs_dir.glob("*.pair.json")) if pairs_dir.exists() else []
    midi_by_stem = {p.stem: p for p in midi_files}
    audio_by_stem = {p.stem: p for p in audio_files}
    pair_by_stem = {p.name.replace(".pair.json", ""): p for p in pair_files}

    issues: list[str] = []
    clone_variation_failures = 0
    valid_pairs = 0
    render_verified_count = 0
    private_paths = False
    seen: set[str] = set()
    for loop in loops:
        if not isinstance(loop, dict):
            issues.append("manifest contains non-object loop entry")
            continue
        basename = str(loop.get("basename", "")).strip()
        if not basename:
            issues.append("loop missing basename")
            continue
        if basename in seen:
            issues.append(f"duplicate basename: {basename}")
        seen.add(basename)
        midi_path = (ROOT_DIR / str(loop.get("midi_path", ""))).resolve()
        audio_path = (ROOT_DIR / str(loop.get("audio_path", ""))).resolve()
        pair_path = (ROOT_DIR / str(loop.get("pair_metadata_path", ""))).resolve()
        if not midi_path.exists():
            issues.append(f"{basename}: missing midi file")
            continue
        if not audio_path.exists():
            issues.append(f"{basename}: missing audio file")
            continue
        if not pair_path.exists():
            issues.append(f"{basename}: missing pair metadata")
            continue
        if midi_path.stem != basename or audio_path.stem != basename or pair_path.name != f"{basename}.pair.json":
            issues.append(f"{basename}: basename mismatch across pair files")
            continue
        pair_payload = _read_json(pair_path)
        if not pair_payload:
            issues.append(f"{basename}: unreadable pair metadata json")
            continue
        private_paths = private_paths or _has_private_markers(pair_payload)
        expected = float(pair_payload.get("duration_seconds_expected", 0.0) or 0.0)
        observed = _wav_duration(audio_path)
        aligned = expected > 0 and abs(observed - expected) <= duration_tolerance_seconds
        if not aligned:
            issues.append(f"{basename}: duration mismatch expected={expected:.6f} observed={observed:.6f}")
        if bool(pair_payload.get("render_verified", False)) and aligned:
            render_verified_count += 1
        valid_pairs += 1

    for stem in audio_by_stem:
        if stem not in midi_by_stem or stem not in pair_by_stem:
            issues.append(f"orphan audio loop: {stem}.wav")
    for stem in midi_by_stem:
        if stem not in audio_by_stem or stem not in pair_by_stem:
            issues.append(f"orphan midi loop: {stem}.mid")
    for stem in pair_by_stem:
        if stem not in audio_by_stem or stem not in midi_by_stem:
            issues.append(f"orphan pair metadata: {stem}.pair.json")

    audio_orphan_count = len([x for x in issues if x.startswith("orphan audio loop:")])
    if "paired_loop_count" in manifest and int(manifest.get("paired_loop_count", 0) or 0) != valid_pairs:
        issues.append(
            f"manifest paired_loop_count mismatch: expected {valid_pairs}, found {int(manifest.get('paired_loop_count', 0) or 0)}"
        )
    if "audio_orphan_count" in manifest and int(manifest.get("audio_orphan_count", 0) or 0) != audio_orphan_count:
        issues.append(
            f"manifest audio_orphan_count mismatch: expected {audio_orphan_count}, found {int(manifest.get('audio_orphan_count', 0) or 0)}"
        )
    if "private_paths_detected" in manifest and bool(manifest.get("private_paths_detected", False)) != private_paths:
        issues.append(
            f"manifest private_paths_detected mismatch: expected {str(private_paths).lower()}, found {str(bool(manifest.get('private_paths_detected', False))).lower()}"
        )
    family_count = 0
    pair_json_count = valid_pairs
    families = manifest.get("families", [])
    if isinstance(families, list) and families:
        family_count = len(families)
        pair_json_count = 0
        render_verified_count = 0
        for family in families:
            if not isinstance(family, dict):
                continue
            family_manifest_path = (ROOT_DIR / str(family.get("family_manifest_path", ""))).resolve()
            family_manifest = _read_json(family_manifest_path)
            pairs = family_manifest.get("pairs", [])
            if not isinstance(pairs, list):
                continue
            seed_hash = ""
            for pair_ref in pairs:
                if not isinstance(pair_ref, dict):
                    continue
                pair_path = (ROOT_DIR / str(pair_ref.get("pair_path", ""))).resolve()
                pair_payload = _read_json(pair_path)
                if not pair_payload:
                    continue
                pair_json_count += 1
                if bool(pair_payload.get("render_verified", False)):
                    render_verified_count += 1
                else:
                    wav_path = (ROOT_DIR / str(pair_payload.get("wav_path", pair_payload.get("audio_path", "")))).resolve()
                    if wav_path.exists() and _wav_duration(wav_path) > 0:
                        render_verified_count += 1
                midi_path = (ROOT_DIR / str(pair_payload.get("midi_path", ""))).resolve()
                if midi_path.exists():
                    midi_hash = hashlib.sha256(midi_path.read_bytes()).hexdigest()[:16]
                    if str(pair_payload.get("variation_type", "")) == "seed":
                        seed_hash = midi_hash
                    elif seed_hash and midi_hash == seed_hash:
                        clone_variation_failures += 1
            if clone_variation_failures > 0:
                issues.append("clone variation hash collision detected")
        valid_pairs = pair_json_count

    verified = (
        valid_pairs > 0
        and audio_orphan_count == 0
        and render_verified_count > 0
        and not private_paths
        and clone_variation_failures == 0
        and not issues
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "pack_manifest_path": manifest_path.as_posix(),
        "pack_id": str(manifest.get("pack_id", "")),
        "midi_loop_count": len(midi_files),
        "audio_loop_count": len(audio_files),
        "midi_count": len(midi_files),
        "wav_count": len(audio_files),
        "paired_loop_count": valid_pairs,
        "pair_json_count": pair_json_count,
        "family_count": family_count,
        "audio_orphan_count": audio_orphan_count,
        "clone_variation_failures": clone_variation_failures,
        "render_verified_count": render_verified_count,
        "private_paths_detected": private_paths,
        "pack_verified": verified,
        "issues": issues,
    }


_verify_pack_primary = verify_pack


def _write_reports(payload: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    VERIFY_REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Paired Loop Pack Verification Report",
        "",
        f"- pack_id: `{payload.get('pack_id', '')}`",
        f"- paired_loop_count: `{payload.get('paired_loop_count', 0)}`",
        f"- audio_orphan_count: `{payload.get('audio_orphan_count', 0)}`",
        f"- render_verified_count: `{payload.get('render_verified_count', 0)}`",
        f"- private_paths_detected: `{payload.get('private_paths_detected', False)}`",
        f"- pack_verified: `{payload.get('pack_verified', False)}`",
        "",
        "## Issues",
    ]
    issues = payload.get("issues", [])
    if isinstance(issues, list) and issues:
        lines.extend([f"- {item}" for item in issues])
    else:
        lines.append("- none")
    lines.append("")
    VERIFY_REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify paired loop pack integrity.")
    parser.add_argument("--manifest", default="")
    parser.add_argument("--duration-tolerance-seconds", type=float, default=0.03)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = (ROOT_DIR / args.manifest).resolve() if args.manifest else _latest_pack_manifest_path()
    if manifest_path is None or not manifest_path.exists():
        print("ERROR=No paired loop pack manifest found under outputs/paired_loop_packs")
        return 1
    payload = verify_pack(manifest_path, duration_tolerance_seconds=max(0.001, float(args.duration_tolerance_seconds)))
    _write_reports(payload)
    print(f"PAIRED_LOOP_PACK_VERIFY_REPORT_JSON={VERIFY_REPORT_JSON.as_posix()}")
    print(f"PAIRED_LOOP_PACK_VERIFY_REPORT_MD={VERIFY_REPORT_MD.as_posix()}")
    print(f"PACK_VERIFIED={str(bool(payload.get('pack_verified', False))).lower()}")
    print(f"PAIRED_LOOP_COUNT={int(payload.get('paired_loop_count', 0))}")
    print(f"AUDIO_ORPHAN_COUNT={int(payload.get('audio_orphan_count', 0))}")
    print(f"RENDER_VERIFIED_COUNT={int(payload.get('render_verified_count', 0))}")
    print(f"PRIVATE_PATHS_DETECTED={str(bool(payload.get('private_paths_detected', False))).lower()}")
    return 0 if bool(payload.get("pack_verified", False)) else 1


if False and __name__ == "__main__":
    raise SystemExit(main())

# ---- Family variation verifier v2 ----
import struct


def _var_len_to_int(blob: bytes, offset: int) -> tuple[int, int]:
    value = 0
    while offset < len(blob):
        byte = blob[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if (byte & 0x80) == 0:
            break
    return value, offset


def _parse_midi_hash(path: Path) -> tuple[str, int]:
    try:
        data = path.read_bytes()
    except OSError:
        return "", 480
    if len(data) < 14 or data[:4] != b"MThd":
        return "", 480
    tpq = struct.unpack(">H", data[12:14])[0]
    pos = 14
    notes: list[tuple[int, int, int, int]] = []
    active: dict[int, tuple[int, int]] = {}
    track_count = struct.unpack(">H", data[10:12])[0]
    for _ in range(track_count):
        if pos + 8 > len(data) or data[pos:pos + 4] != b"MTrk":
            break
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        pos += 8
        track = data[pos:pos + length]
        pos += length
        tick = 0
        idx = 0
        running = None
        while idx < len(track):
            delta, idx = _var_len_to_int(track, idx)
            tick += delta
            if idx >= len(track):
                break
            status = track[idx]
            if status < 0x80 and running is not None:
                status = running
            else:
                idx += 1
                running = status
            if status in (0x90, 0x80) and idx + 2 <= len(track):
                note = track[idx]
                vel = track[idx + 1]
                idx += 2
                if status == 0x90 and vel > 0:
                    active[note] = (tick, vel)
                elif note in active:
                    start, start_vel = active.pop(note)
                    notes.append((note, start_vel, start, max(1, tick - start)))
            elif status == 0xFF and idx < len(track):
                idx += 1
                size, idx = _var_len_to_int(track, idx)
                idx += size
            else:
                idx += 1 if status in (0xC0, 0xD0) else 2
    notes.sort(key=lambda row: (row[2], row[0]))
    return "|".join(f"{a}:{b}:{c}:{d}" for a, b, c, d in notes), (tpq if tpq > 0 else 480)


def verify_pack(pack_path_or_manifest: Path, duration_tolerance_seconds: float = 0.2) -> dict[str, Any]:
    pack_root = pack_path_or_manifest if pack_path_or_manifest.is_dir() else pack_path_or_manifest.parent
    manifest_path = pack_root / "pack_manifest.json"
    manifest = _read_json(manifest_path)
    families = manifest.get("families", [])
    failures: list[str] = []
    audio_orphan_count = 0
    clone_variation_failures = 0
    pair_json_count = 0
    midi_count = 0
    wav_count = 0
    render_verified_count = 0
    strongest_families: list[str] = []
    weak_families: list[str] = []
    weirdest_variations: list[str] = []
    best_standalone_loops: list[str] = []
    if _has_private_markers(manifest):
        failures.append("manifest_contains_private_path")

    for family in families:
        family_id = str(family.get("family_id", ""))
        family_manifest_path = ROOT_DIR / str(family.get("family_manifest_path", ""))
        family_manifest = _read_json(family_manifest_path)
        pairs = family_manifest.get("pairs", [])
        seed_hash = ""
        seed_count = 0
        variation_count = 0
        for pair_ref in pairs:
            pair_json_count += 1
            pair_path = ROOT_DIR / str(pair_ref.get("pair_path", ""))
            pair = _read_json(pair_path)
            for field in ("transformation_from_seed", "musical_independence_note", "source_explanation", "pairing_explanation", "evidence_limits", "usage_notes"):
                if not pair.get(field):
                    failures.append(f"{family_id}:{pair.get('pair_id', 'unknown')}:{field}_missing")
            midi_rel = str(pair.get("midi_path", ""))
            wav_rel = str(pair.get("wav_path", "")) if pair.get("wav_path") else ""
            midi_path = ROOT_DIR / midi_rel
            wav_path = ROOT_DIR / wav_rel if wav_rel else None
            midi_exists = midi_path.exists()
            wav_exists = bool(wav_path and wav_path.exists())
            midi_only_preview = bool(pair.get("midi_only_preview", False))
            if midi_exists:
                midi_count += 1
            else:
                failures.append(f"{family_id}:{pair.get('pair_id', 'unknown')}:missing_midi")
            if wav_exists:
                wav_count += 1
                render_verified_count += 1
            elif not midi_only_preview:
                failures.append(f"{family_id}:{pair.get('pair_id', 'unknown')}:missing_wav_without_preview")
            if midi_exists and not wav_exists and not midi_only_preview:
                audio_orphan_count += 1
            if wav_exists and not midi_exists:
                audio_orphan_count += 1

            variation_type = str(pair.get("variation_type", ""))
            midi_hash, tpq = _parse_midi_hash(midi_path) if midi_exists else ("", 480)
            if variation_type == "seed":
                seed_hash = midi_hash
                seed_count += 1
            else:
                variation_count += 1
                if variation_type == "texture_chop":
                    weirdest_variations.append(str(pair.get("pair_id", "")))
                if variation_type in {"syncopated", "release"}:
                    best_standalone_loops.append(str(pair.get("pair_id", "")))
                if seed_hash and midi_hash and midi_hash == seed_hash:
                    clone_variation_failures += 1
                    failures.append(f"{family_id}:{pair.get('pair_id', 'unknown')}:clone_variation_hash_match")
            if wav_exists and wav_path:
                with wave.open(str(wav_path), "rb") as handle:
                    duration = handle.getnframes() / float(max(1, handle.getframerate()))
                expected = (int(pair.get("bars", 4)) * 4.0 * 60.0) / max(1.0, float(pair.get("bpm", 120.0)))
                if abs(duration - expected) > duration_tolerance_seconds:
                    failures.append(f"{family_id}:{pair.get('pair_id', 'unknown')}:duration_alignment_failed")
            if midi_exists and midi_hash:
                bars = int(pair.get("bars", 4))
                notes = midi_hash.split("|")
                if notes:
                    last_event = max(int(item.split(":")[2]) + int(item.split(":")[3]) for item in notes if item)
                    expected_ticks = bars * 4 * tpq
                    if last_event > expected_ticks + tpq:
                        failures.append(f"{family_id}:{pair.get('pair_id', 'unknown')}:midi_duration_alignment_failed")

        if seed_count < 1 or variation_count < 3:
            failures.append(f"{family_id}:family_minimums_not_met")
            weak_families.append(family_id)
        else:
            strongest_families.append(family_id)

    if len(families) < 3:
        failures.append("pack_minimum_families_not_met")
    if int(manifest.get("family_count", -1)) != len(families):
        failures.append("manifest_family_count_mismatch")
    if int(manifest.get("pair_json_count", -1)) != pair_json_count:
        failures.append("manifest_pair_count_mismatch")
    if int(manifest.get("midi_count", -1)) != midi_count:
        failures.append("manifest_midi_count_mismatch")
    if int(manifest.get("wav_count", -1)) != wav_count:
        failures.append("manifest_wav_count_mismatch")

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "pack_manifest_path": manifest_path.as_posix(),
        "pack_id": str(manifest.get("pack_id", "")),
        "family_count": len(families),
        "paired_loop_count": pair_json_count,
        "midi_loop_count": midi_count,
        "audio_loop_count": wav_count,
        "pair_json_count": pair_json_count,
        "audio_orphan_count": audio_orphan_count,
        "clone_variation_failures": clone_variation_failures,
        "render_verified_count": render_verified_count,
        "private_paths_detected": _has_private_markers({"manifest": manifest}),
        "strongest_families": strongest_families[:8],
        "weak_families": weak_families[:8],
        "weirdest_variations": weirdest_variations[:8],
        "best_standalone_loops": best_standalone_loops[:8],
        "renderer_used": str(manifest.get("renderer_used", "unknown")),
        "pack_verified": not failures and audio_orphan_count == 0 and clone_variation_failures == 0,
        "issues": sorted(set(failures)),
    }
    return payload


def _write_reports(payload: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    VERIFY_REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    VERIFY_REPORT_MD.write_text(
        "\n".join(
            [
                "# Paired Loop Pack Verification Report",
                "",
                f"- pack_id: `{payload['pack_id']}`",
                f"- family_count: `{payload['family_count']}`",
                f"- pair_json_count: `{payload['pair_json_count']}`",
                f"- audio_orphan_count: `{payload['audio_orphan_count']}`",
                f"- clone_variation_failures: `{payload['clone_variation_failures']}`",
                f"- render_verified_count: `{payload['render_verified_count']}`",
                f"- pack_verified: `{payload['pack_verified']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _verify_main() -> int:
    parser = argparse.ArgumentParser(description="Verify paired loop pack integrity.")
    parser.add_argument("--pack-dir", default="")
    parser.add_argument("--duration-tolerance-seconds", type=float, default=0.2)
    args = parser.parse_args()
    if args.pack_dir:
        pack_root = ROOT_DIR / str(args.pack_dir)
    else:
        manifest_path = _latest_pack_manifest_path()
        if manifest_path is None:
            print("ERROR=No paired loop pack manifest found under outputs/paired_loop_packs")
            return 1
        pack_root = manifest_path.parent
    payload = verify_pack(pack_root, duration_tolerance_seconds=max(0.001, float(args.duration_tolerance_seconds)))
    _write_reports(payload)
    print(f"PAIRED_LOOP_PACK_VERIFY_REPORT_JSON={VERIFY_REPORT_JSON.as_posix()}")
    print(f"PAIRED_LOOP_PACK_VERIFY_REPORT_MD={VERIFY_REPORT_MD.as_posix()}")
    print(f"PAIRED_LOOP_PACK_ID={payload['pack_id']}")
    print(f"PACK_VERIFIED={str(payload['pack_verified']).lower()}")
    print(f"FAMILY_COUNT={payload['family_count']}")
    print(f"PAIR_JSON_COUNT={payload['pair_json_count']}")
    print(f"AUDIO_ORPHAN_COUNT={payload['audio_orphan_count']}")
    print(f"CLONE_VARIATION_FAILURES={payload['clone_variation_failures']}")
    print(f"RENDER_VERIFIED_COUNT={payload['render_verified_count']}")
    return 0 if payload["pack_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(_verify_main())
