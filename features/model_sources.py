from __future__ import annotations

from typing import Any


MODEL_SOURCES: list[dict[str, Any]] = [
    {
        "provider_id": "yourmt3",
        "provider_name": "YourMT3",
        "input_type": "audio",
        "output_types": ["midi_transcription"],
        "best_for": ["polyphonic transcription", "note events"],
        "weak_for": ["microtonal nuance unless pitch-bend present", "noisy live certainty"],
        "trust_policy": "model_prediction",
        "dependency_status": "configured",
        "licensing_notes": "Respect upstream model and dataset licenses.",
        "implementation_status": "existing",
        "local_available": "unknown",
        "role": "transcription backbone",
    },
    {
        "provider_id": "pretty_midi",
        "provider_name": "pretty_midi",
        "input_type": "midi",
        "output_types": ["symbolic_observations"],
        "best_for": ["note durations", "velocities", "pitch classes", "polyphony"],
        "weak_for": ["audio-native timing/tuning nuance"],
        "trust_policy": "raw_observation",
        "dependency_status": "configured",
        "licensing_notes": "Python package license applies.",
        "implementation_status": "existing",
        "local_available": "unknown",
        "role": "symbolic MIDI parser",
    },
    {
        "provider_id": "librosa",
        "provider_name": "librosa",
        "input_type": "audio",
        "output_types": ["onset", "tempo", "tempogram", "chroma", "spectral"],
        "best_for": ["transparent baseline features"],
        "weak_for": ["high-level semantic labels"],
        "trust_policy": "derived_observation",
        "dependency_status": "configured",
        "licensing_notes": "Python package license applies.",
        "implementation_status": "existing",
        "local_available": "unknown",
        "role": "audio baseline analyzer",
    },
    {
        "provider_id": "essentia",
        "provider_name": "Essentia",
        "input_type": "audio",
        "output_types": ["rhythm descriptors", "tonal descriptors", "spectral descriptors", "high-level descriptors"],
        "best_for": ["MIR witness descriptors"],
        "weak_for": ["ground-truth labeling"],
        "trust_policy": "external_witness",
        "dependency_status": "optional",
        "licensing_notes": "AGPL/commercial considerations may apply.",
        "implementation_status": "optional_adapter",
        "local_available": "unknown",
        "role": "MIR descriptor witness",
    },
    {
        "provider_id": "beatnet",
        "provider_name": "BeatNet",
        "input_type": "audio",
        "output_types": ["beats", "downbeats", "tempo", "meter hypotheses"],
        "best_for": ["beat/downbeat/meter witness"],
        "weak_for": ["functional harmony inference"],
        "trust_policy": "external_witness",
        "dependency_status": "optional",
        "licensing_notes": "Model/package licenses apply.",
        "implementation_status": "optional_adapter",
        "local_available": "unknown",
        "role": "beat/downbeat/meter witness",
    },
    {
        "provider_id": "madmom",
        "provider_name": "madmom",
        "input_type": "audio",
        "output_types": ["beats", "downbeats", "onsets"],
        "best_for": ["beat/downbeat/onset witness"],
        "weak_for": ["definitive meter certainty"],
        "trust_policy": "external_witness",
        "dependency_status": "optional",
        "licensing_notes": "Package licensing applies.",
        "implementation_status": "optional_adapter",
        "local_available": "unknown",
        "role": "beat/downbeat/onset witness",
    },
    {
        "provider_id": "beat_tracker",
        "provider_name": "Beat tracker abstraction",
        "input_type": "audio",
        "output_types": ["tempo_candidates", "beat_positions", "downbeat_positions", "meter_hypotheses"],
        "best_for": ["runtime backend selection among BeatNet/madmom/librosa"],
        "weak_for": ["ground-truth certainty"],
        "trust_policy": "external_witness",
        "dependency_status": "optional",
        "licensing_notes": "Backend-specific licensing applies.",
        "implementation_status": "optional_adapter",
        "local_available": "unknown",
        "role": "adapter abstraction",
    },
    {
        "provider_id": "music21",
        "provider_name": "music21",
        "input_type": "symbolic",
        "output_types": ["key candidates", "chordification candidates", "interval/counterpoint summaries"],
        "best_for": ["symbolic theory witness"],
        "weak_for": ["audio-native nuance", "ground-truth certainty"],
        "trust_policy": "weak_label",
        "dependency_status": "optional",
        "licensing_notes": "Python package license applies.",
        "implementation_status": "optional_adapter",
        "local_available": "unknown",
        "role": "symbolic theory witness",
    },
    {
        "provider_id": "musicnn",
        "provider_name": "musicnn",
        "input_type": "audio",
        "output_types": ["semantic tags", "embedding summaries"],
        "best_for": ["semantic tag witness"],
        "weak_for": ["precise harmony/meter claims"],
        "trust_policy": "external_witness",
        "dependency_status": "optional",
        "licensing_notes": "Model/package licenses apply.",
        "implementation_status": "optional_adapter",
        "local_available": "unknown",
        "role": "semantic witness",
    },
    {
        "provider_id": "essentia_tf",
        "provider_name": "Essentia TensorFlow Models",
        "input_type": "audio",
        "output_types": ["high-level tags", "embeddings"],
        "best_for": ["model-based semantic witness"],
        "weak_for": ["hard labels"],
        "trust_policy": "external_witness",
        "dependency_status": "optional",
        "licensing_notes": "Model/package licenses apply.",
        "implementation_status": "planned",
        "local_available": "unknown",
        "role": "high-level witness",
    },
    {
        "provider_id": "omnizart",
        "provider_name": "Omnizart",
        "input_type": "audio",
        "output_types": ["chord/beat/downbeat/drum/vocal estimates"],
        "best_for": ["optional comparison witness"],
        "weak_for": ["automatic truth assignment"],
        "trust_policy": "external_witness",
        "dependency_status": "optional",
        "licensing_notes": "Model/package licenses apply.",
        "implementation_status": "optional_adapter",
        "local_available": "unknown",
        "role": "comparison witness",
    },
    {
        "provider_id": "groove_midi_dataset",
        "provider_name": "Groove MIDI Dataset / E-GMD",
        "input_type": "dataset_reference",
        "output_types": ["calibration guidance", "evaluation fixtures"],
        "best_for": ["calibration/evaluation reference"],
        "weak_for": ["direct feature generation in this repo pass"],
        "trust_policy": "calibration_reference",
        "dependency_status": "not_installed",
        "licensing_notes": "Use according to dataset terms; do not auto-download.",
        "implementation_status": "dataset_reference",
        "local_available": "unknown",
        "role": "calibration reference",
    },
]


