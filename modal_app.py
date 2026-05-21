from __future__ import annotations

import os
import subprocess
import tempfile
import time
import math
from io import BytesIO
from pathlib import Path

import modal
from mido import Message, MetaMessage, MidiFile, MidiTrack

app = modal.App("music-brain-v2")
image = modal.Image.debian_slim(python_version="3.11").pip_install("mido>=1.3")
mt3_cache_volume = modal.Volume.from_name("music-brain-mt3-cache", create_if_missing=True)
MT3_CACHE_MOUNT = "/models"
MT3_CHECKPOINT_DIR = f"{MT3_CACHE_MOUNT}/mt3_checkpoints"
YOURMT3_DEFAULT_MODEL = "yourmt3"

yourmt3_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "git-lfs", "ffmpeg", "libsndfile1")
    .pip_install(
        "numpy>=1.26",
        "librosa>=0.10",
        "soundfile>=0.12",
        "pretty_midi>=0.2",
        "mido>=1.3",
        "pytorch-lightning==2.6.1",
        "transformers==4.41.2",
        "mt3-infer[torch]",
    )
    .run_commands("git lfs install --system")
    .env({"MT3_CHECKPOINT_DIR": MT3_CHECKPOINT_DIR})
)

audio_structure_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "numpy>=1.26",
        "scipy>=1.11",
        "librosa>=0.10",
        "soundfile>=0.12",
        "mido>=1.3",
    )
)


@app.function(image=image)
def remote_fake_transcribe(normalized_audio_bytes: bytes) -> dict[str, object]:
    """Remote fake transcriber smoke endpoint for modal_fake backend."""
    if not normalized_audio_bytes:
        raise ValueError("normalized_audio_bytes is empty")

    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)

    track.append(MetaMessage("set_tempo", tempo=500000, time=0))
    track.append(Message("program_change", program=0, time=0))

    for note, ticks in [(60, 240), (64, 240), (67, 240), (72, 360)]:
        track.append(Message("note_on", note=note, velocity=92, time=0))
        track.append(Message("note_off", note=note, velocity=0, time=ticks))

    buffer = BytesIO()
    midi.save(file=buffer)
    midi_bytes = buffer.getvalue()

    return {
        "midi_bytes": midi_bytes,
        "provider_used": "fake",
        "backend": "modal_fake",
        "model_version": "modal-fake-transcriber-v0",
    }


def _resolve_modal_gpu() -> str:
    return os.getenv("MUSIC_BRAIN_MODAL_GPU", "T4")


def _git_lfs_available_from_outputs(git_lfs_version: str | None, git_lfs_error: str | None) -> bool:
    if git_lfs_version and "git-lfs" in git_lfs_version.lower():
        return True
    if git_lfs_error and "is not a git command" in git_lfs_error.lower():
        return False
    return bool(git_lfs_version)


def _is_git_lfs_missing_error(message: str) -> bool:
    lowered = message.lower()
    return (
        "git: 'lfs' is not a git command" in lowered
        or "git lfs" in lowered
        or "checkpointdownloaderror" in lowered
        or "failed to clone repository" in lowered
    )


def _is_pytorch_lightning_missing_error(message: str) -> bool:
    lowered = message.lower()
    return "no module named 'pytorch_lightning'" in lowered or "pytorch_lightning" in lowered


def _is_transformers_model_parallel_error(message: str) -> bool:
    lowered = message.lower()
    return (
        "no module named 'transformers.utils.model_parallel_utils'" in lowered
        or "model_parallel_utils" in lowered
    )


