from __future__ import annotations

from io import BytesIO

import modal
from mido import Message, MetaMessage, MidiFile, MidiTrack

app = modal.App("music-brain-v2")
image = modal.Image.debian_slim(python_version="3.11").pip_install("mido>=1.3")


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