def get_model_source(provider_id: str) -> dict[str, Any] | None:
    for source in MODEL_SOURCES:
        if str(source.get("provider_id")) == provider_id:
            return source
    return None


def list_model_sources() -> list[dict[str, Any]]:
    return MODEL_SOURCES


def get_model_sources_for_feature(feature_name: str) -> list[dict[str, Any]]:
    needle = feature_name.strip().lower()
    output: list[dict[str, Any]] = []
    for source in MODEL_SOURCES:
        outputs = [str(item).lower() for item in source.get("output_types", [])]
        role = str(source.get("role", "")).lower()
        if any(needle in item for item in outputs) or needle in role:
            output.append(source)
    return output


def annotate_feature_with_model_source(feature_record: dict[str, Any], provider_id: str) -> dict[str, Any]:
    refs = feature_record.get("model_source_refs", [])
    if not isinstance(refs, list):
        refs = []
    refs.append(provider_id)
    feature_record["model_source_refs"] = sorted(set(str(item) for item in refs))
    return feature_record


def annotate_external_witness_result(result: dict[str, Any], provider_id: str) -> dict[str, Any]:
    result["model_source_ref"] = provider_id
    source = get_model_source(provider_id)
    if source:
        result["trust_policy"] = source.get("trust_policy")
    return result
