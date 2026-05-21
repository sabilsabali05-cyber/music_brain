# Performance Readiness: Kanye Sunday Service Test

- performance_id: `20260521T203518295255_Kanye_West_performs_I_Wonder_with_Tony_Williams_and_the_Sunday_Service_Choir`
- source_duration_seconds: `209.86195`
- segments_count: `3`
- transcription_windows_count: `3`
- successful_windows: `3`
- failed_windows: `0`
- total_midi_bytes: `20836`
- total_note_on_count: `2680`
- total_transcription_latency_seconds: `108.5636`
- merged_midi_path: `samples/segments/Kanye_West_performs_I_Wonder_with_Tony_Williams_and_the_Sunday_Service_Choir/20260521T203603254802_audio_structure_v1/merged/merged_performance.mid`
- validation_result: `success` (`tracks=1`, `messages=4633`, `note_on_count=2312`)

## Processing Completeness vs Cap

The run was fully processed despite the 3-window cap because segmentation produced exactly 3 windows, and all 3 were transcribed successfully.

## Recommendation for Next Scale Test

Proceed to one longer church-performance file with the same cautious staged flow:

1. Ingest one local long-form file.
2. Process with `max-windows=3` first to validate boundary quality and operational stability.
3. If stable (0 failures, clean benchmark/review), rerun the same manifest with `max-windows=6`.
4. Only move to full-window processing after these capped checkpoints pass.
