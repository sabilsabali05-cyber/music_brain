from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from features.symbolic_ir import (
    SymbolicBackendCapability,
    SymbolicGenerationCandidate,
    SymbolicGenerationRequest,
    SymbolicModelProvenance,
    SymbolicMusicIR,
    SymbolicNoteEvent,
    SymbolicPromptSpec,
    SymbolicSection,
    SymbolicTrack,
)
from features.symbolic_model_ensemble.capability_registry import build_backend_registry
from features.symbolic_model_ensemble.ensemble_orchestrator import SymbolicEnsembleOrchestrator


def _request(backend_id: str, task_type: str = "continuation") -> SymbolicGenerationRequest:
    return SymbolicGenerationRequest(
        request_id="req_1",
        prompt_spec=SymbolicPromptSpec(
            prompt_text="test prompt",
            duration_seconds=48.0,
            tempo=120.0,
            meter="4/4",
            key_hint="unknown",
            ratio_plan="golden_ratio",
            section_labels=["a", "b"],
            requested_track_roles=["drums", "bass"],
        ),
        task_type=task_type,
        source_backend=backend_id,
    )


def _candidate(candidate_id: str, backend_id: str, note_count: int = 4) -> SymbolicGenerationCandidate:
    notes = [SymbolicNoteEvent(start_tick=i * 120, duration_tick=120, pitch=60 + (i % 6), velocity=82, channel=0) for i in range(note_count)]
    ir = SymbolicMusicIR(
        composition_id=f"comp_{candidate_id}",
        prompt_text="prompt",
        duration_seconds=24.0,
        tempo=120.0,
        meter="4/4",
        key_hint="unknown",
        ratio_plan="golden_ratio",
        section_labels=["main"],
        sections=[SymbolicSection(section_label="main", start_tick=0, end_tick=960)],
        tracks=[SymbolicTrack(track_id="t1", track_role="lead", instrument_hint="piano", note_events=notes)],
        source_backend=backend_id,
        generation_method="test",
    )
    return SymbolicGenerationCandidate(
        candidate_id=candidate_id,
        ir=ir,
        source_backend=backend_id,
        generation_method="test",
        model_provenance=SymbolicModelProvenance(source_backend=backend_id, generation_method="test"),
    )


def test_backend_registry_includes_expected_backends() -> None:
    registry = build_backend_registry()
    assert set(registry.keys()) == {"moonbeam", "musicbert", "midigpt", "text2midi", "example_retrieval"}


def test_unavailable_backend_returns_reason_safely() -> None:
    registry = build_backend_registry()
    request = _request("moonbeam")
    result = registry["moonbeam"].generate(request)
    assert result.status == "unavailable"
    assert result.reason


def test_no_backend_silently_pretends_to_generate() -> None:
    registry = build_backend_registry()
    request = _request("moonbeam")
    for backend_id in ["moonbeam", "midigpt", "text2midi"]:
        result = registry[backend_id].generate(request)
        assert result.status == "unavailable"


def test_symbolic_ir_roundtrip_basic_object() -> None:
    ir = SymbolicMusicIR(
        composition_id="comp_roundtrip",
        prompt_text="prompt",
        duration_seconds=32.0,
        tempo=112.0,
        meter="4/4",
        key_hint="minor",
        ratio_plan="golden_ratio",
        section_labels=["intro", "climax"],
        sections=[SymbolicSection(section_label="intro", start_tick=0, end_tick=960)],
        tracks=[SymbolicTrack(track_id="lead_1", track_role="lead", instrument_hint="piano", note_events=[SymbolicNoteEvent(0, 240, 64, 90, 0)])],
    )
    payload = asdict(ir)
    rebuilt = SymbolicMusicIR(
        composition_id=str(payload["composition_id"]),
        prompt_text=str(payload["prompt_text"]),
        duration_seconds=float(payload["duration_seconds"]),
        tempo=float(payload["tempo"]),
        meter=str(payload["meter"]),
        key_hint=str(payload["key_hint"]),
        ratio_plan=str(payload["ratio_plan"]),
        section_labels=list(payload["section_labels"]),
        sections=[SymbolicSection(**row) for row in payload["sections"]],
        tracks=[
            SymbolicTrack(
                track_id=row["track_id"],
                track_role=row["track_role"],
                instrument_hint=row["instrument_hint"],
                note_events=[SymbolicNoteEvent(**item) for item in row["note_events"]],
            )
            for row in payload["tracks"]
        ],
    )
    assert rebuilt.composition_id == ir.composition_id
    assert rebuilt.tracks[0].note_events[0].pitch == 64


