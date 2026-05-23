# Training Data Audit - 20260521T213418203003_Sunday_Service_Choir_122621

## 1. Artifacts generated
- source audio reference: `<PRIVATE_LOCAL_PATH>/Downloads/Sunday Service Choir 122621.mp3`
- active analysis path: `<PRIVATE_LOCAL_PATH>\ai-composer\music_brain\samples\analysis\Sunday_Service_Choir_122621\20260521T213424878654_modal_librosa_dense\structure_analysis.json`
- active segments manifest: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/segments/Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/segments_manifest.json`
- window MIDI count: `54`
- merged MIDI path: `<PRIVATE_LOCAL_PATH>\ai-composer\music_brain\samples\segments\Sunday_Service_Choir_122621\20260521T213524641640_audio_structure_v1\merged\merged_performance.mid`
- merge report path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/segments/Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/merged/merge_report.json`
- feature pack files: `{"rhythm_features": "<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/rhythm_features.json", "harmony_features": "<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/harmony_features.json", "tags": "<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/tags.json", "meter_time_features": "<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/rhythm_time/meter_time_features.json", "feature_pack_manifest": "<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/feature_pack_manifest.json"}`
- AI JSONL path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/features/performances/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/ai_training_records.jsonl`

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

## Meter and Time Intelligence
- confidence: `0.073598`
- ambiguity: `0.963724`
- top meter hypothesis: `{"hypothesis_id": "meter_h_0000", "meter": "3/4", "beats_per_bar": 3, "beat_unit": 4, "confidence": 0.564994, "ambiguity": 0.962029, "evidence": {"downbeat_hits": 11771.5, "offbeat_hits": 20826.0, "bar_support": 1.0, "consistency": 0.7521}, "limitations": ["meter is multi-hypothesis and remains probabilistic."]}`
- subdivision histogram: `{"random": 108}`
- macro section candidates: `["climactic_peak", "intro_or_prelude", "verse_or_chorus_candidate"]`
- usefulness: `weak_or_review_only`
- safe observation fields: `["local_tempo_bpm", "grid_confidence", "subdivision_type", "pulse_stability", "meter_time_refs"]`
- weak/review fields: `["microtiming_summary", "macro_section_candidate", "meter_hypothesis_candidates", "meter_time_ambiguity"]`

## 8. Recommended next steps
- Collect human verification for high-impact weak labels.
- Use accepted/audio_midi_only splits for baseline training first.
- Review quarantined/review records before inclusion.

## Pitch, Harmony, and Tuning Intelligence
- safe observations: `["pitch range and register distribution", "pitch-class normalized summary", "interval-class histogram summary", "voicing span and note-density/polyphony proxies", "direct-derived voice-count estimate proxies"]`
- weak labels: `["chord/key/mode hypotheses", "cadence/modulation candidates", "sonority family candidates", "counterpoint interpretation labels", "microtonal system hypotheses", "tension-release or experimental harmony labels"]`
- external audio/tuning limitations: `["symbolic MIDI pitch classes do not directly prove tuning system", "audio-based intonation estimation is required for non-12TET certainty"]`
- microtonal limitations: `["lack of pitch-bend/non-12TET evidence should remain inconclusive", "absence of evidence is not evidence of strict 12TET"]`
- experimental harmony limitations: `["nonfunctional/cluster-color labels remain candidate-level", "avoid using interpretive harmony labels as hard ground truth"]`
- training usefulness: `safe_stats_high_utility_weak_labels_review_required`
- microtonal analysis available: `False`
- microtonal evidence type: `external_analyzer_required`
- microtonal confidence: `0.15`

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

## Theory and Model Source Coverage
- theory_sources_represented: `["agawu_representing_african_music", "aldwell_schachter_voice_leading", "arom_african_polyphony", "berliner_thinking_in_jazz", "chernoff_african_sensibility", "cohn_audacious_euphony", "cooper_meyer_rhythmic_structure", "cowell_new_musical_resources", "forte_structure_atonal", "fux_gradus_ad_parnassum", "hasty_meter_as_rhythm", "hindemith_craft_composition", "iyer_microtiming_embodied", "keil_feld_groove", "kubik_theory_african_music", "lefebvre_rhythmanalysis", "lewin_gmIt", "london_hearing_in_time", "messiaen_technique_language", "partch_genesis_music", "persichetti_twentieth_century_harmony", "russell_lydian_chromatic", "schoenberg_theory_harmony", "straus_post_tonal", "toussaint_geometry_rhythm", "tymoczko_geometry_music", "xenakis_formalized_music"]`
- model_sources_represented: `["beat_tracker", "beatnet", "essentia", "essentia_tf", "groove_midi_dataset", "librosa", "madmom", "music21", "musicnn", "omnizart", "pretty_midi", "yourmt3"]`
- available_external_witnesses: `["essentia_features", "music21_features"]`
- unavailable_external_witnesses: `["beat_tracker_features", "musicnn_features", "omnizart_availability"]`
- consensus_status: `available`
- what_became_more_trusted: `[]`
- what_remains_weak_or_review_only: `["missing_external_meter_hypotheses", "tonal_center_conflict"]`
- witness_agreement_summary: `["Symbolic key witness is present for key hypothesis comparison."]`
- witness_conflict_warnings: `["Tonal-center disagreement: internal=None external=F."]`
- review_recommendations: `["Beat witness unavailable; review rhythm family confidence manually."]`
