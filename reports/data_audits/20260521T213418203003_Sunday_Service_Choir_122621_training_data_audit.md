# Training Data Audit - 20260521T213418203003_Sunday_Service_Choir_122621

## 1. Artifacts generated
- source audio reference: `C:/Users/izzyo/Downloads/Sunday Service Choir 122621.mp3`
- active analysis path: `C:\Users\izzyo\ai-composer\music_brain\samples\analysis\Sunday_Service_Choir_122621\20260521T213424878654_modal_librosa_dense\structure_analysis.json`
- active segments manifest: `C:/Users/izzyo/ai-composer/music_brain/samples/segments/Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/segments_manifest.json`
- window MIDI count: `54`
- merged MIDI path: `C:\Users\izzyo\ai-composer\music_brain\samples\segments\Sunday_Service_Choir_122621\20260521T213524641640_audio_structure_v1\merged\merged_performance.mid`
- merge report path: `C:/Users/izzyo/ai-composer/music_brain/samples/segments/Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/merged/merge_report.json`
- feature pack files: `{"rhythm_features": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/rhythm_features.json", "harmony_features": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/harmony_features.json", "tags": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/tags.json", "feature_pack_manifest": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/feature_pack_manifest.json"}`
- AI JSONL path: `C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/ai_training_records.jsonl`

## 2. Strongly usable data
- MIDI note events and transcription window timing
- Merged MIDI artifact (if present) and stitch diagnostics
- Raw rhythm density and velocity statistics
- Pitch-class histograms and transcription statuses

## 3. Usable as weak labels
- Chord label candidates
- Rhythm/chord region candidates
- Motif and rhythm-family candidates
- Ontology/semantic interpretation tags

## 4. Experimental / low-confidence data
- Rhythm-family classifications without strong calibration support
- Philosophical rhythm concept labels
- Syncopation and groove proxy inferences
- Motif ranking/importance heuristics

## 5. Missing data
- Essentia descriptors
- musicnn semantic tags
- external model consensus
- human verification labels
- beat/downbeat external witness

## 6. AI-readiness assessment
- Is ai_training_records.jsonl usable? `True`
- Safe for training now: `["raw_observation and derived_observation records", "high/medium reliability windows", "records with complete provenance fields"]`
- Weak labels only: `["heuristic_estimate records", "weak_label and interpretive_weak_label records"]`
- Exclude/downweight: `["failed/missing reliability windows", "review_required records", "ambiguous labels without corroboration"]`

## 7. Dataset inclusion decision
- decision: `accepted`
- recommended split: `train`

## Field-Level Training Usability
- accepted_records may intentionally be observation-only to avoid weak-label contamination.
- safe fields: `["timing boundaries (start/end/duration)", "note count and note density", "velocity statistics", "pitch-class histograms", "transcription reliability score and recommended weight", "feature/provenance references"]`
- weak-label fields: `["chord label candidates", "rhythm-family candidates", "motif group references", "interpretive ontology tags"]`
- review-required fields: `["ambiguous rhythm-family outputs", "low-confidence harmony/rhythm labels", "interpretive philosophical tags", "conflicting model-derived interpretations"]`
- train on raw timing/MIDI now: `True`
- semantic/rhythm/harmony labels status: `weak_or_review_only`

## 8. Recommended next steps
- Collect human verification for high-impact weak labels.
- Use accepted/audio_midi_only splits for baseline training first.
- Review quarantined/review records before inclusion.

## Routing and Label Upgrade Readiness
- asset_type: `performance_recording`
- content_state_counts: `{"unknown": 1094, "ambient_low_information": 90, "percussive_only": 1, "rhythm_dominant": 355, "melodic_lead": 113, "harmonic_dominant": 119}`
- content_state_counts_by_granularity: `{"segment": {"unknown": 54}, "window": {"unknown": 54}, "rhythm_region": {"ambient_low_information": 90, "unknown": 386, "percussive_only": 1, "rhythm_dominant": 355}, "chord_region": {"unknown": 600, "melodic_lead": 113, "harmonic_dominant": 119}}`
- labels_suppressed_by_routing: `1835`
- likely_false_suppressions: `100`
- harmonic_evidence_regions_suppressed: `100`
- upgrade_candidates: `51`
- upgrade_candidates_by_label_family: `{"semantic": 51}`
- downgrade_or_suppress_candidates: `1719`
- downgrade_or_suppress_candidates_by_label_family: `{"semantic": 1244, "rhythm": 356, "harmony": 119}`
- needs_human_review_candidates: `0`
- routing_improves_training_safety: `True`
- recommended_routing_calibration_status: `needs_recalibration`
