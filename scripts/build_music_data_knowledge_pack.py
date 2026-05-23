from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.music_data_explainer.explainer_schema import (  # noqa: E402
    AbletonOutputSummary,
    EvidenceReference,
    GenerativeDatasetSummary,
    MusicDataKnowledgePack,
    MusicDataLimitation,
    MusicDataSourceSummary,
    PerformanceSummary,
    ReadinessSummary,
    SampleLibrarySummary,
)

KNOWLEDGE_PACK_JSON = ROOT_DIR / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json"
KNOWLEDGE_PACK_MD = ROOT_DIR / "reports" / "music_data_explainer" / "music_data_knowledge_pack.md"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _private_marker_in_text(text: str) -> bool:
    markers = ["C:\\Users\\", "C:/Users/", "OneDrive\\Desktop\\sounds", "OneDrive/Desktop/sounds"]
    return any(marker in text for marker in markers)


def _redact_text(text: str) -> str:
    out = text
    out = out.replace("C:\\Users\\", "<PRIVATE_LOCAL_PATH>\\")
    out = out.replace("C:/Users/", "<PRIVATE_LOCAL_PATH>/")
    out = out.replace("OneDrive\\Desktop\\sounds", "<LOCAL_SAMPLE_LIBRARY_ROOT>")
    out = out.replace("OneDrive/Desktop/sounds", "<LOCAL_SAMPLE_LIBRARY_ROOT>")
    return out


