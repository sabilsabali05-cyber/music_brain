from music_brain.schemas import ArtifactPaths, JobReport, LatencySeconds


def test_job_report_contains_required_fields() -> None:
    report = JobReport(
        track_id="trk_abc",
        input_filename="sample.mp3",
        checksum="deadbeef",
        duration_seconds=3.5,
        provider_requested="fake",
        provider_used="fake",
        fallback_used=False,
        fallback_reason=None,
        model_version="fake-transcriber-v0",
        backend="local_fake",
        status="success",
        latency_seconds=LatencySeconds(
            checksum=0.1,
            copy_input=0.1,
            ffmpeg_convert=0.2,
            transcription=0.3,
            total=0.7,
        ),
        artifacts=ArtifactPaths(
            input_audio="library/trk_abc/original/sample.mp3",
            normalized_audio="library/trk_abc/original/normalized.wav",
            full_mix_midi="library/trk_abc/midi/full_mix.mid",
            job_report="library/trk_abc/analysis/job_report.json",
        ),
        error=None,
    )

    payload = report.model_dump()
    assert payload["track_id"] == "trk_abc"
    assert payload["provider_used"] == "fake"
    assert payload["fallback_used"] is False
    assert payload["status"] == "success"
    assert payload["latency_seconds"]["total"] == 0.7
    assert payload["artifacts"]["full_mix_midi"].endswith("full_mix.mid")

