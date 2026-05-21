from music_brain.preflight import run_preflight


def test_preflight_result_structure(monkeypatch, tmp_path) -> None:
    library_root = tmp_path / "library"
    monkeypatch.setenv("MUSIC_BRAIN_LIBRARY_ROOT", str(library_root))
    monkeypatch.setenv("MUSIC_BRAIN_PROVIDER", "fake")
    monkeypatch.setenv("MUSIC_BRAIN_BACKEND", "local_fake")

    report = run_preflight()

    assert isinstance(report.ok, bool)
    assert report.provider == "fake"
    assert report.backend == "local_fake"
    assert report.library_root.endswith("/library") or report.library_root.endswith("\\library")

    check_names = {check.name for check in report.checks}
    assert "python_version" in check_names
    assert "cwd" in check_names
    assert "project_import" in check_names
    assert "ffmpeg_on_path" in check_names
    assert "provider_backend_config" in check_names
    assert "library_create" in check_names
    assert "library_write_permission" in check_names
    assert "configured_backend_usable" in check_names
