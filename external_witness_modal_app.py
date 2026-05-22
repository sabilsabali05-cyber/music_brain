from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import modal

app = modal.App("music-brain-external-witness-v1")

essentia_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "numpy>=1.26",
        "scipy>=1.11",
        "librosa>=0.10",
        "soundfile>=0.12",
        "essentia>=2.1b6.dev1110",
    )
)

music21_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "music21>=9.1",
        "numpy>=1.26",
        "mido>=1.3",
    )
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_result(provider_name: str, source_name: str, *, status: str = "success") -> dict[str, Any]:
    return {
        "provider_name": provider_name,
        "status": status,
        "warnings": [],
        "limitations": [],
        "created_at": _now_iso(),
        "source_artifacts": {"source_name": source_name},
    }


@app.function(image=essentia_image, timeout=300)
def run_essentia_witness(audio_bytes: bytes, source_name: str, options: dict[str, object] | None = None) -> dict[str, Any]:
    payload = _base_result("essentia", source_name)
    payload.update(
        {
            "audio_descriptors": {},
            "rhythm_descriptors": {
                "bpm": None,
                "beat_positions": [],
                "beat_confidence": None,
                "rhythm_summary": {},
            },
            "tonal_descriptors": {
                "key_candidates": [],
                "hpcp_summary": {},
                "chroma_summary": {},
            },
            "spectral_descriptors": {},
            "high_level_descriptors": {},
        }
    )
    if not audio_bytes:
        payload["status"] = "failed"
        payload["warnings"].append("audio_bytes is empty")
        return payload
    try:
        import numpy as np
        from essentia.standard import (
            FrameGenerator,
            HPCP,
            KeyExtractor,
            MonoLoader,
            RhythmExtractor2013,
            SpectralCentroidTime,
            SpectralPeaks,
            Spectrum,
            Windowing,
        )
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "unavailable"
        payload["warnings"].append(f"Essentia import unavailable: {exc.__class__.__name__}: {exc}")
        payload["limitations"].append("Essentia dependency unavailable in Modal image.")
        return payload

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "source_audio"
            audio_path.write_bytes(audio_bytes)
            audio = MonoLoader(filename=str(audio_path), sampleRate=44100)()
            rhythm_extractor = RhythmExtractor2013(method="multifeature")
            bpm, beats, beat_confidence, _, _ = rhythm_extractor(audio)
            key, scale, key_strength = KeyExtractor()(audio)
            win = Windowing(type="hann")
            spec = Spectrum()
            peaks = SpectralPeaks()
            hpcp_alg = HPCP()
            cent_alg = SpectralCentroidTime()
            hpcp_frames: list[list[float]] = []
            centroids: list[float] = []
            for frame in FrameGenerator(audio, frameSize=4096, hopSize=2048, startFromZero=True):
                frame_spec = spec(win(frame))
                freqs, mags = peaks(frame_spec)
                h = hpcp_alg(freqs, mags)
                hpcp_frames.append([float(x) for x in h])
                centroids.append(float(cent_alg(frame)))
            hpcp_mean = [0.0] * 12
            if hpcp_frames:
                arr = np.asarray(hpcp_frames)
                hpcp_mean = [float(v) for v in arr.mean(axis=0).tolist()]
            payload["audio_descriptors"] = {
                "sample_rate": 44100,
                "sample_count": int(len(audio)),
                "duration_seconds": round(float(len(audio) / 44100.0), 6),
            }
            payload["rhythm_descriptors"] = {
                "bpm": round(float(bpm), 6),
                "beat_positions": [round(float(v), 6) for v in list(beats)[:4096]],
                "beat_confidence": round(float(beat_confidence), 6),
                "rhythm_summary": {"beat_count": int(len(beats)), "method": "RhythmExtractor2013(multifeature)"},
            }
            payload["tonal_descriptors"] = {
                "key_candidates": [{"key": str(key), "scale": str(scale), "strength": round(float(key_strength), 6)}],
                "hpcp_summary": {
                    "dimension": len(hpcp_mean),
                    "mean": [round(float(v), 6) for v in hpcp_mean],
                    "max_bin": int(max(range(len(hpcp_mean)), key=lambda i: hpcp_mean[i])) if hpcp_mean else None,
                },
                "chroma_summary": {
                    "mean_energy": round(float(mean(hpcp_mean)), 6) if hpcp_mean else 0.0,
                },
            }
            payload["spectral_descriptors"] = {
                "spectral_centroid_mean": round(float(mean(centroids)), 6) if centroids else None,
                "spectral_centroid_frames": len(centroids),
            }
            payload["high_level_descriptors"] = {"note": "High-level Essentia models not enabled in this witness path."}
            return payload
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "failed"
        payload["warnings"].append(f"Essentia witness execution failed: {exc.__class__.__name__}: {exc}")
        payload["limitations"].append("Witness failure is non-fatal; pipeline should continue.")
        return payload


