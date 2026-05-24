# Generated Artifact Policy

## Scope

This policy governs generated outputs, reports, local config traces, and media artifacts produced by local automation.

## Allowed To Commit

- Source code, tests, and deterministic scaffolding scripts.
- Integration reports that are redacted and do not expose private absolute paths.
- Small text/JSON status files required to prove truthful pipeline behavior.
- Non-sensitive template files (for example feedback templates and usage docs).

## Must Not Commit

- Raw media inputs or copied private source media.
- Local-only config files containing executable/plugin absolute paths.
- Private plugin paths or machine-identifying strings in reports.
- Rendered WAV outputs unless explicitly approved for commit.
- Fake success indicators (for example claiming final WAV exists without verification).

## Required Redaction Rules

- Replace absolute local paths with redacted labels or booleans.
- Report plugin/local setup as capability booleans, not path values.
- Keep privacy/debt findings explicit; do not suppress failures.
- Preserve blocker details as category labels (for example `reaper_executable_path_missing_or_unavailable`) instead of local paths.

## Existing Failure Handling

- If privacy scan fails, report the failing markers and paths in integration outputs.
- Do not silently delete user outputs; prefer policy gates and follow-up cleanup tasks.
- Distinguish pre-existing debt from new branch-introduced leaks.
- Keep generated artifacts honest: missing WAV, missing transformed MIDI, and blocked training must stay explicitly marked.

## Pipeline Gate Expectations

- `wav_rendered=true` only when a verifiable `final.wav` exists and passes validation.
- `chordpotion_status` may be `missing_config` or attempted states; never claim plugin transform success without captured artifact.
- `trained_selector_used=true` only when both trained artifact and confirming report exist.
- No cloud calls in complete local pipeline command.
