# Theory to Generation Mapping

The theory layer emits `GenerationHooks` that map directly to generation controls.

## Mapped fields

- `target_tempo_range`: inferred from rhythm identity.
- `target_key_or_mode`: tonal center hint or ambiguous modal fallback.
- `chord_movement_strategy`: functional, modal, or controlled chromatic movement.
- `bass_motion_strategy`: root/fifth anchors, stepwise support, or pedal.
- `voice_leading_strategy`: preserve common tones and step resolution.
- `motif_development_strategy`: repeat/transform or compact call-response.
- `rhythm_strategy`: pocket-first, sparse grid, or syncopation emphasis.
- `form_strategy`: loop-first, through-composed, or hybrid.
- `texture_strategy`: minimal roles or layered atmosphere.
- `avoid_list`: random clashes and low-register mud.
- `preserve_list`: valuable weirdness and motif anchors.
- `tension_curve`: normalized phrase tension arc.
- `density_curve`: normalized layering arc.
- `confidence`: confidence-weighted usefulness estimate.
- `source_records_used`: source theory record ids.

## Safety/policy

- No cloud/model-training controls are used.
- Hooks are generated only from local corpus metadata/intelligence outputs.
- Ambiguous harmony is handled with `not_applicable` paths, not forced functional labels.
