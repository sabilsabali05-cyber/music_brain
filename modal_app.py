from __future__ import annotations

import os
import subprocess
import tempfile
import time
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
        "mt3-infer[torch]",
    )
    .run_commands("git lfs install --system")
    .env({"MT3_CHECKPOINT_DIR": MT3_CHECKPOINT_DIR})
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
