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
scripts\dev.cmd make-clip samples\input\my_song.wav 30
scripts\dev.cmd analyze-structure-local "samples/input/my_song.wav"
scripts\dev.cmd analyze-structure-modal "samples/input/my_song.wav"
scripts\dev.cmd analyze-structure-modal-dense "samples/input/my_song.wav"
scripts\dev.cmd audio-analysis-diagnostics
scripts\dev.cmd segment-audio "C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3" 60
scripts\dev.cmd segment-audio-structure "samples/input/my_song.wav" 60
scripts\dev.cmd segment-audio-structure-dense "samples/input/my_song.wav" 60
scripts\dev.cmd segment-audio-structure-tuned "samples/input/my_song.wav" 60 0.45
scripts\dev.cmd sweep-audio-structure-dense "samples/input/my_song.wav" 60
scripts\dev.cmd inspect-latest-segments
scripts\dev.cmd compare-segmentations "samples/segments/Varud_-_Sigur_Ros_Valtari"
scripts\dev.cmd transcribe-windows "<manifest_path>" 2
scripts\dev.cmd benchmark-segments "<manifest_path>"
scripts\dev.cmd transcribe-yourmt3 samples\clips\my_song_clip_0s_30s.wav
scripts\dev.cmd clip-and-transcribe-yourmt3 samples\input\my_song.wav 30
scripts\dev.cmd benchmark-track library\trk_20260521T103733Z_e3513afc22
scripts\dev.cmd validate-latest
scripts\dev.cmd validate-track library\trk_20260521T103733Z_e3513afc22
scripts\dev.cmd commit-checkpoint
scripts\dev.cmd commit-checkpoint "My commit message"
```

When paths contain spaces on Windows, always quote them, for example:

```powershell
scripts\dev.cmd clip-and-transcribe-yourmt3 "C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3" 30
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
- If Modal logs show `No module named 'transformers.utils.model_parallel_utils'`, pin `transformers==4.41.2` in the Modal image.
- First run may be slow because model checkpoints may download.
- A Modal Volume caches checkpoints at `MT3_CHECKPOINT_DIR=/models/mt3_checkpoints`.
- Later runs should be faster as cache warms.
- If `mt3-infer` import/model load/transcription fails, the job fails honestly and writes `job_report.json` with error details.
- There is no silent fallback to fake or Basic Pitch.

Known-good smoke command:

```powershell
scripts\dev.cmd smoke-yourmt3
```

Expected success fields in `job_report.json`:

- `provider_requested = "yourmt3"`
- `provider_used = "yourmt3"`
- `backend = "modal"`
- `status = "success"`
- `fallback_used = false`
- `fallback_reason = null`
- `model_version = "yourmt3-modal-experimental-v1"` (or another non-empty Modal model version)

Recent successful run reference:

- `job_report`: `library/trk_20260521T103733Z_e3513afc22/analysis/job_report.json`
- `latency_seconds.total`: `20.0215` seconds
- `latency_seconds.transcription`: `19.8068` seconds

## Validating a completed track

Validate an explicit track folder:

```powershell
python scripts/validate_track.py library/trk_20260521T103733Z_e3513afc22
scripts\dev.cmd validate-track library/trk_20260521T103733Z_e3513afc22
```

Validate the newest track in `library/`:

```powershell
scripts\dev.cmd validate-latest
```

Validation checks include:

- `analysis/job_report.json` exists and parses
- `status == "success"`
- `provider_used == "yourmt3"`
- `backend == "modal"`
- `fallback_used == false`
- `original/normalized.wav` exists
- `midi/full_mix.mid` exists and is non-empty
- MIDI parses with `mido` and reports track/message counts

## Testing YourMT3 on a real clip

Use only audio you own or have rights to process.

Preferred one-command flow:

```powershell
scripts\dev.cmd clip-and-transcribe-yourmt3 "samples/input/my_song.wav" 30
```

This command:

- creates a short clip under `samples/clips/`
- runs `submit_track.py` with `yourmt3/modal` config
- auto-detects the produced track folder from machine-readable output
- runs `validate_track.py`
- runs `benchmark_track.py`
- prints a final summary with track folder, report path, MIDI path, validation result, and benchmark metrics

Manual step-by-step flow (if you want to run each stage separately):

1. Put your file in `samples/input/` (this folder is git-ignored).
2. Make a short clip (default 30s):

```powershell
python scripts/make_clip.py samples/input/my_song.wav --seconds 30
```

Or via dev runner:

```powershell
scripts\dev.cmd make-clip samples/input/my_song.wav 30
```

3. Transcribe the clip with YourMT3:

```powershell
$env:MUSIC_BRAIN_PROVIDER="yourmt3"
$env:MUSIC_BRAIN_BACKEND="modal"
python submit_track.py samples/clips/my_song_clip_0s_30s.wav
```

4. Validate the resulting track folder:

```powershell
scripts\dev.cmd validate-track library/<track_id>
```

5. Benchmark the resulting track folder:

```powershell
python scripts/benchmark_track.py library/<track_id>
scripts\dev.cmd benchmark-track library/<track_id>
```

`benchmark_track.py` prints:

- `track_id`, `status`, `provider_used`, `backend`
- audio duration and transcription/total latency
- MIDI file size, track/message counts, and `note_on` count

## Phrase-aware long performances

Hour-long performances should not be sent as one transcription request. The long-audio scaffold separates:

- `musical_segment`: musically meaningful phrase/section/gesture concept
- `transcription_window`: practical context-padded audio window sent to YourMT3

Important behavior:

