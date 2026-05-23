from __future__ import annotations

import json
from pathlib import Path

import scripts.build_music_data_knowledge_pack as builder
import scripts.explain_music_data as explainer


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _prepare_minimal_repo(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports" / "mass_ingestion" / "mass_ingestion_readiness_report.json",
        {
            "ready_for_controlled_batch": True,
            "ready_for_mass_ingestion": False,
            "ready_for_model_training": False,
            "blockers": ["symbolic corpus export is not training-ready"],
            "top_strengths": ["generative examples exist"],
            "required_next_actions": ["fill local controlled batch manifest"],
        },
    )
    _write_json(
        tmp_path / "reports" / "privacy" / "privacy_leak_scan_report.json",
        {
            "new_public_leak_count": 0,
            "pre_existing_historical_path_debt_count": 5,
            "status": "ok",
            "pre_existing_historical_path_debt": [
                {"path": "reports/x.json", "marker": "C:/Users/test/path", "line_count": 1}
            ],
        },
    )
    _write_json(
        tmp_path / "reports" / "model_training" / "symbolic_corpus_v1_report.json",
        {
            "train_count": 0,
            "validation_count": 0,
            "review_count": 2,
            "exclude_count": 0,
            "training_ready": False,
        },
    )
    _write_json(
        tmp_path / "outputs" / "tangible_generation_v1" / "generation_report.json",
        {
            "output_dir": "outputs/tangible_generation_v1",
            "ratio_timing": {"climax_seconds": 111.2},
            "note_counts": {"song": 128},
            "sample_suggestions_generated": False,
        },
    )
    _write_json(
        tmp_path / "outputs" / "tangible_generation_v1" / "demo_composition_plan.json",
        {"climax_seconds": 111.2},
    )
    _write_json(
        tmp_path / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project" / "track_setup.json",
        {"tracks": [{"role": "drums", "track_type": "midi"}, {"role": "bass", "track_type": "midi"}]},
    )
    _write_json(
        tmp_path / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project" / "export_report.json",
        {"als_generation_status": "not_implemented_experimental_future"},
    )
    _write_json(
        tmp_path / "datasets" / "generative_training" / "perf_a" / "run_1" / "generative_manifest.json",
        {"performance_id": "perf_a", "run_id": "run_1"},
    )
    (tmp_path / "datasets" / "generative_training" / "perf_a" / "run_1" / "generative_examples.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"task_type": "continuation", "split_recommendation": "train"}),
                json.dumps({"task_type": "call_response", "split_recommendation": "validation"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_knowledge_pack_builds_with_missing_optional_files(tmp_path: Path, monkeypatch) -> None:
    _prepare_minimal_repo(tmp_path)
    monkeypatch.setattr(builder, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_MD", tmp_path / "reports" / "music_data_explainer" / "music_data_knowledge_pack.md")
    json_path, md_path, payload = builder.build_music_data_knowledge_pack()
    assert json_path.exists()
    assert md_path.exists()
    assert payload["performances"]
    assert payload["sources"]


def test_knowledge_pack_does_not_expose_private_paths(tmp_path: Path, monkeypatch) -> None:
    _prepare_minimal_repo(tmp_path)
    # Inject path debt with private local marker.
    _write_json(
        tmp_path / "reports" / "controlled_ingestion" / "controlled_batch_plan.json",
        {"status": "valid", "note": "C:/Users/private/location"},
    )
    monkeypatch.setattr(builder, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_MD", tmp_path / "reports" / "music_data_explainer" / "music_data_knowledge_pack.md")
    json_path, _, _ = builder.build_music_data_knowledge_pack()
    content = json_path.read_text(encoding="utf-8")
    assert "C:/Users/" not in content
    assert "C:\\Users\\" not in content


def test_explainer_answers_dataset_overview(tmp_path: Path, monkeypatch) -> None:
    _prepare_minimal_repo(tmp_path)
    monkeypatch.setattr(builder, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_MD", tmp_path / "reports" / "music_data_explainer" / "music_data_knowledge_pack.md")
    builder.build_music_data_knowledge_pack()

    monkeypatch.setattr(explainer, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(explainer, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    answer = explainer.explain_music_data("what data do we have so far?")
    assert "Music Data Explainer" in answer.answer_markdown
    assert "Readiness" in answer.answer_markdown


def test_explainer_answers_model_training_blocker_question(tmp_path: Path, monkeypatch) -> None:
    _prepare_minimal_repo(tmp_path)
    monkeypatch.setattr(builder, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_MD", tmp_path / "reports" / "music_data_explainer" / "music_data_knowledge_pack.md")
    builder.build_music_data_knowledge_pack()
    monkeypatch.setattr(explainer, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(explainer, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    answer = explainer.explain_music_data("why are we not ready for model training?")
    assert "not ready" in answer.answer_markdown.lower()
    assert "no model training has happened" in answer.answer_markdown.lower()


def test_explainer_answers_ableton_output_question(tmp_path: Path, monkeypatch) -> None:
    _prepare_minimal_repo(tmp_path)
    monkeypatch.setattr(builder, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_MD", tmp_path / "reports" / "music_data_explainer" / "music_data_knowledge_pack.md")
    builder.build_music_data_knowledge_pack()
    monkeypatch.setattr(explainer, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(explainer, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    answer = explainer.explain_music_data("what can I open in Ableton right now?")
    assert "Ableton" in answer.answer_markdown
    assert "export root" in answer.answer_markdown.lower()


def test_explainer_cites_evidence_references(tmp_path: Path, monkeypatch) -> None:
    _prepare_minimal_repo(tmp_path)
    monkeypatch.setattr(builder, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_MD", tmp_path / "reports" / "music_data_explainer" / "music_data_knowledge_pack.md")
    builder.build_music_data_knowledge_pack()
    monkeypatch.setattr(explainer, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(explainer, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    answer = explainer.explain_music_data("what did the tangible demo generate?")
    assert answer.evidence_refs
    assert all(item.artifact_path for item in answer.evidence_refs)


def test_explainer_marks_missing_data_honestly(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "datasets" / "music_data_explainer").mkdir(parents=True, exist_ok=True)
    (tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json").write_text(
        json.dumps(
            {
                "sources": [],
                "performances": [],
                "generative_datasets": [],
                "sample_libraries": [],
                "ableton_output": {"export_available": False, "export_root": "outputs/ableton_project_v1/AI_Generated_Song_Project"},
                "readiness": {
                    "ready_for_controlled_batch": False,
                    "ready_for_mass_ingestion": False,
                    "ready_for_model_training": False,
                    "blockers": [],
                    "top_strengths": [],
                    "next_actions": [],
                    "privacy_new_public_leak_count": 0,
                    "privacy_historical_debt_count": 0,
                },
                "known_task_types": [],
                "corpus_split_counts": {},
                "tangible_outputs": {},
                "limitations": [],
                "next_best_actions": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(explainer, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(explainer, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    answer = explainer.explain_music_data("tell me about performances")
    assert "no performance summaries were found" in answer.answer_markdown.lower()


def test_private_path_debt_is_summarized_not_leaked(tmp_path: Path, monkeypatch) -> None:
    _prepare_minimal_repo(tmp_path)
    _write_json(
        tmp_path / "reports" / "privacy" / "privacy_leak_scan_report.json",
        {
            "new_public_leak_count": 0,
            "pre_existing_historical_path_debt_count": 9,
            "status": "ok",
            "pre_existing_historical_path_debt": [
                {"path": "reports/p.json", "marker": "C:/Users/private/abc", "line_count": 1}
            ],
        },
    )
    monkeypatch.setattr(builder, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_JSON", tmp_path / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json")
    monkeypatch.setattr(builder, "KNOWLEDGE_PACK_MD", tmp_path / "reports" / "music_data_explainer" / "music_data_knowledge_pack.md")
    _, _, payload = builder.build_music_data_knowledge_pack()
    payload_text = json.dumps(payload)
    assert "C:/Users/" not in payload_text
    assert payload["readiness"]["privacy_historical_debt_count"] == 9
