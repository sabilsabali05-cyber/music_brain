from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def create_test_tone(output_path: Path, *, duration_seconds: float = 5.0, sample_rate: int = 44100) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_samples = int(duration_seconds * sample_rate)
    amplitude = 0.35
    max_int16 = 32767

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(total_samples):
            t = i / sample_rate
            frequency = 440.0 if t < (duration_seconds / 2.0) else 659.25
            sample = amplitude * math.sin(2.0 * math.pi * frequency * t)
            wav_file.writeframes(struct.pack("<h", int(sample * max_int16)))

    return output_path


def main() -> None:
    output = Path("samples") / "test_tone.wav"
    written = create_test_tone(output)
    print(f"Generated test audio: {written.resolve().as_posix()}")


if __name__ == "__main__":
    main()
