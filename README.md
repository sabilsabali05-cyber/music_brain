# music_brain V2 MVP (transcription control-plane)

This repo currently supports:

- local fake transcription backend (`provider=fake`, `backend=local_fake`)
- remote Modal fake transcription backend (`provider=fake`, `backend=modal_fake`)

Real YourMT3/MT3 inference is intentionally not implemented yet.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Install ffmpeg on Windows:

```powershell
winget install Gyan.FFmpeg
```

4. Close and reopen PowerShell, then verify:

```powershell
ffmpeg -version
```

## Local fake smoke test

```powershell
python submit_track.py --preflight
python scripts/create_test_audio.py
python submit_track.py samples/test_tone.wav
```

Expected `job_report.json` highlights:

- `provider_requested = "fake"`
- `provider_used = "fake"`
- `backend = "local_fake"`
- `model_version = "fake-transcriber-v0"`
- `fallback_used = false`
- `fallback_reason = null`

## Remote Modal fake smoke test

Install and configure Modal credentials:

```powershell
modal setup
```

Set temporary PowerShell environment variables:

```powershell
$env:MUSIC_BRAIN_PROVIDER="fake"
$env:MUSIC_BRAIN_BACKEND="modal_fake"
```

Then run:

```powershell
python submit_track.py --preflight
python scripts/create_test_audio.py
python submit_track.py samples/test_tone.wav
```

Expected `job_report.json` highlights:

- `provider_requested = "fake"`
- `provider_used = "fake"`
- `backend = "modal_fake"`
- `model_version = "modal-fake-transcriber-v0"`
- `fallback_used = false`
- `fallback_reason = null`
- `status = "success"`

## Notes

- `provider=yourmt3` with `backend=modal` is reserved for the next phase and currently returns a clear not-implemented error.
- The CLI always writes `job_report.json`, including failures.
