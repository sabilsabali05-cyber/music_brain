from __future__ import annotations

import os
import tempfile
import time
from io import BytesIO
from pathlib import Path

import modal
from mido import Message, MetaMessage, MidiFile, MidiTrack

app = modal.App("music-brain-v2")
image = modal.Image.debian_slim(python_version="3.11").pip_install("mido>=1.3")
yourmt3_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git")
    .pip_install(
        "mido>=1.3",
        "numpy>=1.26",
        "librosa>=0.10",
        "pretty_midi>=0.2",
        "note-seq>=0.0.5",
        "git+https://github.com/magenta/mt3.git",
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


@app.cls(image=yourmt3_image, gpu=_resolve_modal_gpu(), timeout=600)
class YourMT3ModalRunner:
    """Experimental YourMT3 runner with warm-loaded model state."""

    @modal.enter()
    def load_model(self) -> None:
        self.model_version = os.getenv("MUSIC_BRAIN_YOURMT3_MODEL_VERSION", "yourmt3-modal-experimental-v0")
        self._model = None
        self._model_error: str | None = None

        try:
            # TODO: replace this placeholder import path with the finalized
            # YourMT3 inference wrapper used by production containers.
            import mt3  # type: ignore[import-not-found]  # noqa: F401
            self._model = "loaded"
        except Exception as exc:  # noqa: BLE001
            self._model_error = f"YourMT3 load failed: {exc.__class__.__name__}: {exc}"

    @modal.method()
    def transcribe(self, normalized_audio_bytes: bytes) -> dict[str, object]:
        if not normalized_audio_bytes:
            raise ValueError("normalized_audio_bytes is empty")
        if self._model is None:
            raise RuntimeError(self._model_error or "YourMT3 model is not loaded")

        started = time.perf_counter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "input.wav"
            midi_path = Path(tmp_dir) / "output.mid"
            wav_path.write_bytes(normalized_audio_bytes)
            self._run_experimental_yourmt3(wav_path=wav_path, midi_path=midi_path)
            midi_bytes = midi_path.read_bytes()

        return {
            "midi_bytes": midi_bytes,
            "provider_used": "yourmt3",
            "backend": "modal",
            "model_version": self.model_version,
            "timing": {"transcription_seconds": time.perf_counter() - started},
        }

    def _run_experimental_yourmt3(self, *, wav_path: Path, midi_path: Path) -> None:
        try:
            import mt3  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"YourMT3 import failed at inference stage: {exc}") from exc

        # Experimental feasibility probe: look for a callable wrapper exported by
        # the installed mt3 package. If no known callable is exposed, fail loudly.
        if hasattr(mt3, "transcribe_audio_to_midi"):
            mt3.transcribe_audio_to_midi(str(wav_path), str(midi_path))
            return
        if hasattr(mt3, "run_inference"):
            mt3.run_inference(str(wav_path), str(midi_path))
            return

        raise RuntimeError(
            "YourMT3 inference entrypoint not found in installed mt3 package. "
            "This experimental spike requires wiring the exact inference wrapper."
        )
