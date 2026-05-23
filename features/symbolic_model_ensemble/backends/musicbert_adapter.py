from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from features.symbolic_model_ensemble.backend_protocol import (
    BackendOperationResult,
    available_capability,
    backend_settings,
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

    def symbolic_ir_to_musicbert_input(self, candidate) -> dict[str, Any]:
        return {
            "candidate_id": candidate.candidate_id,
            "track_count": len(candidate.ir.tracks),
            "duration_seconds": candidate.ir.duration_seconds,
            "prompt_text": candidate.ir.prompt_text,
        }

    def musicbert_scores_to_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "hook_placeholder", "keys": sorted(payload.keys())}

    def generate(self, request):
        return unavailable_result(self.backend_id, "musicbert_generation_disabled_evaluator_only")

    def continue_ir(self, request):
        return unavailable_result(self.backend_id, "musicbert_generation_disabled_evaluator_only")

    def infill_ir(self, request):
        return unavailable_result(self.backend_id, "musicbert_generation_disabled_evaluator_only")

    def evaluate(self, candidate):
        availability = self.check_available()
        if availability.status != "available":
            return unavailable_result(self.backend_id, f"unavailable:{availability.reason}")
        return unavailable_result(self.backend_id, "evaluation_hook_not_wired_no_fake_scores")

    def rank(self, candidates):
        availability = self.check_available()
        if availability.status != "available":
            return unavailable_result(self.backend_id, f"unavailable:{availability.reason}")
        return unavailable_result(self.backend_id, "ranking_hook_not_wired_no_fake_scores")

    def explain_result(self, result: BackendOperationResult) -> str:
        return f"MusicBERT result status={result.status} reason={result.reason}"
