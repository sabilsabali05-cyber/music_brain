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
        "drum_variation",
        "groove_variation",
        "density_variation",
        "multitrack_infill",
        "bar_level_infill",
        "track_level_infill",
    ]

    def _paths_ready(self, repo_path: Path, model_path: Path, tokenizer_path: Path | None) -> tuple[bool, str]:
        if not repo_path.exists() or not repo_path.is_dir():
            return False, "repo_path_missing"
        if not model_path.exists():
            return False, "model_path_missing"
        if tokenizer_path is not None and not tokenizer_path.exists():
            return False, "tokenizer_path_missing"
        return True, "paths_ready"

    def _unavailable_operation(
        self,
        *,
        reason: str,
        operation: str,
        request: SymbolicGenerationRequest | None = None,
    ) -> BackendOperationResult:
        details: dict[str, Any] = {
            "status": "unavailable",
            "backend": self.backend_id,
            "reason": reason,
            "operation": operation,
            "no_fake_generation": True,
        }
        if request is not None:
            details["request_id"] = request.request_id
            details["task_type"] = request.task_type
        return BackendOperationResult(
            status="unavailable",
            reason=reason,
            backend_id=self.backend_id,
            details=details,
        )

    def check_available(self):
        settings, source = backend_settings(self.backend_id)
        if not settings:
            return unavailable_capability(
                self.backend_id,
                self.backend_role,
                self.operations,
                f"config_missing:{source}",
                limitations=["MIDI-GPT requires an explicit local symbolic backend config section."],
            )
        if not bool(settings.get("enabled", False)):
            return unavailable_capability(
                self.backend_id,
                self.backend_role,
                self.operations,
                "disabled_in_config",
                limitations=["Enable midigpt in local symbolic backend config to allow probing."],
            )
        model_path = str(settings.get("model_path", "")).strip()
        repo_path = str(settings.get("repo_path", "")).strip()
        tokenizer_path = str(settings.get("tokenizer_path", "")).strip()
        if not model_path:
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, "model_path_missing")
        if not repo_path:
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, "repo_path_missing")
        if tokenizer_path and not Path(tokenizer_path).exists():
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, "tokenizer_path_missing")
        passed, reason = self._paths_ready(
            Path(repo_path),
            Path(model_path),
            Path(tokenizer_path) if tokenizer_path else None,
        )
        if not passed:
            return unavailable_capability(self.backend_id, self.backend_role, self.operations, reason)
        if importlib.util.find_spec("torch") is None:
            return unavailable_capability(
                self.backend_id,
                self.backend_role,
                self.operations,
                "dependency_missing:torch",
                limitations=["Install torch manually in the local environment to run smoke imports."],
            )
        return available_capability(
            self.backend_id,
            self.backend_role,
            self.operations,
            reason="smoke_test_ready_no_fake_generation",
            limitations=[
                "Generation hooks intentionally return unavailable until real local MIDI-GPT inference wiring is implemented.",
                "No fake MIDI content is emitted by this adapter.",
            ],
        )

    def describe_capabilities(self):
        return self.check_available()

    def build_request(self, request: SymbolicGenerationRequest) -> dict[str, Any]:
        return {
            "request_id": request.request_id,
            "task_type": request.task_type,
            "prompt_text": request.prompt_spec.prompt_text,
            "requested_roles": list(request.prompt_spec.requested_track_roles),
            "density_hint": request.conditioning.get("density_hint", "medium"),
            "source_backend": request.source_backend,
        }

    def convert_ir_to_midigpt_input(self, request: SymbolicGenerationRequest) -> dict[str, Any]:
        return self.build_request(request)

    def convert_midigpt_output_to_ir(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "hook_placeholder", "payload_keys": sorted(payload.keys())}

    def run_smoke_test(self) -> tuple[bool, str]:
        capability = self.check_available()
        return capability.status == "available", capability.reason

    def generate_variation(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_operation(
            reason="midigpt_generate_variation_not_wired",
            operation="generate_variation",
            request=request,
        )

    def generate_drum_variation(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_operation(
            reason="midigpt_drum_variation_not_wired",
            operation="generate_drum_variation",
            request=request,
        )

    def generate_groove_variation(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_operation(
            reason="midigpt_groove_variation_not_wired",
            operation="generate_groove_variation",
            request=request,
        )

    def generate_density_variation(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_operation(
            reason="midigpt_density_variation_not_wired",
            operation="generate_density_variation",
            request=request,
        )

    def multitrack_infill(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_operation(
            reason="midigpt_multitrack_infill_not_wired",
            operation="multitrack_infill",
            request=request,
        )

    def bar_level_infill(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_operation(
            reason="midigpt_bar_level_infill_not_wired",
            operation="bar_level_infill",
            request=request,
        )

    def track_level_infill(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self._unavailable_operation(
            reason="midigpt_track_level_infill_not_wired",
            operation="track_level_infill",
            request=request,
        )

    # Protocol compatibility wrappers
    def generate(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self.generate_variation(request)

    def continue_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self.generate_variation(request)

    def infill_ir(self, request: SymbolicGenerationRequest) -> BackendOperationResult:
        return self.multitrack_infill(request)

    def evaluate(self, candidate):
        return unavailable_result(self.backend_id, "midigpt_evaluation_not_primary")

    def rank(self, candidates):
        return unavailable_result(self.backend_id, "midigpt_ranking_not_wired")

    def explain_result(self, result: BackendOperationResult) -> str:
        return f"MIDI-GPT result status={result.status} reason={result.reason}"
