# Taste Database Strategy (Retrieval/Feedback First)

## Product framing

- Branch: `cursor/music-brain-active`
- Core orientation: keep existing model integrations as analysis tools/witnesses, not autonomous composers.
- Proprietary value layer: a private taste database built from derived/indexed loop evidence + explicit user feedback.
- Default operation mode: retrieval-first recommendation and arrangement support.

## 1) Existing model role definition (tools/witnesses)

Required witnesses:
- BasicPitch (transcription witness)
- Demucs (source-separation witness)

Optional witnesses/tools:
- MT3
- Omnizart
- Moonbeam
- MusicBERT
- MIDI-GPT
- Text2MIDI

Model outputs are treated as evidence artifacts only:
- Store hash-linked references, confidence summaries, and tags.
- Do not store model weights, caches, or private local absolute paths in committed records.
- Do not treat model outputs as final truth; they inform retrieval ranking and user-review workflows.

## 2) Taste database architecture

Taste database is a derived/indexed memory layer:
- `taste_item`: canonical loop/entity record used for retrieval.
- `loop_candidate`: retrieval candidate record with witness-derived evidence and quality/risk flags.
- `user_feedback`: explicit human preference signal attached to loop IDs and taste item IDs.

Privacy and identity:
- Use stable hashed IDs (`*_id`, `*_hash`) for source references.
- Keep only redacted public-safe placeholders for local file locations (`<PRIVATE_LOCAL_PATH>/...`).
- Never commit raw audio payloads, private absolute paths, or local model artifacts.

## 3) Retrieval-first generation policy

Policy defaults:
- `retrieval_first = true`
- `generation_enabled = false`
- `reroll_enabled = false`
- `pattern_box_enabled = false`
- `training_allowed = false`

Execution meaning:
- Rank and retrieve existing loop candidates by taste memory + witness evidence + user feedback.
- Allow suggest/compare flows only; no autonomous generation or reroll loops.
- Gate any future generation behind explicit product/policy approval.

## 4) Feedback loop taxonomy

Core decision labels:
- `promote`, `keep`, `adapt`, `archive`, `reject`

Feedback focus categories:
- `groove`, `harmony`, `melody`, `rhythm`, `texture`, `arrangement`, `energy`, `mix`, `emotion`, `novelty`

Signal usage:
- Update aggregate taste scores and retrieval weights.
- Track disagreement and confidence drift across witnesses.
- Preserve reviewer intent and rationale without leaking private paths.

## 5) Training policy (disabled by default)

Training remains disabled unless all gate conditions are explicitly met:
1. Product owner approval recorded in strategy/governance docs.
2. Privacy leak scan passes with zero new leaks.
3. Dataset authorization and provenance audits pass.
4. Local-only execution plan is defined (no cloud training).
5. Reproducible rollback/disable plan is documented and tested.

Until all gates pass:
- `training_allowed = false` in schema defaults and runtime policy.
- Preference updates apply only to retrieval memory and ranking weights (non-training path).
