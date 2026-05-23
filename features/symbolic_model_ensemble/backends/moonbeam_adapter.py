from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from features.symbolic_ir import SymbolicGenerationRequest
from features.symbolic_model_ensemble.backend_protocol import (
    BackendOperationResult,
    available_capability,
    backend_settings,
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

    def _smoke_test(self, repo_path: Path, model_path: Path) -> tuple[bool, str]:
        if not repo_path.exists() or not repo_path.is_dir():
            return False, "repo_path_missing"
        if not model_path.exists():
            return False, "model_path_missing"
        has_code_hint = any(repo_path.glob("*.py")) or (repo_path / "README.md").exists()
        if not has_code_hint:
            return False, "smoke_test_failed_no_code_hint"
        return True, "smoke_test_passed"

    def check_available(self):
        settings, source = backend_settings(self.backend_id)
        if not settings:
            return unavailable_capability(
                self.backend_id,
                self.backend_role,
                self.operations,
                f"config_missing:{source}",
            )
        if not bool(settings.get("enabled", False)):
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, "disabled_in_config")
        model_path = str(settings.get("model_path", "")).strip()
        repo_path = str(settings.get("repo_path", "")).strip()
        if not model_path:
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, "model_path_missing")
        if not repo_path:
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, "repo_path_missing")
        if importlib.util.find_spec("torch") is None:
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, "dependency_missing:torch")
        passed, reason = self._smoke_test(Path(repo_path), Path(model_path))
        if not passed:
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, reason)
        return available_capability(self.backend_id, self.backend_role, self.operations, reason=reason)

    def describe_capabilities(self):
        return self.check_available()

    def symbolic_ir_to_moonbeam_input(self, request: SymbolicGenerationRequest) -> dict[str, Any]:
        return {
            "prompt_text": request.prompt_spec.prompt_text,
            "tempo": request.prompt_spec.tempo,
            "meter": request.prompt_spec.meter,
            "key_hint": request.prompt_spec.key_hint,
            "requested_roles": list(request.prompt_spec.requested_track_roles),
            "task_type": request.task_type,
        }

    def moonbeam_output_to_symbolic_ir(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "hook_placeholder", "payload_keys": sorted(payload.keys())}

    def generate(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return unavailable_result(self.backend_id, "generation_hook_not_wired_no_fake_generation")

    def continue_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return unavailable_result(self.backend_id, "continuation_hook_not_wired_no_fake_generation")

    def infill_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return unavailable_result(self.backend_id, "infill_hook_not_wired_no_fake_generation")

    def evaluate(self, candidate):
        return unavailable_result(self.backend_id, "moonbeam_not_primary_evaluator")

    def rank(self, candidates):
        return unavailable_result(self.backend_id, "moonbeam_ranking_not_wired")

    def explain_result(self, result: BackendOperationResult) -> str:
        return f"Moonbeam result status={result.status} reason={result.reason}"