- Fixed chunks are the fallback baseline, not the end goal.
- The hybrid mode is currently a scaffold and records this explicitly in the manifest strategy.
- Every segment stores previous/next links for timeline context.
- Every window stores core interval plus context-padded interval.
- Future database retrieval should fetch: target segment + neighbor segments + parent performance context.

### Segmentation strategies

- `fixed`: stable baseline fallback (`fixed_with_context`).
- `energy`: conservative `energy_v1` low-energy boundary candidates.
- `hybrid`: current scaffold (`hybrid_scaffold_with_energy_boundaries`) that can still fall back when uncertain.

Boundary labels are candidate signals, not ground truth. Current reasons include:

- `fixed_interval_fallback`
- `low_energy_boundary`
- `max_window_split`
- `uncertain_fallback`

Future improvements can layer in beat/bar grid, chroma/harmonic shifts, recurrence or self-similarity novelty, and motif/section detectors.

Safe first run for long audio:

```powershell
scripts\dev.cmd segment-audio "C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3" 60
scripts\dev.cmd inspect-latest-segments
scripts\dev.cmd transcribe-windows "<manifest_path>" 2
scripts\dev.cmd benchmark-segments "<manifest_path>"
```

This keeps GPU usage bounded while proving manifest + context + resume behavior.

## Comparing segmentation strategies

Every segmentation run is saved separately under:

`samples/segments/<safe_source_name>/<timestamp>_<strategy_used>/`

Each run contains its own `segments_manifest.json` and `windows/` directory, so old runs are not overwritten.
This matters because window transcriptions are expensive and should stay reproducible.

Convenience pointers and comparison:

- `latest_manifest.txt` is a convenience pointer only.
- Use `inspect-segments` or `inspect-latest-segments` to inspect one run.
- Use `compare-segmentations` to compare fixed/energy/hybrid runs side-by-side.

Example:

```powershell
scripts\dev.cmd segment-audio "C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3" 60 energy
scripts\dev.cmd inspect-latest-segments
scripts\dev.cmd compare-segmentations "samples/segments/Varud_-_Sigur_Ros_Valtari"
```

## Reviewing segmentation quality

Before spending more GPU on transcription, generate a human-readable review report:

```powershell
scripts\dev.cmd review-segments "samples/segments/Varud_-_Sigur_Ros_Valtari/20260521T171256329037_audio_structure_v1/segments_manifest.json"
```

This writes:

`reports/segment_reviews/<safe_source_name>_<run_id>.md`

The report summarizes:

- strategy requested/used and fallback status
- available/missing analysis features
- candidate vs accepted boundary counts
- segment-by-segment boundary evidence and links
- transcription window coverage and statuses
- review prompts for threshold tuning and future beat/bar snapping

## Pre-MIDI audio structure analysis

This flow analyzes audio structure before MIDI transcription:

```powershell
scripts\dev.cmd analyze-structure "samples/input/my_song.wav"
scripts\dev.cmd segment-audio-structure "samples/input/my_song.wav" 60
scripts\dev.cmd inspect-latest-segments
scripts\dev.cmd transcribe-windows "<manifest_path>" 2
scripts\dev.cmd benchmark-segments "<manifest_path>"
```

Notes:

- Boundaries are candidate signals, not guaranteed phrase truth.
- Fallback to fixed windows is expected on ambiguous ambient material.
- `audio_structure` uses conservative evidence from available features before transcription.
- Future improvements can add beat/bar snapping, chroma recurrence structure, and learned MERT/CLAP-style embeddings.

## Richer pre-MIDI analysis with Modal/librosa

Use two analysis backends:

- `local_light`: dependency-safe local analyzer, limited but robust on Windows Python 3.14.
- `modal_librosa`: richer CPU-only analyzer on Modal image (no GPU), with chroma/timbre/novelty features.

This does not change YourMT3 model logic and does not require transcription to run.

Preferred flow:

```powershell
scripts\dev.cmd analyze-structure-modal "C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3"
scripts\dev.cmd segment-audio-structure "C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3" 60
scripts\dev.cmd inspect-latest-segments
scripts\dev.cmd compare-segmentations "samples/segments/Varud_-_Sigur_Ros_Valtari"
```

Guidance:

- run `analyze-structure-local` when Modal is unavailable
- run `analyze-structure-modal` when you want richer harmonic/timbral cues
- boundaries remain candidate evidence, not ground truth phrase labels

Tuning experiment helper:

```powershell
scripts\dev.cmd segment-audio-structure-tuned "C:\Users\izzyo\Downloads\Varud - Sigur Ros (Valtari).mp3" 60 0.45
```

This keeps prior runs intact and records tuning values in `segmentation_parameters` inside each manifest.

## Candidate density and boundary generation

Threshold tuning only helps when candidate generation is rich enough. If the analyzer emits too few audio-derived candidates, segmentation selection cannot invent new phrase boundaries.

Use candidate-generation controls in `scripts/analyze_audio_structure.py`:

- `--candidate-density conservative|normal|dense`
- `--peak-pick-threshold <float>`
- `--min-boundary-distance-seconds <float>`
- `--max-candidates <int>`

Dense analysis generates more candidate boundaries, but does **not** automatically accept them as phrase splits. Selection in `segment_audio.py` still applies musical constraints (thresholds, spacing, duration limits).

Fixed coverage windows remain separate from phrase boundaries:

- fixed coverage candidates keep timeline/window coverage behavior
- fixed candidates are excluded from phrase-boundary acceptance by default
- use `--allow-fixed-candidates` in segmentation only when you explicitly want that override

Dense Modal analysis convenience command:

```powershell
scripts\dev.cmd analyze-structure-modal-dense "samples/input/my_song.wav"
scripts\dev.cmd segment-audio-structure-dense "samples/input/my_song.wav" 60
```
