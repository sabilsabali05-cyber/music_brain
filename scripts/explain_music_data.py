from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.music_data_explainer.explainer_schema import (  # noqa: E402
    EvidenceReference,
    ExplainerAnswer,
    ExplainerQuestion,
    MusicDataLimitation,
)

KNOWLEDGE_PACK_JSON = ROOT_DIR / "datasets" / "music_data_explainer" / "music_data_knowledge_pack.json"


def _load_knowledge_pack() -> dict[str, Any]:
    if not KNOWLEDGE_PACK_JSON.exists():
        raise FileNotFoundError(
            "Missing knowledge pack. Run: scripts\\dev.cmd build-music-data-knowledge-pack"
        )
    payload = json.loads(KNOWLEDGE_PACK_JSON.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Knowledge pack must be a JSON object.")
    return payload


def classify_question(question: str) -> ExplainerQuestion:
    q = question.lower()
    if any(token in q for token in ["what data", "overview", "have so far", "dataset"]):
        category = "dataset_overview"
    elif any(token in q for token in ["performance", "ghost town", "sunday service"]):
        category = "performance_summary"
    elif any(token in q for token in ["generative", "continuation", "call_response", "buildup"]):
        category = "generative_examples"
    elif any(token in q for token in ["tangible", "demo", "generated midi"]):
        category = "tangible_generation"
    elif any(token in q for token in ["ableton", "open in ableton", "track setup"]):
        category = "ableton_export"
    elif any(token in q for token in ["sample library", "sounds folder", "samples"]):
        category = "sample_library"
    elif any(token in q for token in ["synplant", "seed selection"]):
        category = "synplant_seed_selection"
    elif any(token in q for token in ["blocker", "not ready", "mass ingestion"]):
        category = "readiness_blockers"
    elif any(token in q for token in ["model training", "training ready", "train model"]):
        category = "model_training_readiness"
    elif any(token in q for token in ["next step", "controlled ingestion", "first batch"]):
        category = "controlled_ingestion_next_steps"
    elif any(token in q for token in ["privacy", "authorization", "paths", "splice"]):
        category = "privacy_and_authorization"
    else:
        category = "unknown"
    return ExplainerQuestion(question_text=question, category=category)


def _source_evidence(pack: dict[str, Any], contains: str) -> list[EvidenceReference]:
    refs: list[EvidenceReference] = []
    for source in pack.get("sources", []):
        if not isinstance(source, dict):
            continue
        path = str(source.get("artifact_path", ""))
        if contains in path:
            refs.append(
                EvidenceReference(
                    artifact_path=path,
                    summary="source artifact",
                    privacy_redacted=bool(source.get("privacy_redacted", False)),
                )
            )
    return refs


def _render_answer(question: ExplainerQuestion, pack: dict[str, Any]) -> ExplainerAnswer:
    readiness = pack.get("readiness", {})
    corpus = pack.get("corpus_split_counts", {})
    category = question.category
    evidence: list[EvidenceReference] = []
    limitations: list[MusicDataLimitation] = []
    lines: list[str] = []

    if category == "dataset_overview":
        lines.extend(
            [
                "You currently have a mixed music-data workspace with performance-derived generative datasets, prototype tangible MIDI outputs, and an Ableton-ready export scaffold.",
                f"- Performances summarized: `{len(pack.get('performances', []))}`",
                f"- Generative datasets found: `{len(pack.get('generative_datasets', []))}`",
                f"- Known generative tasks: `{', '.join(pack.get('known_task_types', [])) or 'none found'}`",
                f"- Sample libraries summarized: `{len(pack.get('sample_libraries', []))}`",
                f"- Ableton export available: `{pack.get('ableton_output', {}).get('export_available', False)}`",
                f"- Readiness: controlled_batch=`{readiness.get('ready_for_controlled_batch', False)}`, mass_ingestion=`{readiness.get('ready_for_mass_ingestion', False)}`, model_training=`{readiness.get('ready_for_model_training', False)}`",
            ]
        )
        evidence.extend(_source_evidence(pack, "mass_ingestion"))
        evidence.extend(_source_evidence(pack, "tangible_generation_v1"))
    elif category == "performance_summary":
        performances = pack.get("performances", [])
        if performances:
            top = performances[0]
            lines.append(
                f"One available performance summary is `{top.get('display_name', top.get('performance_id', 'unknown'))}` with `{top.get('generative_example_count', 0)}` generative examples."
            )
            lines.append(
                f"Task coverage for that performance: `{', '.join(top.get('task_types', [])) or 'unknown'}`."
            )
            lines.append("Musically, more task diversity usually improves arrangement flexibility and recombination quality.")
        else:
            lines.append("No performance summaries were found in the current knowledge pack.")
            limitations.append(
                MusicDataLimitation(
                    limitation_id="missing_performance_summary",
                    description="No generative manifests were discoverable for performance-level explanation.",
                    severity="medium",
                )
            )
        evidence.extend(_source_evidence(pack, "generative_training"))
    elif category == "generative_examples":
        lines.extend(
            [
                "Generative examples are supervised pairs used to teach musical continuation and transformation behavior.",
                "- `continuation`: continue a phrase from preceding context.",
                "- `call_response`: produce an answering phrase with contrast and relation.",
                "- `buildup_to_release`: shape tension then resolution across a section boundary.",
                "These tasks feed prototype generation by selecting and recombining learned structural patterns rather than training a new model in this step.",
                f"Known tasks in this repo: `{', '.join(pack.get('known_task_types', [])) or 'unknown'}`.",
            ]
        )
        evidence.extend(_source_evidence(pack, "generative_training"))
    elif category == "tangible_generation":
        tangible = pack.get("tangible_outputs", {})
        lines.extend(
            [
                "The tangible demo is prototype generation from existing examples, not model-trained composition.",
                f"- Output dir: `{tangible.get('output_dir', 'outputs/tangible_generation_v1')}`",
                f"- Climax timing (if known): `{tangible.get('climax_seconds', 'unknown')}`",
                f"- Note counts: `{tangible.get('note_counts', {})}`",
                "Listen for section arc clarity (build -> climax -> release), role balance, and transition coherence.",
            ]
        )
        evidence.extend(_source_evidence(pack, "tangible_generation_v1"))
    elif category == "ableton_export":
        ableton = pack.get("ableton_output", {})
        lines.extend(
            [
                "You can open the Ableton-ready project scaffold and import the generated MIDI tracks.",
                f"- Export root: `{ableton.get('export_root', 'outputs/ableton_project_v1/AI_Generated_Song_Project')}`",
                f"- MIDI track count: `{ableton.get('midi_track_count', 0)}`",
                f"- Track roles: `{', '.join(ableton.get('track_roles', [])) or 'unknown'}`",
                f"- ALS generation status: `{ableton.get('als_generation_status', 'not_implemented_experimental_future')}`",
                "Synplant seed summaries are guidance for manual sound selection; no Synplant automation is claimed.",
            ]
        )
        evidence.extend(_source_evidence(pack, "ableton_project_v1"))
    elif category in {"readiness_blockers", "model_training_readiness"}:
        lines.extend(
            [
                "The project is not ready for mass ingestion/model training yet.",
                f"- ready_for_controlled_batch: `{readiness.get('ready_for_controlled_batch', False)}`",
                f"- ready_for_mass_ingestion: `{readiness.get('ready_for_mass_ingestion', False)}`",
                f"- ready_for_model_training: `{readiness.get('ready_for_model_training', False)}`",
                f"- Blockers: `{', '.join(readiness.get('blockers', [])) or 'none reported'}`",
                f"- Corpus split counts: train=`{corpus.get('train', 0)}`, validation=`{corpus.get('validation', 0)}`, review=`{corpus.get('review', 0)}`, exclude=`{corpus.get('exclude', 0)}`",
                "No model training has happened; the current stage is readiness + curation.",
            ]
        )
        evidence.extend(_source_evidence(pack, "mass_ingestion"))
        evidence.extend(_source_evidence(pack, "model_training"))
    elif category == "sample_library":
        libs = pack.get("sample_libraries", [])
        if libs:
            first = libs[0]
            lines.append(
                f"Sample library `{first.get('library_id', 'unknown')}` is indexed with approx `{first.get('sample_count', 'unknown')}` records."
            )
            lines.append("Local sample libraries can support texture retrieval and manual seed suggestion workflows.")
        else:
            lines.append("No sample-library manifest summary is available in this pack.")
        lines.append("Private absolute paths are redacted in explainer outputs.")
        evidence.extend(_source_evidence(pack, "sample_libraries"))
    elif category == "synplant_seed_selection":
        lines.extend(
            [
                "Synplant seed selection is currently manual/human-in-the-loop.",
                "Local samples can be used as seed candidates when authorization permits.",
                "Splice-like sources remain production-oriented and should stay training-excluded by default.",
                "No automated Synplant generation is claimed in this pipeline state.",
            ]
        )
        evidence.extend(_source_evidence(pack, "feedback"))
        evidence.extend(_source_evidence(pack, "mass_ingestion"))
    elif category == "controlled_ingestion_next_steps":
        lines.append("Next practical step is to fill a local controlled-batch manifest and run planner + dry-run.")
        for action in pack.get("next_best_actions", []):
            lines.append(f"- {action}")
        evidence.extend(_source_evidence(pack, "controlled_ingestion"))
    elif category == "privacy_and_authorization":
        lines.extend(
            [
                "Privacy guardrails are active: new public leaks should remain zero.",
                f"- New public leak count: `{readiness.get('privacy_new_public_leak_count', 0)}`",
                f"- Historical path debt count: `{readiness.get('privacy_historical_debt_count', 0)}`",
                "Authorization constraints should be applied before enabling training export or ingestion execute mode.",
            ]
        )
        evidence.extend(_source_evidence(pack, "privacy"))
        evidence.extend(_source_evidence(pack, "controlled_ingestion"))
    else:
        lines.extend(
            [
                "I can answer this better with a dataset/readiness-oriented question.",
                "Try asking about: data overview, model-training blockers, Ableton outputs, or controlled-ingestion next steps.",
            ]
        )
        limitations.append(
            MusicDataLimitation(
                limitation_id="unknown_question_category",
                description="Question did not map cleanly to supported explainer categories.",
                severity="low",
            )
        )

    if not evidence:
        limitations.append(
            MusicDataLimitation(
                limitation_id="limited_evidence",
                description="No direct evidence artifact matched this question category.",
                severity="medium",
            )
        )

    markdown = "\n".join(
        [
            f"## Music Data Explainer ({category})",
            "",
            *lines,
            "",
            "### Evidence",
            *([f"- `{item.artifact_path}` - {item.summary}" for item in evidence] or ["- none"]),
            "",
            "### Uncertainty",
            *([f"- {item.description}" for item in limitations] or ["- no major uncertainty flagged"]),
            "",
        ]
    )
    return ExplainerAnswer(
        question_text=question.question_text,
        category=category,
        answer_markdown=markdown,
        confidence="medium" if limitations else "high",
        evidence_refs=evidence,
        limitations=limitations,
    )


def explain_music_data(question_text: str) -> ExplainerAnswer:
    pack = _load_knowledge_pack()
    question = classify_question(question_text)
    return _render_answer(question, pack)


def main() -> int:
    parser = argparse.ArgumentParser(description="Explain current music data state from local knowledge pack.")
    parser.add_argument("question", help="Plain-English question about current data/readiness.")
    args = parser.parse_args()
    answer = explain_music_data(args.question)
    print(answer.answer_markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
