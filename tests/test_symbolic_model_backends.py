from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from features.symbolic_models.backends.registry import (
    check_symbolic_model_backends,
    get_symbolic_model_provider,
    list_symbolic_model_providers,
)
from scripts.generate_midi_with_backend import generate_midi_with_backend
from scripts.plan_symbolic_generation import plan_symbolic_generation


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(row) for row in rows)
    path.write_text((body + "\n") if body else "", encoding="utf-8")


def _seed_dataset(tmp_path: Path, task: str = "continuation") -> Path:
    dataset_dir = tmp_path / "datasets" / "generative_training" / "perf_symbolic" / "run_1"
    _write_json(
        dataset_dir / "generative_manifest.json",
        {
            "performance_id": "perf_symbolic",
            "segment_run_id": "run_1",
            "generative_examples_count": 1,
            "split_counts": {"train": 1, "validation": 0, "review": 0, "exclude": 0},
            "examples_by_task_type": {task: 1},
        },
    )
    _write_jsonl(
        dataset_dir / "generative_examples.jsonl",
        [
            {
                "example_id": "ex1",
                "performance_id": "perf_symbolic",
                "segment_run_id": "run_1",
                "task_type": task,
                "split_recommendation": "train",
                "quality_score": {"final_score": 0.8},
                "target_representation": {
                    "midi_events": [
                        {"start": 0.0, "end": 0.25, "note": 60, "velocity": 90},
                        {"start": 0.3, "end": 0.5, "note": 62, "velocity": 80},
                    ]
                },
                "context_start_seconds": 0.0,
                "context_end_seconds": 1.0,
                "target_start_seconds": 1.0,
                "target_end_seconds": 2.0,
                "conditioning": {"tempo_context": {"local_tempo_bpm_median": 120.0}},
            }
        ],
    )
    return dataset_dir


def test_registry_lists_expected_symbolic_providers() -> None:
    providers = {item.provider_id for item in list_symbolic_model_providers()}
    assert {"musicbert", "moonbeam", "midigpt", "text2midi"} <= providers


def test_unavailable_providers_do_not_crash() -> None:
    results = check_symbolic_model_backends()
    assert len(results) >= 4
    assert all(item.provider_id for item in results)


def test_musicbert_exposes_evaluator_capabilities_only() -> None:
    provider = get_symbolic_model_provider("musicbert")
    assert provider is not None
    caps = set(provider.describe_capabilities().capabilities)
    assert "symbolic_embedding" in caps
    assert "similarity_scoring" in caps
    assert "reranking" in caps
    assert "midi_continuation" not in caps


def test_moonbeam_exposes_continuation_and_infill_capabilities() -> None:
    provider = get_symbolic_model_provider("moonbeam")
    assert provider is not None
    caps = set(provider.describe_capabilities().capabilities)
    assert "midi_continuation" in caps
    assert "midi_infill" in caps


def test_midigpt_exposes_multitrack_controllable_capabilities() -> None:
    provider = get_symbolic_model_provider("midigpt")
    assert provider is not None
    caps = set(provider.describe_capabilities().capabilities)
    assert "multitrack_generation" in caps
    assert "controllable_generation" in caps


def test_text2midi_exposes_text_to_midi_capability() -> None:
    provider = get_symbolic_model_provider("text2midi")
    assert provider is not None
    caps = set(provider.describe_capabilities().capabilities)
    assert "text_to_midi" in caps


def test_planner_recommends_provider_order_by_task(tmp_path: Path, monkeypatch) -> None:
    dataset_dir = _seed_dataset(tmp_path, task="continuation")
    monkeypatch.chdir(tmp_path)
    json_path, _ = plan_symbolic_generation(dataset_dir, task="continuation", prompt="make a sparse gospel call response")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    order = payload["provider_fallback_order"]
    assert order[0] == "example_retrieval"
    assert "moonbeam" in order
    assert "text2midi" in order
    assert order[-1] == "musicbert"


def test_planner_fallback_starts_with_example_retrieval_when_models_unavailable(tmp_path: Path, monkeypatch) -> None:
    dataset_dir = _seed_dataset(tmp_path, task="call_response")
    monkeypatch.chdir(tmp_path)
    json_path, _ = plan_symbolic_generation(dataset_dir, task="call_response")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["provider_plan"][0]["provider_id"] == "example_retrieval"
    assert payload["provider_plan"][0]["available"] is True


def test_generation_wrapper_writes_unavailable_report_safely(tmp_path: Path, monkeypatch) -> None:
    dataset_dir = _seed_dataset(tmp_path, task="continuation")
    monkeypatch.chdir(tmp_path)
    output_dir, report_path, _ = generate_midi_with_backend(dataset_dir, provider="moonbeam", task="continuation")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert output_dir.exists()
    assert report["provider_id"] == "moonbeam"
    assert report["generation_status"] in {"unavailable", "unimplemented_stub"}
    assert report["provenance"]["not_model_trained"] is True


def test_generation_wrapper_example_retrieval_fallback_generates_from_examples(tmp_path: Path, monkeypatch) -> None:
    dataset_dir = _seed_dataset(tmp_path, task="continuation")
    monkeypatch.chdir(tmp_path)
    output_dir, report_path, _ = generate_midi_with_backend(dataset_dir, provider="example_retrieval", task="continuation")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert output_dir.exists()
    assert report["provider_id"] == "example_retrieval"
    assert report["generation_status"] in {"success_delegated_to_example_retrieval", "success_internal_example_fallback"}
    assert report["provenance"]["prototype_generated_from_existing_examples"] is True
    assert report["provenance"]["not_model_trained"] is True


def test_no_heavy_imports_at_module_import_time() -> None:
    heavy_modules = {"torch", "transformers", "midigpt", "moonbeam", "text2midi"}
    before = set(sys.modules.keys())
    importlib.import_module("features.symbolic_models.backends.musicbert_adapter")
    importlib.import_module("features.symbolic_models.backends.moonbeam_adapter")
    importlib.import_module("features.symbolic_models.backends.midigpt_adapter")
    importlib.import_module("features.symbolic_models.backends.text2midi_adapter")
    after = set(sys.modules.keys())
    newly_loaded = after - before
    assert not (heavy_modules & newly_loaded)
