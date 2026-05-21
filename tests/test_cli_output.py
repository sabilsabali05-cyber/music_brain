from pathlib import Path

import submit_track
from scripts.create_test_audio import create_test_tone


def test_cli_success_output_contains_required_fields(monkeypatch, tmp_path: Path, capsys) -> None:
    input_wav = tmp_path / "sample.wav"
    create_test_tone(input_wav, duration_seconds=0.2)

    library_root = tmp_path / "library"
    monkeypatch.setenv("MUSIC_BRAIN_LIBRARY_ROOT", str(library_root))
    monkeypatch.setenv("MUSIC_BRAIN_PROVIDER", "fake")
    monkeypatch.setenv("MUSIC_BRAIN_BACKEND", "local_fake")

    def fake_convert_to_wav(input_path: Path, output_path: Path) -> None:
        output_path.write_bytes(input_path.read_bytes())

    monkeypatch.setattr("submit_track.convert_to_normalized_wav", fake_convert_to_wav)
    monkeypatch.setattr("sys.argv", ["submit_track.py", str(input_wav)])

    submit_track.main()

    output = capsys.readouterr().out
    assert "provider_used: fake" in output
    assert "backend: local_fake" in output
    assert "midi_path:" in output
    assert "job_report:" in output


def test_cli_failure_output_contains_stage_and_report(monkeypatch, tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing.wav"
    monkeypatch.setenv("MUSIC_BRAIN_LIBRARY_ROOT", str(tmp_path / "library"))
    monkeypatch.setenv("MUSIC_BRAIN_PROVIDER", "fake")
    monkeypatch.setenv("MUSIC_BRAIN_BACKEND", "local_fake")
    monkeypatch.setattr("sys.argv", ["submit_track.py", str(missing)])

    try:
        submit_track.main()
    except SystemExit as exc:
        assert exc.code == 1

    output = capsys.readouterr().out
    assert "status: failed" in output
    assert "failing_stage: init" in output
    assert "job_report:" in output
