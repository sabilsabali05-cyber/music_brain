# ballad_2min_v1 Review Sheet

- Output ID: `ballad_2min_v1`
- Tempo: `78 BPM`
- Key: `A minor`
- Duration: `120.0 seconds (2:00)`
- Meter: `4/4`
- Section Structure: `intro -> verse -> hook -> bridge -> final_hook -> outro`

## Tracks / Stems
- `ballad_drums.mid`
- `ballad_bass.mid`
- `ballad_chords.mid`
- `ballad_lead.mid`
- `ballad_texture.mid`
- `ballad_full.mid`

## Note Counts (MIDI `note_on` with velocity > 0)
- `ballad_drums.mid`: `144`
- `ballad_bass.mid`: `92`
- `ballad_chords.mid`: `234`
- `ballad_lead.mid`: `108`
- `ballad_texture.mid`: `50`
- `ballad_full.mid`: `628`

## Model Usage
- Models checked: `moonbeam`, `musicbert`, `midigpt`, `text2midi`, `example_retrieval`
- Models actually used: `example_retrieval`
- Models skipped unavailable:
  - `moonbeam:disabled_or_missing_local_config`
  - `musicbert:disabled_or_missing_local_config`
  - `midigpt:disabled_or_missing_local_config`
  - `text2midi:disabled_or_missing_local_config`

## Generation Provenance
- Generated from trained models: `false`
- Generated from repo/data conditioning: `yes`
- Honest explanation: The result uses local symbolic example conditioning from `datasets/generative_training` (motif/arrangement constraints) plus a deterministic minor-ballad ruleset. It is not a newly trained model sample; it is retrieval + ruleset generation based on repository-local data and configuration.

## Human Review Checklist
- [ ] Chords feel emotional?
- [ ] Melody is hummable?
- [ ] Bass supports the progression?
- [ ] Drums leave space?
- [ ] Texture helps or clutters?
- [ ] Bridge works?
- [ ] Final hook lands?
- [ ] What to regenerate?
- [ ] What to keep?
