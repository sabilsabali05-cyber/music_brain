from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

from features.symbolic_model_ensemble.backend_protocol import (
    BackendOperationResult,
    available_capability,
    unavailable_capability,
    unavailable_result,
)


class MusicBertAdapter:
    backend_id = "musicbert"
    backend_role = "symbolic_understanding_evaluation_similarity"
    operations = [
        "symbolic_embedding",
        "style_similarity",
        "accompaniment_fit",
        "melody_fit",
        "classification",
        "candidate_ranking",
    ]

    def _model_integrations_config_paths(self) -> tuple[Path, Path]:
        root_dir = Path(__file__).resolve().parents[3]
        config_dir = root_dir / "config" / "model_integrations"
        return config_dir / "model_integrations.local.json", config_dir / "model_integrations.example.json"

    def _load_musicbert_settings(self) -> tuple[dict[str, Any], bool]:
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
        settings = models.get("musicbert", {})
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
        settings, using_local_config = self._load_musicbert_settings()
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

    def build_request(self, candidate) -> dict[str, Any]:
        return self.convert_ir_to_musicbert_input(candidate)

    def convert_ir_to_musicbert_input(self, candidate) -> dict[str, Any]:
        return {
            "candidate_id": candidate.candidate_id,
            "track_count": len(candidate.ir.tracks),
            "duration_seconds": candidate.ir.duration_seconds,
            "prompt_text": candidate.ir.prompt_text,
        }

    def convert_musicbert_scores_to_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "hook_placeholder", "keys": sorted(payload.keys())}

    def symbolic_ir_to_musicbert_input(self, candidate) -> dict[str, Any]:
        return self.convert_ir_to_musicbert_input(candidate)

    def musicbert_scores_to_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.convert_musicbert_scores_to_evaluation(payload)

    def generate(self, request):
        return unavailable_result(self.backend_id, "musicbert_generation_disabled_evaluator_only")

    def continue_ir(self, request):
        return unavailable_result(self.backend_id, "musicbert_generation_disabled_evaluator_only")

    def infill_ir(self, request):
        return unavailable_result(self.backend_id, "musicbert_generation_disabled_evaluator_only")

    def _unavailable_evaluation(self) -> BackendOperationResult:
        capability = self.check_available()
        return BackendOperationResult(
            status="unavailable",
            reason=capability.reason,
            backend_id=self.backend_id,
            details={
                "backend": self.backend_id,
                "status": "unavailable",
                "reason": capability.reason,
                "no_fake_evaluation": True,
            },
        )

    def evaluate(self, candidate):
        return self._unavailable_evaluation()

    def rank(self, candidates):
        return self._unavailable_evaluation()

    def embed_ir(self, candidate):
        return self._unavailable_evaluation()

    def similarity(self, candidate_a, candidate_b):
        return self._unavailable_evaluation()

    def accompaniment_fit(self, candidate):
        return self._unavailable_evaluation()

    def melody_fit(self, candidate):
        return self._unavailable_evaluation()

    def explain_result(self, result: BackendOperationResult) -> str:
        return f"MusicBERT result status={result.status} reason={result.reason}"