@app.function(image=audio_structure_image, timeout=300)
def analyze_audio_structure_modal(
    audio_bytes: bytes, source_name: str, options: dict[str, object] | None = None
) -> dict[str, object]:
    import librosa
    import numpy as np
    import soundfile as sf

    if not audio_bytes:
        raise ValueError("audio_bytes is empty")

    opts = options or {}
    frame_hop_seconds = float(opts.get("frame_hop_seconds", 0.25))
    candidate_density = str(opts.get("candidate_density", "conservative")).lower().strip() or "conservative"
    if candidate_density not in {"conservative", "normal", "dense"}:
        candidate_density = "conservative"
    peak_pick_threshold = float(opts.get("peak_pick_threshold", 0.55))
    min_boundary_distance_seconds = float(opts.get("min_boundary_distance_seconds", 12.0))
    max_candidates = max(1, int(opts.get("max_candidates", 8)))

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / "source_audio"
        source_path.write_bytes(audio_bytes)
        analysis_wav = Path(tmp_dir) / "analysis.wav"
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "22050",
            "-vn",
            str(analysis_wav),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg wav conversion failed: {(result.stderr or '').strip()}")
        samples, sample_rate = sf.read(str(analysis_wav), always_2d=False)
        if getattr(samples, "ndim", 1) == 2:
            samples = np.mean(samples, axis=1)

    y = np.asarray(samples, dtype=np.float32)
    duration_seconds = float(len(y) / max(1, sample_rate))
    hop_length = max(256, int(sample_rate * frame_hop_seconds))
    n_fft = max(1024, hop_length * 2)

    def _norm(values: list[float]) -> list[float]:
        if not values:
            return []
        low = min(values)
        high = max(values)
        if high - low <= 1e-9:
            return [0.0 for _ in values]
        return [float((v - low) / (high - low)) for v in values]

    def _deriv(values: list[float]) -> list[float]:
        if not values:
            return []
        return [0.0] + [abs(values[i] - values[i - 1]) for i in range(1, len(values))]

    def _val(values: list[float], idx: int) -> float:
        if not values:
            return 0.0
        if idx < 0:
            return float(values[0])
        if idx >= len(values):
            return float(values[-1])
        return float(values[idx])

    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop_length)[0].astype(float).tolist()
    onset = librosa.onset.onset_strength(y=y, sr=sample_rate, hop_length=hop_length).astype(float).tolist()
    chroma = librosa.feature.chroma_stft(y=y, sr=sample_rate, hop_length=hop_length, n_fft=n_fft)
    chroma_change = [0.0]
    for idx in range(1, chroma.shape[1]):
        chroma_change.append(float(np.mean(np.abs(chroma[:, idx] - chroma[:, idx - 1]))))
    mfcc = librosa.feature.mfcc(y=y, sr=sample_rate, n_mfcc=13, hop_length=hop_length, n_fft=n_fft)
    timbre_change = [0.0]
    for idx in range(1, mfcc.shape[1]):
        timbre_change.append(float(np.mean(np.abs(mfcc[:, idx] - mfcc[:, idx - 1]))))

    rms_n = _norm(rms)
    onset_n = _norm(onset if onset else _deriv(rms_n))
    chroma_n = _norm(chroma_change)
    timbre_n = _norm(timbre_change)
    length = max(len(rms_n), len(onset_n), len(chroma_n), len(timbre_n))
    novelty = _norm(
        [
            0.25 * _val(rms_n, i)
            + 0.30 * _val(onset_n, i)
            + 0.25 * _val(chroma_n, i)
            + 0.20 * _val(timbre_n, i)
            for i in range(length)
        ]
    )

    presets = {
        "conservative": {"threshold_offset": 0.05, "distance_scale": 1.2, "max_scale": 0.8},
        "normal": {"threshold_offset": 0.0, "distance_scale": 1.0, "max_scale": 1.0},
        "dense": {"threshold_offset": -0.12, "distance_scale": 0.55, "max_scale": 1.8},
    }
    preset = presets[candidate_density]
    requested_threshold = float(peak_pick_threshold)
    effective_threshold = max(0.0, min(1.0, requested_threshold + float(preset["threshold_offset"])))
    requested_min_distance_seconds = max(0.1, float(min_boundary_distance_seconds))
    effective_min_distance_seconds = max(0.1, requested_min_distance_seconds * float(preset["distance_scale"]))
    effective_max_candidates = max(1, int(round(max_candidates * float(preset["max_scale"]))))
    min_distance_frames = max(1, int(effective_min_distance_seconds / max(frame_hop_seconds, 1e-6)))

    feature_map = {
        "novelty_combined": novelty,
        "chroma_change": chroma_n,
        "timbre_change": timbre_n,
        "onset_strength": onset_n,
        "rms": rms_n,
    }
    feature_reason_map = {
        "novelty_combined": "combined_audio_novelty",
        "chroma_change": "harmonic_chroma_change",
        "timbre_change": "timbre_change",
        "onset_strength": "onset_density_change",
        "rms": "energy_change",
    }
    raw_peak_count_by_feature: dict[str, int] = {}
    raw_candidates: list[dict[str, object]] = []
    for source_feature, curve in feature_map.items():
        raw_peak_indices: list[int] = []
        last_peak = -min_distance_frames
        for idx in range(1, len(curve) - 1):
            if idx - last_peak < min_distance_frames:
                continue
            if curve[idx] < effective_threshold:
                continue
            if curve[idx] >= curve[idx - 1] and curve[idx] >= curve[idx + 1]:
                raw_peak_indices.append(idx)
                last_peak = idx
        raw_peak_count_by_feature[source_feature] = len(raw_peak_indices)
        for idx in raw_peak_indices:
            time_seconds = min(duration_seconds, idx * frame_hop_seconds)
            evidence = {
                "energy_change": round(_val(rms_n, idx), 6),
                "onset_change": round(_val(onset_n, idx), 6),
                "chroma_change": round(_val(chroma_n, idx), 6),
                "timbre_change": round(_val(timbre_n, idx), 6),
                "combined_novelty": round(_val(novelty, idx), 6),
            }
            base_confidence = float(_val(curve, idx))
            confidence = max(0.0, min(1.0, 0.65 * base_confidence + 0.35 * float(evidence["combined_novelty"])))
            raw_candidates.append(
                {
                    "time_seconds": round(float(time_seconds), 6),
                    "confidence": round(confidence, 6),
                    "reason": feature_reason_map[source_feature],
                    "source_feature": source_feature,
                    "candidate_source": "audio_structure",
                    "eligible_for_phrase_boundary": True,
                    "feature_evidence": evidence,
                }
            )

    raw_candidates.sort(key=lambda row: float(row.get("time_seconds", 0.0)))
    duplicate_window_seconds = max(frame_hop_seconds * 2.0, min(2.0, effective_min_distance_seconds * 0.25))
    grouped: list[list[dict[str, object]]] = []
    for candidate in raw_candidates:
        if not grouped:
            grouped.append([candidate])
            continue
        previous_time = float(grouped[-1][-1].get("time_seconds", 0.0))
        current_time = float(candidate.get("time_seconds", 0.0))
        if abs(current_time - previous_time) <= duplicate_window_seconds:
            grouped[-1].append(candidate)
        else:
            grouped.append([candidate])

    fused_candidates: list[dict[str, object]] = []
    for group_index, group in enumerate(grouped, start=1):
        strongest = max(group, key=lambda row: float(row.get("confidence", 0.0)))
        contributing_features = sorted({str(row.get("source_feature", "novelty_combined")) for row in group})
        confidence = min(1.0, float(strongest.get("confidence", 0.0)) + 0.04 * max(0, len(contributing_features) - 1))
        merged_evidence = {
            "energy_change": 0.0,
            "onset_change": 0.0,
            "chroma_change": 0.0,
            "timbre_change": 0.0,
            "combined_novelty": 0.0,
        }
        for row in group:
            evidence_obj = row.get("feature_evidence", {})
            if not isinstance(evidence_obj, dict):
                continue
            for key in merged_evidence:
                merged_evidence[key] = max(float(merged_evidence[key]), float(evidence_obj.get(key, 0.0) or 0.0))
        fused = dict(strongest)
        fused["confidence"] = round(confidence, 6)
        fused["duplicate_group_id"] = f"grp_{group_index:04d}"
        fused["contributing_features"] = contributing_features
        fused["feature_evidence"] = {key: round(value, 6) for key, value in merged_evidence.items()}
        fused_candidates.append(fused)

    fused_by_strength = sorted(fused_candidates, key=lambda row: float(row.get("confidence", 0.0)), reverse=True)
    selected: list[dict[str, object]] = []
    for row in fused_by_strength:
        if len(selected) >= effective_max_candidates:
            break
        time_seconds = float(row.get("time_seconds", 0.0))
        if any(abs(time_seconds - float(existing.get("time_seconds", 0.0))) < effective_min_distance_seconds for existing in selected):
            continue
        selected.append(row)
    selected = sorted(selected, key=lambda row: float(row.get("confidence", 0.0)), reverse=True)
    for rank, row in enumerate(selected, start=1):
        row["rank"] = rank
    returned = sorted(selected, key=lambda row: float(row.get("time_seconds", 0.0)))

    return {
        "source_name": source_name,
        "duration_seconds": round(duration_seconds, 6),
        "analysis_backend": "modal_librosa",
        "analysis_version": "audio_structure_modal_librosa_v1",
        "frame_hop_seconds": frame_hop_seconds,
        "features": {
            "rms": rms_n,
            "onset_strength": onset_n,
            "chroma_change": chroma_n,
            "timbre_change": timbre_n,
            "novelty_combined": novelty,
        },
        "boundary_candidates": returned,
        "diagnostics": {
            "fallback_recommended": len(returned) == 0,
            "candidate_boundary_count": len(returned),
            "accepted_boundary_count": 0,
            "rejected_boundary_count": max(0, len(raw_candidates) - len(returned)),
            "candidate_density": candidate_density,
            "raw_peak_count_by_feature": raw_peak_count_by_feature,
            "fused_candidate_count": len(fused_candidates),
            "returned_candidate_count": len(returned),
            "peak_pick_threshold": requested_threshold,
            "min_boundary_distance_seconds": requested_min_distance_seconds,
            "max_candidates": max_candidates,
            "available_features": ["rms", "onset_strength", "chroma_change", "timbre_change", "novelty_combined"],
            "missing_features": [],
            "notes": [
                "Computed on Modal CPU librosa image.",
                "Boundary candidates are conservative cues, not guaranteed phrase truth.",
            ],
            "modal_cpu_only": True,
        },
    }


