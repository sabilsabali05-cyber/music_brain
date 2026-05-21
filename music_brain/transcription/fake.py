from __future__ import annotations

from mido import Message, MetaMessage, MidiFile, MidiTrack

from .base import BaseTranscriber, TranscriptionRequest, TranscriptionResult


class FakeTranscriber(BaseTranscriber):
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        midi = MidiFile()
        track = MidiTrack()
        midi.tracks.append(track)

        track.append(MetaMessage("set_tempo", tempo=500000, time=0))
        track.append(Message("program_change", program=0, time=0))

        note_plan = [
            (60, 240),
            (64, 240),
            (67, 240),
            (72, 360),
        ]

        for pitch, ticks in note_plan:
            track.append(Message("note_on", note=pitch, velocity=88, time=0))
            track.append(Message("note_off", note=pitch, velocity=0, time=ticks))

        midi.save(str(request.output_midi_path))
        return TranscriptionResult(
            provider_used="fake",
            backend="local_fake",
            model_version="fake-transcriber-v0",
            fallback_used=False,
            fallback_reason=None,
        )
