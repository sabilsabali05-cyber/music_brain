# Training Data Audit - 20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir

## 1. Artifacts generated
- source audio reference: `C:/Users/izzyo/Downloads/Kanye West performs Ghost Town with 070 Shake and the Sunday Service Choir.mp3`
- active analysis path: `C:\Users\izzyo\ai-composer\music_brain\samples\analysis\Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir\20260521T204701196539_modal_librosa_dense\structure_analysis.json`
- active segments manifest: `C:/Users/izzyo/ai-composer/music_brain/samples/segments/Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/segments_manifest.json`
- window MIDI count: `13`
- merged MIDI path: `C:\Users\izzyo\ai-composer\music_brain\samples\segments\Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir\20260521T204750163461_audio_structure_v1\merged\merged_performance.mid`
- merge report path: `C:/Users/izzyo/ai-composer/music_brain/samples/segments/Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/merged/merge_report.json`
- feature pack files: `{"rhythm_features": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/rhythm_features.json", "harmony_features": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/harmony_features.json", "tags": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/tags.json", "feature_pack_manifest": "C:/Users/izzyo/ai-composer/music_brain/features/performances/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/feature_pack_manifest.json"}`
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
- beat/downbeat external witness

## 6. AI-readiness assessment
- Is ai_training_records.jsonl usable? `True`
- Safe for training now: `["raw_observation and derived_observation records", "high/medium reliability windows", "records with complete provenance fields"]`
- Weak labels only: `["heuristic_estimate records", "weak_label and interpretive_weak_label records"]`
- Exclude/downweight: `["failed/missing reliability windows", "review_required records", "ambiguous labels without corroboration"]`

## 7. Dataset inclusion decision
- decision: `accepted`
- recommended split: `train`

## 8. Recommended next steps
- Collect human verification for high-impact weak labels.
- Use accepted/audio_midi_only splits for baseline training first.
- Review quarantined/review records before inclusion.