@app.function(image=yourmt3_image, volumes={MT3_CACHE_MOUNT: mt3_cache_volume})
def yourmt3_diagnostics() -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "checkpoint_dir": os.getenv("MT3_CHECKPOINT_DIR", MT3_CHECKPOINT_DIR),
        "selected_model": os.getenv("MUSIC_BRAIN_MT3_MODEL", YOURMT3_DEFAULT_MODEL),
        "mt3_infer_import": False,
        "available_models": None,
        "torch_cuda_available": False,
        "git_version": None,
        "git_lfs_version": None,
        "git_lfs_available": False,
        "pytorch_lightning_import_ok": False,
        "pytorch_lightning_version": None,
        "pytorch_lightning_error": None,
        "transformers_import_ok": False,
        "transformers_version": None,
        "transformers_error": None,
    }
    try:
        git_version = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
        diagnostics["git_version"] = (git_version.stdout or git_version.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        diagnostics["git_error"] = f"{exc.__class__.__name__}: {exc}"

    git_lfs_error: str | None = None
    try:
        git_lfs_version = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True, check=False)
        git_lfs_text = (git_lfs_version.stdout or git_lfs_version.stderr).strip()
        diagnostics["git_lfs_version"] = git_lfs_text
        if git_lfs_version.returncode != 0:
            git_lfs_error = git_lfs_text
    except Exception as exc:  # noqa: BLE001
        git_lfs_error = f"{exc.__class__.__name__}: {exc}"
        diagnostics["git_lfs_error"] = git_lfs_error

    diagnostics["git_lfs_available"] = _git_lfs_available_from_outputs(
        diagnostics["git_lfs_version"], git_lfs_error
    )

    try:
        import torch

        diagnostics["torch_cuda_available"] = bool(torch.cuda.is_available())
    except Exception as exc:  # noqa: BLE001
        diagnostics["torch_error"] = f"{exc.__class__.__name__}: {exc}"

    try:
        import pytorch_lightning as pl

        diagnostics["pytorch_lightning_import_ok"] = True
        diagnostics["pytorch_lightning_version"] = getattr(pl, "__version__", "unknown")
    except Exception as exc:  # noqa: BLE001
        diagnostics["pytorch_lightning_error"] = f"{exc.__class__.__name__}: {exc}"

    try:
        import transformers

        diagnostics["transformers_import_ok"] = True
        diagnostics["transformers_version"] = getattr(transformers, "__version__", "unknown")
    except Exception as exc:  # noqa: BLE001
        diagnostics["transformers_error"] = f"{exc.__class__.__name__}: {exc}"

    try:
        from mt3_infer import __version__ as mt3_infer_version

        diagnostics["mt3_infer_import"] = True
        diagnostics["mt3_infer_version"] = mt3_infer_version
        try:
            from mt3_infer import list_models  # type: ignore[attr-defined]

            diagnostics["available_models"] = list_models()
        except Exception:
            diagnostics["available_models"] = None
    except Exception as exc:  # noqa: BLE001
        diagnostics["mt3_infer_error"] = f"{exc.__class__.__name__}: {exc}"

    return diagnostics