def test_ensemble_falls_back_when_real_backends_unavailable(tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()
    report = orchestrator.generate("crooked gospel rap", output_root=tmp_path / "out")
    assert report["example_retrieval_fallback"] is True
    assert report["no_real_symbolic_backend_available"] is True


def test_fallback_report_marks_no_real_backend(tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()
    orchestrator.generate("fallback check", output_root=tmp_path / "out")
    payload = json.loads((tmp_path / "out" / "ensemble_generation_report.json").read_text(encoding="utf-8"))
    assert payload["no_real_symbolic_backend_available"] is True
    assert payload["not_model_trained_on_user_data"] is True


def test_musicbert_role_is_evaluation_not_main_generation() -> None:
    registry = build_backend_registry()
    assert "candidate_ranking" in registry["musicbert"].operations
    request = _request("musicbert")
    result = registry["musicbert"].generate(request)
    assert result.status == "unavailable"


def test_moonbeam_preferred_main_generation_when_available(monkeypatch, tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()

    class FakeMoonbeam:
        backend_id = "moonbeam"

        def check_available(self):
            return SymbolicBackendCapability(
                backend_id="moonbeam",
                backend_role="main",
                supported_operations=["continuation"],
                status="available",
                reason="ok",
            )

        describe_capabilities = check_available

        def generate(self, request):
            raise AssertionError("moonbeam generate should not be called")

        def continue_ir(self, request):
            return type("Res", (), {"status": "ok", "reason": "ok", "candidate": _candidate("moonbeam_1", "moonbeam", note_count=10)})()

        def infill_ir(self, request):
            return type("Res", (), {"status": "unavailable", "reason": "n/a", "candidate": None})()

        def evaluate(self, candidate):
            return type("Res", (), {"status": "unavailable", "reason": "n/a", "candidate": None})()

        def rank(self, candidates):
            return type("Res", (), {"status": "unavailable", "reason": "n/a", "candidate": None})()

        def explain_result(self, result):
            return "ok"

    class FakeUnavailable:
        def __init__(self, backend_id: str):
            self.backend_id = backend_id

        def check_available(self):
            return SymbolicBackendCapability(
                backend_id=self.backend_id,
                backend_role="test",
                supported_operations=[],
                status="unavailable",
                reason="disabled",
            )

        describe_capabilities = check_available

        def generate(self, request):
            return type("Res", (), {"status": "unavailable", "reason": "disabled", "candidate": None})()

        continue_ir = generate
        infill_ir = generate
        evaluate = generate
        rank = generate

        def explain_result(self, result):
            return "disabled"

    orchestrator.registry["moonbeam"] = FakeMoonbeam()
    orchestrator.registry["text2midi"] = FakeUnavailable("text2midi")
    orchestrator.registry["midigpt"] = FakeUnavailable("midigpt")
    orchestrator.registry["example_retrieval"] = FakeUnavailable("example_retrieval")
    orchestrator.registry["musicbert"] = FakeUnavailable("musicbert")
    report = orchestrator.generate("moonbeam preferred", output_root=tmp_path / "out")
    assert report["selected_candidate_backend"] == "moonbeam"


def test_midigpt_is_routed_for_drum_variation_tasks(tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()
    seen_task_types: list[str] = []

    class Recorder:
        backend_id = "midigpt"
        operations = []

        def check_available(self):
            return SymbolicBackendCapability(
                backend_id=self.backend_id,
                backend_role="test",
                supported_operations=[],
                status="unavailable",
                reason="disabled",
            )

        describe_capabilities = check_available

        def generate(self, request):
            return type("Res", (), {"status": "unavailable", "reason": "n/a", "candidate": None})()

        def continue_ir(self, request):
            return type("Res", (), {"status": "unavailable", "reason": "n/a", "candidate": None})()

        def infill_ir(self, request):
            seen_task_types.append(request.task_type)
            return type("Res", (), {"status": "unavailable", "reason": "n/a", "candidate": None})()

        evaluate = generate
        rank = generate

        def explain_result(self, result):
            return "n/a"

    orchestrator.registry["midigpt"] = Recorder()
    orchestrator.generate("route midigpt", output_root=tmp_path / "out")
    assert "drum_multitrack_variation" in seen_task_types


def test_text2midi_is_routed_for_prompt_sketch_tasks(tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()
    seen_task_types: list[str] = []

    class Recorder:
        backend_id = "text2midi"
        operations = []

        def check_available(self):
            return SymbolicBackendCapability(
                backend_id=self.backend_id,
                backend_role="test",
                supported_operations=[],
                status="unavailable",
                reason="disabled",
            )

        describe_capabilities = check_available

        def generate(self, request):
            seen_task_types.append(request.task_type)
            return type("Res", (), {"status": "unavailable", "reason": "n/a", "candidate": None})()

        continue_ir = generate
        infill_ir = generate
        evaluate = generate
        rank = generate

        def explain_result(self, result):
            return "n/a"

    orchestrator.registry["text2midi"] = Recorder()
    orchestrator.generate("route text2midi", output_root=tmp_path / "out")
    assert "prompt_sketch" in seen_task_types


def test_public_reports_contain_no_private_paths(tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()
    orchestrator.generate("privacy check", output_root=tmp_path / "out")
    report_text = (tmp_path / "out" / "ensemble_generation_report.json").read_text(encoding="utf-8")
    assert "C:/" + "Users/" not in report_text
    assert "C:\\" + "Users\\" not in report_text


def test_no_model_training_claim_is_made(tmp_path: Path) -> None:
    orchestrator = SymbolicEnsembleOrchestrator()
    payload = orchestrator.generate("training claim check", output_root=tmp_path / "out")
    assert payload["not_model_trained_on_user_data"] is True
