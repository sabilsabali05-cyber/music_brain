# Training Data Audit - 20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir

## 1. Artifacts generated
- source audio reference: `C:/Users/izzyo/Downloads/Kanye West performs Ghost Town with 070 Shake and the Sunday Service Choir.mp3`
- active analysis path: `C:\Users\izzyo\ai-composer\music_brain\samples\analysis\Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir\20260521T204701196539_modal_librosa_dense\structure_analysis.json`
- active segments manifest: `C:/Users/izzyo/ai-composer/music_brain/samples/segments/Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/segments_manifest.json`
- window MIDI count: `13`
- merged MIDI path: `C:\Users\izzyo\ai-composer\music_brain\samples\segments\Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir\20260521T204750163461_audio_structure_v1\merged\merged_performance.mid`
- merge report path: `C:/Users/izzyo/ai-composer/music_brain/samples/segments/Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/merged/merge_report.json`
- feature pack files: `{"rhythm_features": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/rhythm_features.json", "harmony_features": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/harmony_features.json", "tags": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/tags.json", "meter_time_features": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/rhythm_time/meter_time_features.json", "feature_pack_manifest": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/feature_pack_manifest.json"}`
- AI JSONL path: `C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/ai_training_records.jsonl`

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
- human verification labels

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
- confidence: `0.190786`
- ambiguity: `0.855685`
- top meter hypothesis: `{"hypothesis_id": "meter_h_0000", "meter": "3/4", "beats_per_bar": 3, "beat_unit": 4, "confidence": 0.562622, "ambiguity": 0.967614, "evidence": {"downbeat_hits": 3407.3, "offbeat_hits": 6194.4, "bar_support": 1.0, "consistency": 0.7532}, "limitations": ["meter is multi-hypothesis and remains probabilistic."]}`
- subdivision histogram: `{"random": 26}`
- macro section candidates: `["climactic_peak", "intro_or_prelude"]`
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
- content_state_counts: `{"unknown": 231, "rhythm_dominant": 101, "percussive_only": 1, "melodic_lead": 28, "harmonic_dominant": 41}`
- content_state_counts_by_granularity: `{"segment": {"unknown": 13}, "window": {"unknown": 13}, "rhythm_region": {"unknown": 86, "rhythm_dominant": 101, "percussive_only": 1}, "chord_region": {"melodic_lead": 28, "unknown": 119, "harmonic_dominant": 41}}`
- labels_suppressed_by_routing: `363`
- likely_false_suppressions: `29`
- harmonic_evidence_regions_suppressed: `100`
- upgrade_candidates: `13`
- upgrade_candidates_by_label_family: `{"semantic": 13}`
- downgrade_or_suppress_candidates: `390`
- downgrade_or_suppress_candidates_by_label_family: `{"semantic": 247, "rhythm": 102, "harmony": 41}`
- needs_human_review_candidates: `0`
- routing_improves_training_safety: `True`
- recommended_routing_calibration_status: `needs_recalibration`

## Theory and Model Source Coverage
- theory_sources_represented: `["agawu_representing_african_music", "aldwell_schachter_voice_leading", "arom_african_polyphony", "berliner_thinking_in_jazz", "chernoff_african_sensibility", "cohn_audacious_euphony", "cooper_meyer_rhythmic_structure", "cowell_new_musical_resources", "forte_structure_atonal", "fux_gradus_ad_parnassum", "hasty_meter_as_rhythm", "hindemith_craft_composition", "iyer_microtiming_embodied", "keil_feld_groove", "kubik_theory_african_music", "lefebvre_rhythmanalysis", "lewin_gmIt", "london_hearing_in_time", "messiaen_technique_language", "partch_genesis_music", "persichetti_twentieth_century_harmony", "russell_lydian_chromatic", "schoenberg_theory_harmony", "straus_post_tonal", "toussaint_geometry_rhythm", "tymoczko_geometry_music", "xenakis_formalized_music"]`
- model_sources_represented: `["beat_tracker", "beatnet", "essentia", "essentia_tf", "groove_midi_dataset", "librosa", "madmom", "music21", "musicnn", "omnizart", "pretty_midi", "yourmt3"]`
- available_external_witnesses: `["beat_tracker_features", "essentia_features", "music21_features", "musicnn_features", "omnizart_availability"]`
- unavailable_external_witnesses: `[]`
- consensus_status: `available`
- what_became_more_trusted: `[]`
- what_remains_weak_or_review_only: `["missing_external_meter_hypotheses"]`
- witness_agreement_summary: `["Symbolic key witness is present for key hypothesis comparison."]`
- witness_conflict_warnings: `[]`
- review_recommendations: `["Beat witness unavailable; review rhythm family confidence manually."]`
