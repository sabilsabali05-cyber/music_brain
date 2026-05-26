# Model Witness Audit

- generated_at: `2026-05-26T12:59:50.985379+00:00`
- gate_rule: `use witness only when configured, installed, and smoke_test_passed are all true`
- total_witnesses: `7`
- available: `0`
- blocked: `7`
- required_blocked: `1`

## Witnesses
- `Moonbeam` (`moonbeam`): available=`false` configured=`false` smoke_test_passed=`false` reason=`disabled`
- `MusicBERT` (`musicbert`): available=`false` configured=`false` smoke_test_passed=`false` reason=`disabled`
- `MIDI-GPT` (`midigpt`): available=`false` configured=`false` smoke_test_passed=`false` reason=`disabled`
- `Text2MIDI` (`text2midi`): available=`false` configured=`false` smoke_test_passed=`false` reason=`disabled`
- `Transcription witnesses` (`transcription_witnesses`): available=`false` configured=`false` smoke_test_passed=`false` reason=`disabled_or_missing_local_config`
- `Source separation witness` (`source_separation_witness`): available=`false` configured=`false` smoke_test_passed=`false` reason=`disabled_or_missing_local_config`
- `Texture witness` (`texture_witness`): available=`false` configured=`false` smoke_test_passed=`false` reason=`no_texture_backend_configured`

## Blockers
- midigpt:not_configured
- moonbeam:not_configured
- musicbert:not_configured
- source_separation_witness:no_local_demucs_backend
- text2midi:not_configured
- texture_witness:no_texture_backend_configured
- transcription_witnesses:no_local_transcription_backend
