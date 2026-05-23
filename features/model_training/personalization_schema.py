from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

TrainingMode = Literal[
    "frozen_with_retrieval_conditioning",
    "adapter_training",
    "lora_finetune",
    "classifier_head_training",
    "ranker_training",
    "preference_model_training",
    "full_finetune_later",
    "not_trainable_yet",
]

ReadinessState = Literal[
    "not_ready",
    "conditioning_ready",
    "ranker_training_ready",
    "adapter_training_ready",
    "fine_tune_ready",
    "blocked",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class UserDataRequirement:
    requirement_id: str
    description: str
    required: bool = True
    source_examples: list[str] = field(default_factory=list)
    blocked_if_missing: bool = False


@dataclass
class TrainingObjective:
    objective_id: str
    description: str
    label_schema: str
    success_metrics: list[str] = field(default_factory=list)


@dataclass
class TrainingBlocker:
    blocker_id: str
    reason: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    requires_policy_fix: bool = False


@dataclass
class FineTuneStrategy:
    strategy_id: str
    mode: TrainingMode
    description: str
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class AdapterTrainingStrategy:
    adapter_type: str
    target_modules: list[str] = field(default_factory=list)
    parameter_budget_hint: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class FrozenModelConditioningStrategy:
    retrieval_inputs: list[str] = field(default_factory=list)
    context_features: list[str] = field(default_factory=list)
    inference_constraints: list[str] = field(default_factory=list)


@dataclass
class PreferenceLearningStrategy:
    preference_sources: list[str] = field(default_factory=list)
    target_label: str = ""
    aggregation_rule: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class SubsystemTrainingTarget:
    subsystem_id: str
    pretrained_role: str
    user_data_personalization_path: str
    required_training_data: list[UserDataRequirement] = field(default_factory=list)
    blocked_data: list[str] = field(default_factory=list)
    first_trainable_objective: TrainingObjective | None = None
    later_fine_tuning_objective: TrainingObjective | None = None
    default_mode: TrainingMode = "not_trainable_yet"
    adapter_strategy: AdapterTrainingStrategy | None = None
    conditioning_strategy: FrozenModelConditioningStrategy | None = None
    preference_strategy: PreferenceLearningStrategy | None = None
    fine_tune_strategy: FineTuneStrategy | None = None
    validation_requirements: list[str] = field(default_factory=list)


@dataclass
class PersonalizedSubsystemTrainingPlan:
    generated_at: str
    plan_id: str
    core_principle: str
    global_blocked_data: list[str] = field(default_factory=list)
    subsystems: list[SubsystemTrainingTarget] = field(default_factory=list)
