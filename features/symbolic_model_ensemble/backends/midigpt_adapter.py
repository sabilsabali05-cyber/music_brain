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


class MidiGptAdapter:
    backend_id = "midigpt"
    backend_role = "controllable_multitrack_variation_backend"
    operations = [
        "track_level_infill",
        "bar_level_infill",
        "drum_variation",
        "density_control",
        "polyphony_control",
        "duration_control",
        "instrument_control",
    ]

    def _smoke_test(self, repo_path: Path, model_path: Path) -> tuple[bool, str]:
        if not repo_path.exists() or not repo_path.is_dir():
            return False, "repo_path_missing"
        if not model_path.exists():
            return False, "model_path_missing"
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

    def symbolic_ir_to_midigpt_input(self, request: SymbolicGenerationRequest) -> dict[str, Any]:
        return {
            "task_type": request.task_type,
            "prompt_text": request.prompt_spec.prompt_text,
            "requested_roles": list(request.prompt_spec.requested_track_roles),
            "density_hint": request.conditioning.get("density_hint", "medium"),
        }

    def midigpt_output_to_symbolic_ir(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "hook_placeholder", "payload_keys": sorted(payload.keys())}

    def generate(self, request):
        return unavailable_result(self.backend_id, "generation_hook_not_wired_no_fake_generation")

    def continue_ir(self, request):
        return unavailable_result(self.backend_id, "continuation_hook_not_wired_no_fake_generation")

    def infill_ir(self, request):
        return unavailable_result(self.backend_id, "infill_hook_not_wired_no_fake_generation")

    def evaluate(self, candidate):
        return unavailable_result(self.backend_id, "midigpt_evaluation_not_primary")

    def rank(self, candidates):
        return unavailable_result(self.backend_id, "midigpt_ranking_not_wired")

    def explain_result(self, result: BackendOperationResult) -> str:
        return f"MIDI-GPT result status={result.status} reason={result.reason}"
