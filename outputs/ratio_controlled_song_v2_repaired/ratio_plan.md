# Ratio Plan (v2)

- generation_id: `ratio_controlled_song_v2`
- duration_seconds: `120.0`
- bpm: `108`
- golden_climax_ts: `74.164079`
- section_boundaries_seconds: `[0.0, 28.32, 45.84, 74.164, 120.0]`
- phrase_ratio_target: `1.5`
- rhythm_ratio_target: `1.6666666666666667`
- interval_ratio_target: `1.25`
- density_ratio_target: `1.6`

## Notes
- Plan is authored before any note generation and used as the single generation source.
- Boundaries and rhythm cells are explicit to improve evaluator observability.
- Controls remain soft; warnings should still surface if compliance drops.
