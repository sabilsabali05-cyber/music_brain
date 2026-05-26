# Source Loop Extraction Report

- generated_at: `2026-05-26T22:33:14.315841+00:00`
- considered_controlled_batch_rows: `25`
- extracted_clip_rows: `19`
- actual_source_audio_snippets_extracted: `19`
- eligible_for_buddy_generation_count: `19`
- missing_local_path_count: `0`
- missing_audio_file_count: `0`
- extraction_failures_count: `6`

## Witness Availability Snapshot
- available: `none`
- unavailable: `midigpt, moonbeam, musicbert, source_separation_witness, text2midi, texture_witness, transcription_witnesses`

## Policy
- no_training: `True`
- no_cloud_default: `True`
- source_audio_modified: `False`
- source_audio_snippets_committed: `False`

## Hard Gate
- only clips with local_audio_clip_exists=true are eligible for buddy generation

## Limitations
- Tempo/key analysis mixes filename hints with lightweight local waveform proxies.
- No cloud backends were called in extraction.