@app.cls(
    image=yourmt3_image,
    gpu=_resolve_modal_gpu(),
    timeout=600,
    volumes={MT3_CACHE_MOUNT: mt3_cache_volume},
)
class YourMT3ModalRunner:
    """Experimental YourMT3 runner with warm-loaded model state."""

    @modal.enter()
    def load_model(self) -> None:
        self.model_name = os.getenv("MUSIC_BRAIN_MT3_MODEL", YOURMT3_DEFAULT_MODEL)
        self.model_version = f"{self.model_name}-modal-experimental-v1"

        try:
            from mt3_infer import load_model
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"mt3-infer is not installed inside the Modal image: {exc.__class__.__name__}: {exc}"
            ) from exc

        try:
            self.model = load_model(self.model_name, device="cuda")
        except Exception as exc:  # noqa: BLE001
            detailed = f"{exc.__class__.__name__}: {exc}"
            if _is_git_lfs_missing_error(detailed):
                raise RuntimeError(
                    "YourMT3 model failed to load inside Modal because git-lfs is missing or unavailable: "
                    f"{detailed}"
                ) from exc
            if _is_pytorch_lightning_missing_error(detailed):
                raise RuntimeError(
                    "YourMT3 model failed to load inside Modal because pytorch-lightning is missing: "
                    f"{detailed}"
                ) from exc
            if _is_transformers_model_parallel_error(detailed):
                raise RuntimeError(
                    "YourMT3 model failed to load inside Modal because transformers version is incompatible: "
                    f"{detailed}"
                ) from exc
            raise RuntimeError(f"YourMT3 model failed to load inside Modal: {detailed}") from exc

    @modal.method()
    def transcribe(self, normalized_audio_bytes: bytes) -> dict[str, object]:
        if not normalized_audio_bytes:
            raise ValueError("normalized_audio_bytes is empty")

        started = time.perf_counter()
        try:
            audio, sample_rate = self._decode_audio(normalized_audio_bytes)
            midi_result = self.model.transcribe(audio, sr=sample_rate)
            midi_bytes = self._midi_to_bytes(midi_result)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"YourMT3 transcription failed inside Modal: {exc.__class__.__name__}: {exc}"
            ) from exc

        return {
            "midi_bytes": midi_bytes,
            "provider_used": "yourmt3",
            "backend": "modal",
            "model_version": self.model_version,
            "timing": {"transcription_seconds": time.perf_counter() - started},
        }

    def _decode_audio(self, normalized_audio_bytes: bytes) -> tuple[object, int]:
        import librosa
        import numpy as np
        import soundfile as sf

        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "input.wav"
            wav_path.write_bytes(normalized_audio_bytes)
            audio, sample_rate = sf.read(str(wav_path), always_2d=False)

        if hasattr(audio, "ndim") and getattr(audio, "ndim") == 2:
            audio = np.mean(audio, axis=1)

        target_sr = 16000
        if sample_rate != target_sr:
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sr)
            sample_rate = target_sr

        return audio, sample_rate

    def _midi_to_bytes(self, midi_result: object) -> bytes:
        if isinstance(midi_result, (bytes, bytearray)):
            return bytes(midi_result)

        with tempfile.TemporaryDirectory() as tmp_dir:
            midi_path = Path(tmp_dir) / "output.mid"
            if hasattr(midi_result, "write"):
                midi_result.write(str(midi_path))
                return midi_path.read_bytes()
            if isinstance(midi_result, MidiFile):
                midi_result.save(str(midi_path))
                return midi_path.read_bytes()

        raise RuntimeError(f"Unsupported MIDI output type from mt3-infer: {type(midi_result).__name__}")
