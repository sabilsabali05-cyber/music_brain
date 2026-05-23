from __future__ import annotations

from dataclasses import asdict
from typing import Any

from features.symbolic_ir import SymbolicBackendCapability
from features.symbolic_model_ensemble.backends import (
    ExampleRetrievalAdapter,
    MidiGptAdapter,
    MoonbeamAdapter,
    MusicBertAdapter,
    Text2MidiAdapter,
)


def build_backend_registry() -> dict[str, Any]:
    return {
        "moonbeam": MoonbeamAdapter(),
        "musicbert": MusicBertAdapter(),
        "midigpt": MidiGptAdapter(),
        "text2midi": Text2MidiAdapter(),
        "example_retrieval": ExampleRetrievalAdapter(),
    }


def list_backend_capabilities() -> list[SymbolicBackendCapability]:
    registry = build_backend_registry()
    return [adapter.describe_capabilities() for adapter in registry.values()]


def backend_availability_payload() -> dict[str, Any]:
    capabilities = list_backend_capabilities()
    return {
        "status": "ok",
        "backends": [asdict(item) for item in capabilities],
        "limitations": [
            "Availability only checks config/dependency/path/smoke gate readiness.",
            "No model weights are downloaded by this checker.",
            "No training or audio processing is performed.",
        ],
    }
