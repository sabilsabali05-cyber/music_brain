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


class MoonbeamAdapter:
    backend_id = "moonbeam"
    backend_role = "main_symbolic_composition_continuation_infill"
    operations = [
        "symbolic_understanding",
        "continuation",
        "infill",
        "section_development",
        "phrase_development",
        "conditional_generation",
    ]

    def _model_integrations_config_paths(self) -> tuple[Path, Path]:
        root_dir = Path(__file__).resolve().parents[3]
        config_dir = root_dir / "config" / "model_integrations"
        return config_dir / "model_integrations.local.json", config_dir / "model_integrations.example.json"

    def _load_moonbeam_settings(self) -> tuple[dict[str, Any], bool]:
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
        settings = models.get("moonbeam", {})
        return settings if isinstance(settings, dict) else {}, bool(local_path.exists())

    def _check_paths(self, settings: dict[str, Any]) -> tuple[bool, str]:
        repo_path = Path(str(settings.get("repo_path", "")).strip())
        model_path = Path(str(settings.get("model_path", "")).strip())
        tokenizer_path = Path(str(settings.get("tokenizer_path", "")).strip())
        if not str(settings.get("repo_path", "")).strip():
            return False, "repo_path_missing"
        if not str(settings.get("model_path", "")).strip():
            return False, "model_path_missing"
        if not str(settings.get("tokenizer_path", "")).strip():
            return False, "tokenizer_path_missing"
        if not repo_path.exists() or not repo_path.is_dir():
            return False, "repo_path_missing"
        if not model_path.exists():
            return False, "model_path_missing"
        if not tokenizer_path.exists():
            return False, "tokenizer_path_missing"
        return True, "paths_ready"

    def run_smoke_test(self) -> tuple[bool, str]:
        settings, using_local_config = self._load_moonbeam_settings()
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
        return available_capability(self.backend_id, self.backend_role, self.operations, reason=reason)

    def describe_capabilities(self):
        return self.check_available()

    def build_request(self, request: SymbolicGenerationRequest) -> dict[str, Any]:
        return self.convert_ir_to_moonbeam_input(request)

    def convert_ir_to_moonbeam_input(self, request: SymbolicGenerationRequest) -> dict[str, Any]:
        return {
            "prompt_text": request.prompt_spec.prompt_text,
            "tempo": request.prompt_spec.tempo,
            "meter": request.prompt_spec.meter,
            "key_hint": request.prompt_spec.key_hint,
            "requested_roles": list(request.prompt_spec.requested_track_roles),
            "task_type": request.task_type,
        }

    def symbolic_ir_to_moonbeam_input(self, request: SymbolicGenerationRequest) -> dict[str, Any]:
        return self.convert_ir_to_moonbeam_input(request)

    def convert_moonbeam_output_to_ir(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "hook_placeholder", "payload_keys": sorted(payload.keys())}

    def moonbeam_output_to_symbolic_ir(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.convert_moonbeam_output_to_ir(payload)

    def _unavailable_generation(self) -> BackendOperationResult:
        capability = self.check_available()
        return BackendOperationResult(
            status="unavailable",
            reason=capability.reason,
            backend_id=self.backend_id,
            details={
                "backend": self.backend_id,
                "status": "unavailable",
                "reason": capability.reason,
                "no_fake_generation": True,
            },
        )

    def generate(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_generation()

    def continue_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_generation()

    def infill_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_generation()

    def generate_sections(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_generation()

    def evaluate(self, candidate):
        return unavailable_result(self.backend_id, "moonbeam_not_primary_evaluator")

    def rank(self, candidates):
        return unavailable_result(self.backend_id, "moonbeam_ranking_not_wired")

    def explain_result(self, result: BackendOperationResult) -> str:
        return f"Moonbeam result status={result.status} reason={result.reason}"