@app.function(image=music21_image, timeout=300)
def run_music21_witness(midi_bytes: bytes, source_name: str, options: dict[str, object] | None = None) -> dict[str, Any]:
    payload = _base_result("music21", source_name)
    payload.update(
        {
            "symbolic_descriptors": {},
            "key_candidates": [],
            "chord_candidates": [],
            "interval_summary": {},
            "voice_leading_summary": {},
        }
    )
    if not midi_bytes:
        payload["status"] = "failed"
        payload["warnings"].append("midi_bytes is empty")
        return payload
    try:
        from music21 import chord, converter, interval, note
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "unavailable"
        payload["warnings"].append(f"music21 import unavailable: {exc.__class__.__name__}: {exc}")
        payload["limitations"].append("music21 dependency unavailable in Modal image.")
        return payload

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            midi_path = Path(tmp_dir) / "merged.mid"
            midi_path.write_bytes(midi_bytes)
            score = converter.parse(str(midi_path))

        flat_notes = [n for n in score.flatten().notes if isinstance(n, note.Note)]
        pcs = [int(n.pitch.pitchClass) for n in flat_notes]
        pc_hist = {str(i): 0 for i in range(12)}
        for pc in pcs:
            pc_hist[str(pc)] += 1

        key_candidates: list[dict[str, object]] = []
        try:
            k = score.analyze("key")
            key_candidates.append({"key": str(k.tonic.name), "mode": str(k.mode), "correlation": float(getattr(k, "correlationCoefficient", 0.0) or 0.0)})
        except Exception:  # noqa: BLE001
            payload["warnings"].append("music21 key analysis failed; key candidates omitted.")

        chord_counts: dict[str, int] = {}
        try:
            ch_score = score.chordify()
            for item in ch_score.flatten().notes:
                if not isinstance(item, chord.Chord):
                    continue
                label = item.commonName or item.pitchedCommonName or "chord"
                chord_counts[label] = chord_counts.get(label, 0) + 1
        except Exception:  # noqa: BLE001
            payload["warnings"].append("music21 chordification failed; chord candidates omitted.")

        intervals: list[int] = []
        for a, b in zip(flat_notes, flat_notes[1:]):
            try:
                intervals.append(abs(interval.Interval(a, b).semitones))
            except Exception:  # noqa: BLE001
                continue
        small_steps = sum(1 for v in intervals if v <= 2)
        leaps = sum(1 for v in intervals if v >= 5)

        payload["key_candidates"] = key_candidates[:6]
        payload["chord_candidates"] = [{"label": k, "count": v} for k, v in sorted(chord_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]]
        payload["symbolic_descriptors"] = {
            "note_count": len(flat_notes),
            "pitch_class_histogram": pc_hist,
        }
        payload["interval_summary"] = {
            "interval_count": len(intervals),
            "mean_semitones": (sum(intervals) / len(intervals)) if intervals else 0.0,
            "step_ratio": (small_steps / len(intervals)) if intervals else 0.0,
            "leap_ratio": (leaps / len(intervals)) if intervals else 0.0,
        }
        payload["voice_leading_summary"] = {
            "step_motion_count": small_steps,
            "leap_motion_count": leaps,
            "motion_balance": "step_dominant" if small_steps >= leaps else "leap_dominant",
        }
        payload["limitations"].append("derived from YourMT3 MIDI; not ground truth")
        return payload
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "failed"
        payload["warnings"].append(f"music21 witness execution failed: {exc.__class__.__name__}: {exc}")
        payload["limitations"].append("Witness failure is non-fatal; pipeline should continue.")
        return payload