def _sanitize_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_obj(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_sanitize_obj(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _source_summary(path: Path) -> MusicDataSourceSummary:
    exists = path.exists()
    privacy_redacted = False
    notes: list[str] = []
    if exists:
        try:
            sample = path.read_text(encoding="utf-8", errors="ignore")[:2000]
            privacy_redacted = _private_marker_in_text(sample)
            if privacy_redacted:
                notes.append("privacy_redacted")
        except OSError:
            notes.append("unreadable")
    else:
        notes.append("missing")
    return MusicDataSourceSummary(
        source_id=path.stem,
        artifact_path=_rel(path),
        exists=exists,
        privacy_redacted=privacy_redacted,
        notes=notes,
    )


def _summarize_generative_datasets(pack: MusicDataKnowledgePack) -> None:
    manifest_paths = sorted((ROOT_DIR / "datasets" / "generative_training").glob("**/generative_manifest.json"))
    performance_map: dict[str, PerformanceSummary] = {}
    task_types: set[str] = set()

    for manifest_path in manifest_paths:
        manifest = _read_json(manifest_path)
        performance_id = str(manifest.get("performance_id", manifest_path.parent.parent.name))
        dataset_id = str(manifest.get("run_id", manifest_path.parent.name))
        examples_path = manifest_path.parent / "generative_examples.jsonl"
        example_count = _count_jsonl_rows(examples_path)

        split_counts: dict[str, int] = {}
        dataset_task_types: set[str] = set()
        if examples_path.exists():
            with examples_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    task = str(row.get("task_type", "")).strip()
                    split = str(row.get("split_recommendation", "")).strip() or "unknown"
                    if task:
                        dataset_task_types.add(task)
                        task_types.add(task)
                    split_counts[split] = split_counts.get(split, 0) + 1

        dataset_summary = GenerativeDatasetSummary(
            dataset_id=dataset_id,
            dataset_path=_rel(manifest_path.parent),
            performance_id=performance_id,
            example_count=example_count,
            task_types=sorted(dataset_task_types),
            split_counts=split_counts,
            privacy_redacted=False,
        )
        pack.generative_datasets.append(dataset_summary)

        perf = performance_map.get(performance_id)
        if perf is None:
            perf = PerformanceSummary(
                performance_id=performance_id,
                display_name=performance_id,
                evidence_refs=[EvidenceReference(artifact_path=_rel(manifest_path), summary="generative manifest")],
            )
            performance_map[performance_id] = perf
        perf.generative_dataset_count += 1
        perf.generative_example_count += example_count
        perf.task_types = sorted(set(perf.task_types).union(dataset_task_types))

    pack.performances = sorted(performance_map.values(), key=lambda item: item.display_name)
    pack.known_task_types = sorted(task_types)


def _summarize_sample_library(pack: MusicDataKnowledgePack) -> None:
    manifests = sorted((ROOT_DIR / "datasets" / "sample_libraries").glob("**/sample_library_manifest.json"))
    for manifest_path in manifests:
        data = _read_json(manifest_path)
        library_id = str(data.get("library_id", manifest_path.parent.name))
        source_type = str(data.get("source_type", "unknown"))
        sample_count = data.get("records_count")
        if not isinstance(sample_count, int):
            sample_count = data.get("supported_files_indexed")
        indexed_audio_files = data.get("supported_files_indexed")
        privacy_redacted = _private_marker_in_text(json.dumps(data)[:4000]) if data else False
        pack.sample_libraries.append(
            SampleLibrarySummary(
                library_id=library_id,
                manifest_found=True,
                sample_count=sample_count if isinstance(sample_count, int) else None,
                indexed_audio_files=indexed_audio_files if isinstance(indexed_audio_files, int) else None,
                source_type=source_type,
                privacy_redacted=privacy_redacted,
                notes=["privacy_redacted"] if privacy_redacted else [],
            )
        )


def _summarize_tangible_and_ableton(pack: MusicDataKnowledgePack) -> None:
    generation_report = _read_json(ROOT_DIR / "outputs" / "tangible_generation_v1" / "generation_report.json")
    composition_plan = _read_json(ROOT_DIR / "outputs" / "tangible_generation_v1" / "demo_composition_plan.json")
    if generation_report:
        note_counts = generation_report.get("note_counts", {})
        pack.tangible_outputs = {
            "output_dir": str(generation_report.get("output_dir", "outputs/tangible_generation_v1")),
            "sample_suggestions_generated": bool(generation_report.get("sample_suggestions_generated", False)),
            "climax_seconds": generation_report.get("ratio_timing", {}).get("climax_seconds")
            if isinstance(generation_report.get("ratio_timing"), dict)
            else None,
            "note_counts": note_counts if isinstance(note_counts, dict) else {},
        }
    if composition_plan and not pack.tangible_outputs.get("climax_seconds"):
        pack.tangible_outputs["climax_seconds"] = composition_plan.get("climax_seconds")

    track_setup = _read_json(ROOT_DIR / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project" / "track_setup.json")
    export_report = _read_json(ROOT_DIR / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project" / "export_report.json")
    track_roles: list[str] = []
    midi_track_count = 0
    if isinstance(track_setup.get("tracks"), list):
        for item in track_setup["tracks"]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            if role:
                track_roles.append(role)
            if str(item.get("track_type", "")).strip() == "midi":
                midi_track_count += 1

    pack.ableton_output = AbletonOutputSummary(
        export_available=bool(track_setup) and bool(export_report),
        export_root="outputs/ableton_project_v1/AI_Generated_Song_Project",
        midi_track_count=midi_track_count,
        track_roles=sorted(set(track_roles)),
        als_generation_status=str(export_report.get("als_generation_status", "not_implemented_experimental_future")),
        notes=[],
    )


def _summarize_readiness(pack: MusicDataKnowledgePack) -> None:
    readiness = _read_json(ROOT_DIR / "reports" / "mass_ingestion" / "mass_ingestion_readiness_report.json")
    privacy = _read_json(ROOT_DIR / "reports" / "privacy" / "privacy_leak_scan_report.json")
    controlled_plan = _read_json(ROOT_DIR / "reports" / "controlled_ingestion" / "controlled_batch_plan.json")
    corpus = _read_json(ROOT_DIR / "reports" / "model_training" / "symbolic_corpus_v1_report.json")

    blockers = readiness.get("blockers", [])
    if not isinstance(blockers, list):
        blockers = []
    strengths = readiness.get("top_strengths", [])
    if not isinstance(strengths, list):
        strengths = []
    next_actions = readiness.get("required_next_actions", [])
    if not isinstance(next_actions, list):
        next_actions = []

    pack.readiness = ReadinessSummary(
        ready_for_controlled_batch=bool(readiness.get("ready_for_controlled_batch", False)),
        ready_for_mass_ingestion=bool(readiness.get("ready_for_mass_ingestion", False)),
        ready_for_model_training=bool(readiness.get("ready_for_model_training", False)),
        blockers=[str(item) for item in blockers],
        top_strengths=[str(item) for item in strengths],
        next_actions=[str(item) for item in next_actions],
        privacy_new_public_leak_count=int(privacy.get("new_public_leak_count", 0) or 0),
        privacy_historical_debt_count=int(privacy.get("pre_existing_historical_path_debt_count", 0) or 0),
    )

    split_counts = {
        "train": int(corpus.get("train_count", 0) or 0),
        "validation": int(corpus.get("validation_count", 0) or 0),
        "review": int(corpus.get("review_count", 0) or 0),
        "exclude": int(corpus.get("exclude_count", 0) or 0),
    }
    pack.corpus_split_counts = split_counts

    if controlled_plan.get("status") not in {None, "valid"}:
        pack.limitations.append(
            MusicDataLimitation(
                limitation_id="controlled_plan_invalid",
                description="Controlled ingestion plan is invalid and needs manifest updates.",
                severity="high",
            )
        )
    if pack.readiness.privacy_historical_debt_count > 0:
        pack.limitations.append(
            MusicDataLimitation(
                limitation_id="historical_privacy_debt",
                description="Historical tracked path debt exists and should be scrubbed/redacted.",
                severity="medium",
            )
        )

    pack.next_best_actions = [
        "Fill a local controlled batch manifest with 1-5 authorized song files.",
        "Run controlled-batch plan + dry-run before execute mode.",
        "Prioritize review queue items to increase training-ready corpus coverage.",
        "Keep privacy scans clean for new public leaks before each merge.",
    ]


def build_music_data_knowledge_pack() -> tuple[Path, Path, dict[str, Any]]:
    pack = MusicDataKnowledgePack()

    source_paths = [
        ROOT_DIR / "reports" / "mass_ingestion" / "mass_ingestion_readiness_report.json",
        ROOT_DIR / "reports" / "privacy" / "privacy_leak_scan_report.json",
        ROOT_DIR / "reports" / "controlled_ingestion" / "controlled_batch_plan.json",
        ROOT_DIR / "reports" / "model_training" / "symbolic_corpus_v1_report.json",
        ROOT_DIR / "reports" / "review_queue" / "review_queue_summary.json",
        ROOT_DIR / "reports" / "data_quality" / "training_candidate_quality_report.json",
        ROOT_DIR / "reports" / "model_evaluation" / "generated_composition_scorecard.json",
        ROOT_DIR / "outputs" / "tangible_generation_v1" / "generation_report.json",
        ROOT_DIR / "outputs" / "tangible_generation_v1" / "demo_composition_plan.json",
        ROOT_DIR / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project" / "track_setup.json",
        ROOT_DIR / "outputs" / "ableton_project_v1" / "AI_Generated_Song_Project" / "export_report.json",
    ]
    pack.sources = [_source_summary(path) for path in source_paths]

    _summarize_generative_datasets(pack)
    _summarize_sample_library(pack)
    _summarize_tangible_and_ableton(pack)
    _summarize_readiness(pack)

    payload = _sanitize_obj(pack.as_dict())
    KNOWLEDGE_PACK_JSON.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_PACK_MD.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_PACK_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Music Data Knowledge Pack",
        "",
        f"- built_at: `{payload['built_at']}`",
        f"- performances_found: `{len(payload['performances'])}`",
        f"- generative_datasets_found: `{len(payload['generative_datasets'])}`",
        f"- known_task_types: `{', '.join(payload['known_task_types']) if payload['known_task_types'] else 'none'}`",
        f"- ready_for_controlled_batch: `{payload['readiness']['ready_for_controlled_batch']}`",
        f"- ready_for_mass_ingestion: `{payload['readiness']['ready_for_mass_ingestion']}`",
        f"- ready_for_model_training: `{payload['readiness']['ready_for_model_training']}`",
        "",
        "## Top Blockers",
    ]
    lines.extend([f"- {item}" for item in payload["readiness"]["blockers"]] or ["- none"])
    lines.extend(["", "## Next Best Actions"])
    lines.extend([f"- {item}" for item in payload["next_best_actions"]])
    lines.extend(["", "## Evidence Sources"])
    for item in payload["sources"]:
        status = "exists" if item["exists"] else "missing"
        redaction = " privacy_redacted" if item["privacy_redacted"] else ""
        lines.append(f"- `{item['artifact_path']}` ({status}{redaction})")
    lines.append("")
    KNOWLEDGE_PACK_MD.write_text("\n".join(lines), encoding="utf-8")
    return KNOWLEDGE_PACK_JSON, KNOWLEDGE_PACK_MD, payload


def main() -> int:
    json_path, md_path, payload = build_music_data_knowledge_pack()
    print(f"MUSIC_DATA_KNOWLEDGE_PACK_JSON={json_path.as_posix()}")
    print(f"MUSIC_DATA_KNOWLEDGE_PACK_MD={md_path.as_posix()}")
    print(f"PERFORMANCES_FOUND={len(payload['performances'])}")
    print(f"GENERATIVE_DATASETS_FOUND={len(payload['generative_datasets'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
