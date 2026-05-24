from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

from features.symbolic_ir import SymbolicGenerationRequest
from features.symbolic_model_ensemble.backend_protocol import (
    BackendOperationResult,
    available_capability,
    unavailable_capability,
    unavailable_result,
)


class Text2MidiAdapter:
    backend_id = "text2midi"
    backend_role = "prompt_to_midi_sketch_backend"
    operations = [
        "prompt_to_midi",
        "text_conditioned_seed",
        "chord_key_tempo_prompting",
        "user_vocabulary_future_target",
    ]

    def _model_integrations_config_paths(self) -> tuple[Path, Path]:
        root_dir = Path(__file__).resolve().parents[3]
        config_dir = root_dir / "config" / "model_integrations"
        return config_dir / "model_integrations.local.json", config_dir / "model_integrations.example.json"

    def _load_text2midi_settings(self) -> tuple[dict[str, Any], bool]:
        local_path, example_path = self._model_integrations_config_paths()
        source = local_path if local_path.exists() else example_path
        if not source.exists():
            return {}, False
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}, False
        models = payload.get("models", {}) if isinstance(payload, dict) else {}
        if not isinstance(models, dict):
            return {}, False
        settings = models.get("text2midi", {})
        return settings if isinstance(settings, dict) else {}, bool(local_path.exists())

    def _check_paths(self, settings: dict[str, Any]) -> tuple[bool, str]:
        repo_path = Path(str(settings.get("repo_path", "")).strip())
        model_path = Path(str(settings.get("model_path", "")).strip())
        if not str(settings.get("repo_path", "")).strip():
            return False, "repo_path_missing"
        if not str(settings.get("model_path", "")).strip():
            return False, "model_path_missing"
        if not repo_path.exists() or not repo_path.is_dir():
            return False, "repo_path_missing"
        if not model_path.exists():
            return False, "model_path_missing"
        return True, "paths_ready"

    def run_smoke_test(self) -> tuple[bool, str]:
        settings, using_local_config = self._load_text2midi_settings()
        if not using_local_config:
            return False, "disabled_or_missing_local_config"
        if not bool(settings.get("enabled", False)):
            return False, "disabled_in_local_config"
        ready, reason = self._check_paths(settings)
        if not ready:
            return False, reason
        if not bool(settings.get("smoke_test_enabled", False)):
            return False, "smoke_test_disabled_in_config"
        try:
            importlib.import_module("torch")
        except ModuleNotFoundError:
            return False, "dependency_missing:torch"
        except Exception:  # noqa: BLE001
            return False, "dependency_probe_failed:torch"
        return True, "smoke_test_passed"

    def check_available(self):
        passed, reason = self.run_smoke_test()
        if not passed:
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, reason)
        return available_capability(
            self.backend_id,
            self.backend_role,
            self.operations,
            reason=reason,
            limitations=[
                "Prompt sketch scaffold only; real Text2MIDI inference wiring is intentionally not implemented.",
                "No fake MIDI output is emitted by this adapter.",
            ],
        )

    def describe_capabilities(self):
        return self.check_available()

    def prompt_spec_to_text2midi_input(self, request: SymbolicGenerationRequest) -> dict[str, Any]:
        return {
            "prompt": request.prompt_spec.prompt_text,
            "tempo": request.prompt_spec.tempo,
            "meter": request.prompt_spec.meter,
            "key_hint": request.prompt_spec.key_hint,
            "chord_hint": request.conditioning.get("chord_hint", "unknown"),
            "seed_mode": request.conditioning.get("seed_mode", "text_conditioned_seed"),
            "user_vocabulary_terms": list(request.conditioning.get("user_vocabulary_terms", [])),
            "duration_seconds": request.prompt_spec.duration_seconds,
        }

    def text2midi_output_to_symbolic_ir(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "hook_placeholder", "payload_keys": sorted(payload.keys())}

    def _unavailable_generation(self, reason: str) -> BackendOperationResult:
        return BackendOperationResult(
            status="unavailable",
            reason=reason,
            backend_id=self.backend_id,
            details={
                "backend": self.backend_id,
                "status": "unavailable",
                "reason": reason,
                "no_fake_generation": True,
                "scores_generated": False,
            },
        )

    def generate(self, request):
        return self._unavailable_generation("text2midi_prompt_sketch_not_wired_no_fake_generation")

    def continue_ir(self, request):
        return self._unavailable_generation("continuation_not_supported_for_text2midi")

    def infill_ir(self, request):
        return self._unavailable_generation("infill_not_supported_for_text2midi")

    def evaluate(self, candidate):
        return unavailable_result(self.backend_id, "text2midi_evaluation_not_supported")

    def rank(self, candidates):
        return unavailable_result(self.backend_id, "text2midi_ranking_not_supported")

    def explain_result(self, result: BackendOperationResult) -> str:
        return f"Text2MIDI result status={result.status} reason={result.reason}"
