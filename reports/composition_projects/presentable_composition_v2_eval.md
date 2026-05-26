# Presentable Composition V2 Evaluation

- regenerated_v2: `true`
- selected_midi_path: `outputs/presentable_composition_from_draft_v2/selected/full.mid`
- v2_presentability_score: `0.793539`
- v2_ratio_compliance_score: `0.670152`
- v2_database_comparison_confidence: `0.453055`

## Evidence Impact
- repaired note parsing changed note_count from 0 to 368
- tempo/key/musicality are now computed from parsed note evidence instead of empty-note fallback
- candidate ranking uses evidence-derived control targets from repaired analysis

