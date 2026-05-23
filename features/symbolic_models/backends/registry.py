from __future__ import annotations

from features.symbolic_models.backends.base import BaseSymbolicModelAdapter
from features.symbolic_models.backends.midigpt_adapter import MidiGptAdapter
from features.symbolic_models.backends.moonbeam_adapter import MoonbeamAdapter
from features.symbolic_models.backends.musicbert_adapter import MusicBertAdapter
from features.symbolic_models.backends.text2midi_adapter import Text2MidiAdapter
from features.symbolic_models.model_backend_schema import ModelAvailabilityReport, SymbolicModelProvider


def _provider_instances(*, stub_mode: bool = False) -> dict[str, BaseSymbolicModelAdapter]:
    return {
        "musicbert": MusicBertAdapter(stub_mode=stub_mode),
        "moonbeam": MoonbeamAdapter(stub_mode=stub_mode),
        "midigpt": MidiGptAdapter(stub_mode=stub_mode),
        "text2midi": Text2MidiAdapter(stub_mode=stub_mode),
    }


def list_symbolic_model_providers(*, stub_mode: bool = False) -> list[SymbolicModelProvider]:
    return [provider.describe_capabilities() for provider in _provider_instances(stub_mode=stub_mode).values()]


def check_symbolic_model_backends(*, stub_mode: bool = False) -> list[ModelAvailabilityReport]:
    output: list[ModelAvailabilityReport] = []
    for provider_id, provider in _provider_instances(stub_mode=stub_mode).items():
        try:
            output.append(provider.check_available())
        except Exception as exc:  # noqa: BLE001
            capability_payload = provider.describe_capabilities()
            output.append(
                ModelAvailabilityReport(
                    provider_id=provider_id,
                    display_name=capability_payload.display_name,
                    available=False,
                    capabilities=capability_payload.capabilities,
                    default_role=capability_payload.default_role,
                    role_hint=capability_payload.role_hint,
                    installation_hint=capability_payload.installation_hint,
                    details={"error": str(exc)},
                    limitations=["Availability check raised an exception; provider disabled safely."],
                )
            )
    return output


def get_symbolic_model_provider(provider_id: str, *, stub_mode: bool = False) -> BaseSymbolicModelAdapter | None:
    return _provider_instances(stub_mode=stub_mode).get(provider_id.strip().lower())
