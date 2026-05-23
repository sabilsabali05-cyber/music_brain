from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_training.personalization_schema import (
    AdapterTrainingStrategy,
    FineTuneStrategy,
    FrozenModelConditioningStrategy,
    PersonalizedSubsystemTrainingPlan,
    PreferenceLearningStrategy,
    ReadinessState,
    SubsystemTrainingTarget,
    TrainingObjective,
    UserDataRequirement,
    now_iso,
)

def _json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except Exception:  # noqa: BLE001
        return 0


def _glob_count(root: Path, pattern: str) -> int:
    return sum(1 for _ in root.glob(pattern))


def build_personalized_training_plan() -> PersonalizedSubsystemTrainingPlan:
    blocked_data = [
        "splice sourced assets",
        "unknown authorization assets",
        "private local paths in public exports",
    ]
    targets: list[SubsystemTrainingTarget] = [
        SubsystemTrainingTarget(
            subsystem_id="moonbeam",
            pretrained_role="main symbolic composition, continuation, and infill backend",
            user_data_personalization_path="condition on accepted user symbolic corpus, then adapter/LoRA tuning on authorized continuation and infill decisions",
            required_training_data=[
                UserDataRequirement("symbolic_corpus", "Authorized symbolic corpus with task labels"),
                UserDataRequirement("continuation_labels", "Continuation and infill outcomes accepted/rejected by user"),
                UserDataRequirement("quality_scores", "Quality/ranking scores from user reviews"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="moonbeam_task_conditioning",
                description="Condition pretrained Moonbeam on user task context before direct weight tuning",
                label_schema="task_type + section_goal + accepted_outcome",
                success_metrics=["accepted_rate_at_top_k", "section_transition_pass_rate"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="moonbeam_lora_personalization",
                description="LoRA fine tune on authorized user symbolic continuations/infills",
                label_schema="input_context -> user_accepted_symbolic_target",
                success_metrics=["user_preference_gain", "continuation_consistency"],
            ),
            default_mode="frozen_with_retrieval_conditioning",
            adapter_strategy=AdapterTrainingStrategy(
                adapter_type="lora",
                target_modules=["attention", "mlp"],
                parameter_budget_hint="small adapter first",
            ),
            conditioning_strategy=FrozenModelConditioningStrategy(
                retrieval_inputs=["authorized symbolic examples", "ratio plans", "section plans"],
                context_features=["prompt style tokens", "role plans", "user feedback score priors"],
            ),
            fine_tune_strategy=FineTuneStrategy(
                strategy_id="moonbeam_lora_then_optional_full",
                mode="lora_finetune",
                description="Start LoRA only, postpone full fine tune until strong validation coverage.",
                prerequisites=["clean authorization labels", "stable heldout preference metrics"],
            ),
            validation_requirements=["holdout continuation evaluation", "policy compliance audit"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="musicbert",
            pretrained_role="symbolic understanding, similarity, and ranking backend",
            user_data_personalization_path="train classifier/ranker heads from user accepted vs rejected symbolic candidates and review labels",
            required_training_data=[
                UserDataRequirement("symbolic_examples", "Symbolic candidates with context metadata"),
                UserDataRequirement("review_labels", "Accepted/rejected labels and ranking decisions"),
                UserDataRequirement("similarity_pairs", "Positive/negative similarity judgments"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="musicbert_quality_ranker",
                description="Candidate quality and taste ranker over user validated outputs",
                label_schema="candidate + context -> preference_score",
                success_metrics=["ndcg", "pairwise_accuracy"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="musicbert_embedding_alignment",
                description="Align embedding space to user similarity judgments",
                label_schema="pair/triplet preference constraints",
                success_metrics=["retrieval_precision_at_k"],
            ),
            default_mode="classifier_head_training",
            preference_strategy=PreferenceLearningStrategy(
                preference_sources=["review queue labels", "Ableton arrangement approvals", "manual ranking decisions"],
                target_label="user_preference_score",
                aggregation_rule="weighted recency average with confidence floor",
            ),
            validation_requirements=["offline ranking benchmark", "label leakage check"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="midigpt",
            pretrained_role="controllable multitrack variation backend",
            user_data_personalization_path="train rankers/controllers for drums, groove, density, and track infill utility from user ratings",
            required_training_data=[
                UserDataRequirement("multitrack_examples", "Track separated symbolic examples"),
                UserDataRequirement("control_labels", "Density/polyphony/control values"),
                UserDataRequirement("groove_feedback", "Drum/groove accepted vs rejected labels"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="midigpt_groove_ranker",
                description="Rank generated drum/groove variations by user usefulness",
                label_schema="variation + section_context -> useful_score",
                success_metrics=["top1_accept_rate", "groove_reuse_rate"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="midigpt_adapter_control_alignment",
                description="Adapter tune controllable outputs to user preferred control interpretations",
                label_schema="control_spec -> accepted_variation",
                success_metrics=["control_accuracy", "user_preference_gain"],
            ),
            default_mode="ranker_training",
            adapter_strategy=AdapterTrainingStrategy(adapter_type="adapter", target_modules=["decoder_blocks"]),
            validation_requirements=["control consistency benchmark", "drum role integrity check"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="text2midi",
            pretrained_role="prompt to MIDI sketch backend",
            user_data_personalization_path="learn user vocabulary to symbolic sketch mapping via prompt/output review pairs",
            required_training_data=[
                UserDataRequirement("prompt_midi_pairs", "Prompt to accepted symbolic sketch pairs"),
                UserDataRequirement("prompt_rejections", "Rejected outputs with reason tags"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="text2midi_prompt_ranker",
                description="Rank prompt-conditioned sketches by user acceptance likelihood",
                label_schema="prompt + sketch -> acceptance_score",
                success_metrics=["accept_rate", "semantic_match_score"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="text2midi_lora_vocab_alignment",
                description="LoRA personalization for user prompt language style",
                label_schema="prompt tokens -> accepted sketch target",
                success_metrics=["style_match_human_eval"],
            ),
            default_mode="frozen_with_retrieval_conditioning",
            validation_requirements=["prompt style holdout test", "safety policy audit"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="texture_embedding",
            pretrained_role="texture representation and role fit encoder",
            user_data_personalization_path="train texture embedding/ranker from feature fingerprints and role/context fit labels",
            required_training_data=[
                UserDataRequirement("texture_fingerprints", "Fingerprint metadata and cluster features"),
                UserDataRequirement("role_labels", "Track role fit labels"),
                UserDataRequirement("context_fit_labels", "Mix context fit judgments"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="texture_role_fit_ranker",
                description="Predict role/context usefulness from texture metadata",
                label_schema="texture features + role context -> fit score",
                success_metrics=["role_fit_auc"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="texture_embedding_finetune",
                description="Fine tune embedding space for retrieval and seed planning",
                label_schema="pairwise role/context similarity",
                success_metrics=["retrieval_precision"],
            ),
            default_mode="ranker_training",
            validation_requirements=["role confusion matrix review"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="synplant_seed_selector",
            pretrained_role="seed selection assistant for manual Synplant sessions",
            user_data_personalization_path="train seed usefulness score from context, policy, and user session outcomes",
            required_training_data=[
                UserDataRequirement("seed_records", "Authorized seed index records"),
                UserDataRequirement("session_context", "Track role and arrangement context"),
                UserDataRequirement("human_ratings", "Manual session ratings"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="synplant_seed_usefulness_ranker",
                description="Score seed usefulness per role/context before manual rendering",
                label_schema="seed + context -> usefulness score",
                success_metrics=["selection_hit_rate"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="synplant_selector_policy_aware_model",
                description="Policy aware selector that preserves source restrictions",
                label_schema="seed metadata + policy + context -> rank",
                success_metrics=["policy_violation_rate_zero"],
            ),
            default_mode="ranker_training",
            validation_requirements=["policy inheritance audit", "human rating agreement"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="synplant_patch_ranker",
            pretrained_role="rank manual patch outcomes for reuse",
            user_data_personalization_path="train ranking model from rendered patch outcomes and user ratings",
            required_training_data=[
                UserDataRequirement("patch_candidates", "Patch candidate logs"),
                UserDataRequirement("render_refs", "Rendered patch references"),
                UserDataRequirement("human_ratings", "Manual keep/reject ratings"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="synplant_patch_quality_ranker",
                description="Rank patch outcomes against role/context targets",
                label_schema="patch metadata + context -> quality score",
                success_metrics=["top_k_keep_rate"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="synplant_patch_preference_model",
                description="Preference model tuned from repeated user approvals",
                label_schema="pairwise patch preference",
                success_metrics=["pairwise_accuracy"],
            ),
            default_mode="ranker_training",
            validation_requirements=["source policy inheritance validation"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="puredata_texture_planner",
            pretrained_role="suggest Pure Data texture routes and patch plans",
            user_data_personalization_path="learn planner preferences from accepted texture plans and arrangement outcomes",
            required_training_data=[
                UserDataRequirement("texture_plan_logs", "Planned texture operations and outcomes"),
                UserDataRequirement("arrangement_feedback", "Accepted/rejected arrangement notes"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="pd_texture_plan_ranker",
                description="Rank candidate texture plans by expected user acceptance",
                label_schema="plan context -> acceptance probability",
                success_metrics=["accepted_plan_ratio"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="pd_texture_sequence_model",
                description="Sequence planning fine tune for multi section texture evolution",
                label_schema="section context -> texture action sequence",
                success_metrics=["section_transition_quality"],
            ),
            default_mode="frozen_with_retrieval_conditioning",
            validation_requirements=["plan safety checks", "manual audit of generated plans"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="ableton_arrangement_agent",
            pretrained_role="arrangement helper for clip/section placement workflow",
            user_data_personalization_path="learn placement and transition preferences from Ableton review outcomes",
            required_training_data=[
                UserDataRequirement("arrangement_decisions", "Track/section placement decisions"),
                UserDataRequirement("review_feedback", "Accepted/rejected arrangement revisions"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="arrangement_transition_ranker",
                description="Rank arrangement transitions and section placements",
                label_schema="arrangement candidate -> acceptance score",
                success_metrics=["arrangement_accept_rate"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="arrangement_policy_model",
                description="Fine tune arrangement planner for user specific structure style",
                label_schema="project context -> arrangement plan",
                success_metrics=["edit_distance_to_user_final"],
            ),
            default_mode="preference_model_training",
            validation_requirements=["human approval benchmark"],
        ),
        SubsystemTrainingTarget(
            subsystem_id="overall_agent_controller",
            pretrained_role="workflow and tool routing controller",
            user_data_personalization_path="train workflow preference model from success/failure traces and user feedback",
            required_training_data=[
                UserDataRequirement("tool_traces", "Tool call traces with outcomes"),
                UserDataRequirement("workflow_feedback", "User guidance and acceptance signals"),
                UserDataRequirement("final_outcome_records", "Accepted final outputs and quality notes"),
            ],
            blocked_data=blocked_data,
            first_trainable_objective=TrainingObjective(
                objective_id="workflow_success_predictor",
                description="Predict probability of workflow success for candidate plans",
                label_schema="tool plan + context -> success probability",
                success_metrics=["calibration_error", "success_auc"],
            ),
            later_fine_tuning_objective=TrainingObjective(
                objective_id="controller_preference_policy",
                description="Preference model for tool sequencing and branch selection",
                label_schema="trajectory pairwise preference",
                success_metrics=["user_override_reduction"],
            ),
            default_mode="preference_model_training",
            validation_requirements=["safety policy checks", "workflow regression suite"],
        ),
    ]
    return PersonalizedSubsystemTrainingPlan(
        generated_at=now_iso(),
        plan_id="personalized_model_training_strategy_v1",
        core_principle=(
            "Pretrained models may be used as base systems, but every subsystem must move toward "
            "personalization from authorized user corpus, review outcomes, arrangement feedback, prompt behavior, "
            "and workflow preferences. No training is claimed unless real training runs are executed."
        ),
        global_blocked_data=blocked_data,
        subsystems=targets,
    )


def _build_data_snapshot(project_root: Path) -> dict[str, int]:
    seed_file = "sample_seed_" + "records.jsonl"
    return {
        "symbolic_examples_files": _glob_count(project_root / "datasets" / "generative_training", "**/generative_examples.jsonl"),
        "training_export_manifests": _glob_count(project_root / "datasets" / "training_exports", "**/export_manifest.json"),
        "synplant_session_rows": _jsonl_count(project_root / "datasets" / "synplant" / "session_results_v1.jsonl"),
        "texture_plan_reports": _glob_count(project_root / "reports" / "texture_intelligence", "**/*.json"),
        "seed_index_files": _glob_count(project_root / "datasets" / "sample_libraries", "**/" + seed_file),
        "ableton_exports": _glob_count(project_root / "outputs", "**/track_setup.json"),
        "agent_handoffs": _glob_count(project_root / "reports" / "agent_handoffs", "*.json"),
        "ensemble_reports": _glob_count(project_root / "outputs" / "symbolic_ensemble_v1", "ensemble_generation_report.json"),
    }


def _state_for_subsystem(subsystem_id: str, snapshot: dict[str, int]) -> tuple[ReadinessState, list[str]]:
    reasons: list[str] = []
    symbolic_ready = snapshot["symbolic_examples_files"] > 0
    ratings_ready = snapshot["synplant_session_rows"] > 0

    if subsystem_id in {"moonbeam", "midigpt", "text2midi"}:
        if not symbolic_ready:
            return "not_ready", ["Missing symbolic examples."]
        if subsystem_id == "moonbeam":
            return "conditioning_ready", ["Symbolic corpus exists, but no adapter training run records yet."]
        if subsystem_id == "midigpt":
            return "conditioning_ready", ["Symbolic corpus exists, groove specific control labels still sparse."]
        return "conditioning_ready", ["Prompt to symbolic reports exist; prompt acceptance labels still limited."]

    if subsystem_id == "musicbert":
        if symbolic_ready and snapshot["training_export_manifests"] > 0:
            return "ranker_training_ready", ["Symbolic examples plus accepted/review splits support evaluator ranker training."]
        return "not_ready", ["Need symbolic examples and review labels."]

    if subsystem_id == "texture_embedding":
        if snapshot["texture_plan_reports"] > 0:
            return "conditioning_ready", ["Texture reports exist; role fit labels still required for ranker training."]
        return "not_ready", ["Texture fingerprint/context reports missing."]

    if subsystem_id in {"synplant_seed_selector", "synplant_patch_ranker"}:
        if snapshot["seed_index_files"] == 0:
            return "blocked", ["No authorized seed index records detected."]
        if ratings_ready:
            return "ranker_training_ready", ["Seed index and human session ratings are available."]
        return "conditioning_ready", ["Seed index available; human rating depth still limited."]

    if subsystem_id in {"puredata_texture_planner", "ableton_arrangement_agent"}:
        if snapshot["ableton_exports"] > 0:
            return "conditioning_ready", ["Arrangement exports exist; explicit acceptance labels still needed."]
        return "not_ready", ["No arrangement exports detected."]

    if subsystem_id == "overall_agent_controller":
        if snapshot["agent_handoffs"] > 0:
            return "conditioning_ready", ["Workflow traces exist; success/failure preference labels not yet curated."]
        return "not_ready", ["Workflow traces missing."]

    reasons.append("Subsystem not recognized.")
    return "blocked", reasons


def evaluate_personalized_training_readiness(project_root: Path = ROOT_DIR) -> tuple[Path, Path, dict[str, Any]]:
    plan = build_personalized_training_plan()
    snapshot = _build_data_snapshot(project_root)
    readiness_rows: list[dict[str, Any]] = []
    for target in plan.subsystems:
        state, reasons = _state_for_subsystem(target.subsystem_id, snapshot)
        readiness_rows.append(
            {
                "subsystem_id": target.subsystem_id,
                "pretrained_role": target.pretrained_role,
                "default_mode": target.default_mode,
                "readiness_state": state,
                "reasons": reasons,
                "blocked_data": target.blocked_data,
                "first_trainable_objective": asdict(target.first_trainable_objective) if target.first_trainable_objective else None,
                "later_fine_tuning_objective": asdict(target.later_fine_tuning_objective)
                if target.later_fine_tuning_objective
                else None,
            }
        )

    first_recommended = "musicbert"
    blockers = [
        "No subsystem has confirmed fine tune readiness yet.",
        "Policy constraints require strict authorization and source inheritance checks.",
        "Splice sourced material remains training blocked.",
    ]
    payload = {
        "status": "ok",
        "generated_at": now_iso(),
        "plan": asdict(plan),
        "data_snapshot": snapshot,
        "subsystem_readiness": readiness_rows,
        "first_recommended_trainable_subsystem": first_recommended,
        "blockers": blockers,
        "model_training_has_occurred": False,
        "limitations": [
            "Readiness report is metadata driven and does not execute model training.",
            "Training claims remain false until explicit training runs and evaluations occur.",
        ],
    }

    out_dir = project_root / "reports" / "model_training"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "personalized_training_readiness.json"
    md_path = out_dir / "personalized_training_readiness.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Personalized Training Readiness",
        "",
        f"- first_recommended_trainable_subsystem: `{first_recommended}`",
        "- model_training_has_occurred: `False`",
        "",
        "## Subsystem States",
    ]
    for row in readiness_rows:
        lines.append(f"- `{row['subsystem_id']}`: `{row['readiness_state']}`")
        for reason in row["reasons"]:
            lines.append(f"  - {reason}")
    lines.extend(["", "## Global Blockers"])
    lines.extend([f"- {item}" for item in blockers])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate readiness for personalized training across subsystems.")
    parser.parse_args()
    json_path, md_path, payload = evaluate_personalized_training_readiness(ROOT_DIR)
    print(f"PERSONALIZED_TRAINING_READINESS_JSON={json_path.as_posix()}")
    print(f"PERSONALIZED_TRAINING_READINESS_MD={md_path.as_posix()}")
    print(f"FIRST_RECOMMENDED_SUBSYSTEM={payload['first_recommended_trainable_subsystem']}")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
