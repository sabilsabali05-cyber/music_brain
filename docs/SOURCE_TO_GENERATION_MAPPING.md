# Source -> Generation Mapping

`features/source_understanding/source_to_generation.py` maps source-understanding rows into concrete generation controls.

## Mapping Coverage

- confidence -> arrangement energy curve
- confidence + tags -> rhythmic density
- harmonic tags + control hints -> harmonic complexity
- motif control hints -> motif repetition
- tempo hint -> tempo range
- preservation tags -> preserve controls
- avoid tags -> risk controls

## Example

- input tags: `["high_energy", "harmonic_rich", "groove_lock"]`
- output:
  - higher density
  - higher harmonic complexity
  - preserve `groove_lock`
  - confidence-weighted arrangement curve

## Policy

- Mapping is deterministic and local.
- Mapping never assumes fake plugin/VST behavior.
- Mapping does not require WAV rendering.
