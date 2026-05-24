from __future__ import annotations

from features.audio_understanding.audio_understanding_schema import AudioUnderstandingModelRecord


def list_audio_understanding_models() -> list[AudioUnderstandingModelRecord]:
    return [
        AudioUnderstandingModelRecord(
            model_id="essentia",
            role="Baseline descriptor witness and optional practical analyzer; no training.",
            enabled_by_default=False,
            smoke_test_supported=True,
            expected_outputs=["descriptor_summary", "feature_witness"],
            limitations=[
                "Disabled by default until local config explicitly enables it.",
                "No downloads, no training, and no automatic audio processing in setup checks.",
            ],
        ),
        AudioUnderstandingModelRecord(
            model_id="muq",
            role="Future semantic embedding encoder scaffold; disabled by default.",
            enabled_by_default=False,
            smoke_test_supported=True,
            expected_outputs=["embedding_vector", "semantic_tags_future"],
            limitations=[
                "Scaffold only: embedding generation is intentionally not implemented.",
                "No downloads and no automatic audio processing.",
            ],
        ),
        AudioUnderstandingModelRecord(
            model_id="mert",
            role="Future representation embedding encoder scaffold; disabled by default.",
            enabled_by_default=False,
            smoke_test_supported=True,
            expected_outputs=["embedding_vector", "representation_features_future"],
            limitations=[
                "Scaffold only: embedding generation is intentionally not implemented.",
                "No downloads and no automatic audio processing.",
            ],
        ),
    ]
