# music_brain V2 MVP (transcription control-plane)

This repo currently supports:

- local fake transcription backend (`provider=fake`, `backend=local_fake`)
- remote Modal fake transcription backend (`provider=fake`, `backend=modal_fake`)
- experimental YourMT3 on Modal (`provider=yourmt3`, `backend=modal`)

The YourMT3 path is an experimental feasibility spike and may fail while dependencies/inference wiring are being resolved.

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

## Common commands

Use the task runner to avoid retyping long sequences:

- On Windows, prefer `scripts\dev.cmd` to avoid PowerShell execution policy issues.
- If Cursor cannot see `git` or `ffmpeg` but normal PowerShell can, restart Cursor or open a new terminal.
- The dev runner auto-discovers Git and ffmpeg on Windows using common install paths when Cursor's PATH is incomplete.

```powershell
scripts\dev.cmd doctor
scripts\dev.cmd test
scripts\dev.cmd deploy-modal
scripts\dev.cmd deploy-modal-utf8
scripts\dev.cmd smoke-local-fake
scripts\dev.cmd smoke-modal-fake
scripts\dev.cmd smoke-yourmt3
scripts\dev.cmd logs-modal
scripts\dev.cmd preflight-yourmt3
scripts\dev.cmd commit-checkpoint
scripts\dev.cmd commit-checkpoint "My commit message"
```

Troubleshooting:

- If Modal deploy fails with `'charmap' codec can't encode character`, run:

```powershell
scripts\dev.cmd deploy-modal-utf8
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

- The CLI always writes `job_report.json`, including failures.

## Experimental YourMT3 Modal spike

This path is intentionally experimental. It attempts real YourMT3 execution in a Modal GPU container and fails honestly if model loading/inference is not ready.

PowerShell flow:

```powershell
pip install -r requirements.txt
modal setup
modal deploy modal_app.py
$env:MUSIC_BRAIN_PROVIDER="yourmt3"
$env:MUSIC_BRAIN_BACKEND="modal"
python submit_track.py --preflight
python scripts/create_test_audio.py
python submit_track.py samples/test_tone.wav
```

Expected success fields in `job_report.json`:

- `provider_requested = "yourmt3"`
- `provider_used = "yourmt3"`
- `backend = "modal"`
- `model_version = "<non-empty>"`
- `fallback_used = false`
- `fallback_reason = null`
- `status = "success"`

Expected failure behavior:

- job status is `failed`
- `provider_used` remains `"none"`
- failure details are present in `error.stage`, `error.message`, and `error.exception_type`
- no silent fallback to fake or any other model

`local_fake` and `modal_fake` remain the stable control-plane test paths. They are for plumbing validation only and must not be silently used when `provider=yourmt3` is requested.

### Fixing/using the real mt3-infer YourMT3 backend

- The Modal YourMT3 runner uses `mt3-infer` inside the Modal image (not your local Windows Python env).
- The Modal image must include `git-lfs` because `mt3-infer` checkpoint download pulls LFS-tracked assets.
- If Modal logs show `No module named 'pytorch_lightning'`, pin and include `pytorch-lightning==2.6.1` in the Modal image.
- First run may be slow because model checkpoints may download.
- A Modal Volume caches checkpoints at `MT3_CHECKPOINT_DIR=/models/mt3_checkpoints`.
- Later runs should be faster as cache warms.
- If `mt3-infer` import/model load/transcription fails, the job fails honestly and writes `job_report.json` with error details.
- There is no silent fallback to fake or Basic Pitch.
