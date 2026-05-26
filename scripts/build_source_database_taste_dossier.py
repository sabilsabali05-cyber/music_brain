from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.source_taste_understanding import SourceDatabaseGenerativePrinciple, SourceTasteDossier

CONSENSUS_PATH = ROOT_DIR / "datasets" / "model_witnesses" / "source_audio_witness_consensus.jsonl"
MANIFEST_REPORT = ROOT_DIR / "reports" / "source_audio_study" / "source_audio_study_manifest_report.json"
OUT_REPORT_DIR = ROOT_DIR / "reports" / "source_taste_understanding"
OUT_DATA_DIR = ROOT_DIR / "datasets" / "source_taste_understanding"
DOSSIER_JSON = OUT_REPORT_DIR / "source_database_taste_dossier.json"
DOSSIER_MD = OUT_REPORT_DIR / "source_database_taste_dossier.md"
PRINCIPLES_JSONL = OUT_DATA_DIR / "source_database_generative_principles.jsonl"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _build_principles(consensus_rows: list[dict[str, Any]]) -> list[SourceDatabaseGenerativePrinciple]:
    base_principles = [
        (
            "principle_01_transform_not_copy",
            "Transform structural intent rather than copying melodic phrases.",
            "Consensus rows repeatedly reject direct source-copy behavior.",
            0.82,
            "medium",
        ),
        (
            "principle_02_meter_is_guidance",
            "Use meter and groove hints as guidance with room for reinterpretation.",
            "Witnesses offer probabilistic meter hints with disagreements preserved.",
            0.74,
            "medium",
        ),
        (
            "principle_03_preserve_disagreement",
            "When witnesses conflict, carry conflict into composition constraints.",
            "Consensus schema stores qualitative conflicts explicitly.",
            0.79,
            "medium",
        ),
        (
            "principle_04_weak_evidence_guard",
            "Downgrade confidence where no real backend confirms observations.",
            "Many rows mark no_real_backend_confirmation in weak evidence areas.",
            0.77,
            "medium",
        ),
        (
            "principle_05_policy_first_audio",
            "Only analyze raw audio when manifest analysis_allowed is true.",
            "Study manifest explicitly separates authorization and analysis policies.",
            0.88,
            "high",
        ),
    ]
    supporting = sorted({str(row.get("consensus_id", "")) for row in consensus_rows if str(row.get("consensus_id", "")).strip()})
    principles: list[SourceDatabaseGenerativePrinciple] = []
    for pid, statement, rationale, confidence, quality in base_principles:
        principles.append(
            SourceDatabaseGenerativePrinciple(
                principle_id=pid,
                statement=statement,
                rationale=rationale,
                supporting_witnesses=supporting[:12],
                confidence=confidence,
                evidence_quality=quality,
                transformation_not_copy_note="Original generation only; no phrase-level copying from source material.",
            )
        )
    return principles


def build_dossier() -> tuple[SourceTasteDossier, list[SourceDatabaseGenerativePrinciple]]:
    consensus_rows = _read_jsonl(CONSENSUS_PATH)
    manifest_report = _read_json(MANIFEST_REPORT)
    principles = _build_principles(consensus_rows)
    strongest = [row.to_dict() for row in sorted(principles, key=lambda p: p.confidence, reverse=True)[:5]]
    dossier = SourceTasteDossier(
        dossier_id="source_database_taste_dossier_v1",
        generated_at=datetime.now(UTC).isoformat(),
        source_items_considered=int(manifest_report.get("source_items_considered", len(consensus_rows))),
        source_items_analyzed=sum(1 for row in consensus_rows if not row.get("blockers")),
        strongest_principles=strongest,
        weak_evidence_limits=[
            "Most consensus rows rely on heuristic/local evidence due to unavailable optional backends.",
            "No claim of full source-audio understanding is made when witnesses are unavailable.",
            "Conflicting witness claims remain unresolved without additional validated backends.",
        ],
        witness_influence_summary=[
            "Heuristic local feature witness influences timing and structure hints.",
            "Unavailable backend witnesses only contribute blockers and risk annotations.",
        ],
        rejected_principles=[
            "Do not optimize for musicality score-first outputs.",
            "Do not suppress witness disagreement to produce a single average narrative.",
        ],
        transformation_vs_copy_policy="Generate transformed derivatives guided by principles; avoid direct copying of source content.",
    )
    return dossier, principles


def write_outputs(dossier: SourceTasteDossier, principles: list[SourceDatabaseGenerativePrinciple]) -> tuple[Path, Path, Path]:
    OUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOSSIER_JSON.write_text(json.dumps(dossier.to_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    with PRINCIPLES_JSONL.open("w", encoding="utf-8") as handle:
        for row in principles:
            handle.write(json.dumps(row.to_dict(), ensure_ascii=True) + "\n")
    lines = [
        "# Source Database Taste Dossier",
        "",
        f"- dossier_id: `{dossier.dossier_id}`",
        f"- source_items_considered: `{dossier.source_items_considered}`",
        f"- source_items_analyzed: `{dossier.source_items_analyzed}`",
        f"- transformation_vs_copy_policy: {dossier.transformation_vs_copy_policy}",
        "",
        "## Strongest Principles",
    ]
    for row in dossier.strongest_principles:
        lines.append(f"- `{row['principle_id']}`: {row['statement']} (confidence `{row['confidence']}`)")
    lines.extend(["", "## Weak Evidence Limits"])
    lines.extend([f"- {item}" for item in dossier.weak_evidence_limits])
    DOSSIER_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return DOSSIER_JSON, DOSSIER_MD, PRINCIPLES_JSONL


def main() -> int:
    dossier, principles = build_dossier()
    json_path, md_path, principles_path = write_outputs(dossier, principles)
    print(f"SOURCE_DATABASE_TASTE_DOSSIER_JSON={json_path.as_posix()}")
    print(f"SOURCE_DATABASE_TASTE_DOSSIER_MD={md_path.as_posix()}")
    print(f"SOURCE_DATABASE_GENERATIVE_PRINCIPLES={principles_path.as_posix()}")
    print(f"SOURCE_ITEMS_CONSIDERED={dossier.source_items_considered}")
    print(f"SOURCE_ITEMS_ANALYZED={dossier.source_items_analyzed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
