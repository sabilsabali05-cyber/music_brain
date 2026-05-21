from pathlib import Path

from music_brain.storage import TrackStorage


def test_artifact_layout_paths() -> None:
    storage = TrackStorage(Path("library"))
    track_id = "trk_test_123"
    paths = storage.build_paths(track_id=track_id, input_filename="song.mp3")

    assert paths.track_root == Path("library") / track_id
    assert paths.input_audio == Path("library") / track_id / "original" / "song.mp3"
    assert paths.normalized_audio == Path("library") / track_id / "original" / "normalized.wav"
    assert paths.full_mix_midi == Path("library") / track_id / "midi" / "full_mix.mid"
    assert paths.job_report == Path("library") / track_id / "analysis" / "job_report.json"

