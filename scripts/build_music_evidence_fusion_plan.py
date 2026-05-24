from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.music_cognition.evidence_fusion_schema import EvidenceFusionPlan, FusionSource  # noqa: E402
from scripts.full_model_activation_common import now_iso, write_report  # noqa: E402

REPORT_DIR = ROOT_DIR / "reports" / "music_cognition"


def build_evidence_fusion_plan() -> EvidenceFusionPlan:
    return EvidenceFusionPlan(
        status="planned",
        fusion_performed=False,
        graph_generated=False,
        model_training_has_occurred=False,
        summary=[
            "Fuse full-mix and stem-level evidence as weighted witnesses, never as automatic ground truth.",
            "Compare transcription witnesses (yourmt3/basic_pitch) for agreement and preserve witness_not_truth semantics.",
            "Treat demucs as weak evidence with explicit confidence penalties and review gating.",
            "Combine essentia, muq, and mert evidence into retrieval/ranking context only.",
            "Feed symbolic ranking and human feedback outcomes into preference rankers, not direct training here.",
        ],
        sources=[
            FusionSource(
                source_id="full_mix_features",
                source_type="mix_level_witness",
                witness_semantics="witness_not_truth",
                enabled=True,
                available=True,
                contribution="global rhythmic, harmonic, and density context",
            ),
            FusionSource(
                source_id="stem_features_demucs",
                source_type="stem_level_weak_evidence",
                witness_semantics="weak_evidence_requires_review",
                enabled=False,
                available=False,
                contribution="optional stem isolation witness with confidence penalty",
            ),
            FusionSource(
                source_id="transcription_witnesses",
                source_type="symbolic_witness",
                witness_semantics="witness_not_truth",
                enabled=False,
                available=False,
                contribution="cross-model agreement and disagreement features",
            ),
            FusionSource(
                source_id="audio_understanding_embeddings",
                source_type="embedding_witness",
                witness_semantics="witness_not_truth",
                enabled=False,
                available=False,
                contribution="essentia/muq/mert support for retrieval and ranking",
            ),
        ],
    )


def main() -> int:
    payload = build_evidence_fusion_plan().as_dict()
    payload["created_at"] = now_iso()
    json_path = REPORT_DIR / "evidence_fusion_plan.json"
    md_path = REPORT_DIR / "evidence_fusion_plan.md"
    write_report(
        payload=payload,
        json_path=json_path,
        md_path=md_path,
        title="Music Evidence Fusion Plan",
        bullets=[
            f"status: `{payload['status']}`",
            f"fusion_performed: `{payload['fusion_performed']}`",
            f"graph_generated: `{payload['graph_generated']}`",
            f"model_training_has_occurred: `{payload['model_training_has_occurred']}`",
            "feedback_to_ranker_path: `planned_preference_learning_only`",
        ],
    )

    # Keep JSON stable and explicit for downstream checks.
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"EVIDENCE_FUSION_PLAN_JSON={json_path.as_posix()}")
    print(f"EVIDENCE_FUSION_PLAN_MD={md_path.as_posix()}")
    print("EVIDENCE_FUSION_STATUS=planned")
    print("FUSION_PERFORMED=False")
    print("GRAPH_GENERATED=False")
    print("MODEL_TRAINING_HAS_OCCURRED=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
