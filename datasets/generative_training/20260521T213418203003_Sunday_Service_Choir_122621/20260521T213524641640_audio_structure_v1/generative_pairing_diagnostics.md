# Generative Pairing Diagnostics - 20260521T213524641640_audio_structure_v1

## Examples by task type
- buildup_to_release: `19`
- call_response: `45`
- continuation: `39`
- groove_continuation: `37`
- harmony_continuation: `53`
- infill_missing_region: `52`
- melody_continuation: `6`
- motif_transformation: `22`
- phrase_continuation: `104`
- section_transition: `53`

## Boundary quality distribution
- `{"count": 430, "mean": 0.821568, "min": 0.315355, "p25": 0.842168, "p50": 0.90661, "p75": 0.91585, "max": 0.953549}`

## Phrase boundary weak by task
- `{"infill_missing_region": 27, "motif_transformation": 9}`

## Route-state unsuitable by content state
- `{"ambient_low_information": 53, "melodic_lead": 2, "rhythm_dominant": 74, "unknown": 4}`

## Recommended pairing strategy changes
- Increase phrase-like candidate generation from density/routing-change boundaries for tasks with high phrase_boundary_weak counts.
- Use evidence boosters for harmony/melody/call_response when routing labels are conservative in long-form choir sections.
- For dense targets with weak boundaries, expand context by one extra compatible window before excluding.
- Prioritize examples near thresholds by improving boundary evidence rather than lowering split thresholds.
