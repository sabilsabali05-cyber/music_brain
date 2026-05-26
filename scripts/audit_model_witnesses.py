from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_witnesses import ModelWitnessAudit, ModelWitnessStatus, now_iso
from scripts.check_midigpt_setup import evaluate_midigpt_setup
from scripts.check_moonbeam_setup import evaluate_moonbeam_setup
from scripts.check_musicbert_setup import evaluate_musicbert_setup
from scripts.check_source_separation_setup import evaluate_source_separation_setup
from scripts.check_text2midi_setup import evaluate_text2midi_setup
from scripts.check_transcription_witnesses_setup import evaluate_transcription_witnesses_setup
from scripts.run_midigpt_smoke_test import run_midigpt_smoke_test
from scripts.run_moonbeam_smoke_test import run_moonbeam_smoke_test
from scripts.run_musicbert_smoke_test import run_musicbert_smoke_test
from scripts.run_text2midi_smoke_test import run_text2midi_smoke_test

REPORT_DIR = ROOT_DIR / "reports" / "model_witnesses"
REPORT_JSON = REPORT_DIR / "model_witness_audit.json"
REPORT_MD = REPORT_DIR / "model_witness_audit.md"


def _bool(value: Any) -> bool:
    return bool(value)


def _from_setup_and_smoke(
    *,
    witness_id: str,
    witness_name: str,
    witness_type: str,
    backend: str,
    required_for_pipeline: bool,
    setup_payload: dict[str, Any],
    smoke_payload: dict[str, Any],
    configured_key: str,
    available_key: str,
    reason_key: str = "unavailable_reason",
) -> ModelWitnessStatus:
    configured = _bool(setup_payload.get(configured_key, False))
    smoke_passed = _bool(smoke_payload.get("real_smoke_passed", False))
    installed = configured
    available = _bool(smoke_payload.get(available_key, False)) and smoke_passed
    blockers: list[str] = []
    if not configured:
        blockers.append("not_configured")
    if configured and not smoke_passed:
        blockers.append("smoke_test_failed_or_not_run")
    unavailable_reason = str(smoke_payload.get(reason_key) or setup_payload.get(reason_key) or "").strip()
    gate_status = "pass" if available else "blocked"
    return ModelWitnessStatus(
        witness_id=witness_id,
        witness_name=witness_name,
        witness_type=witness_type,
        backend=backend,
        required_for_pipeline=required_for_pipeline,
        configured=configured,
        installed=installed,
        smoke_test_passed=smoke_passed,
        available=available,
        gate_status=gate_status,
        unavailable_reason=unavailable_reason or "unknown",
        blockers=blockers,
        next_setup_step=str(setup_payload.get("next_setup_step", "")).strip(),
        metadata={
            "setup_status": setup_payload.get("status", "unknown"),
            "smoke_status": smoke_payload.get("status", "unknown"),
        },
    )


def build_model_witness_audit() -> ModelWitnessAudit:
    moonbeam_setup = evaluate_moonbeam_setup()
    musicbert_setup = evaluate_musicbert_setup()
    midigpt_setup = evaluate_midigpt_setup()
    text2midi_setup = evaluate_text2midi_setup()
    transcription_setup = evaluate_transcription_witnesses_setup()
    separation_setup = evaluate_source_separation_setup()

    moonbeam_smoke = run_moonbeam_smoke_test()
    musicbert_smoke = run_musicbert_smoke_test()
    midigpt_smoke = run_midigpt_smoke_test()
    text2midi_smoke = run_text2midi_smoke_test()

    witnesses: list[ModelWitnessStatus] = [
        _from_setup_and_smoke(
            witness_id="moonbeam",
            witness_name="Moonbeam",
            witness_type="symbolic_generation",
            backend="local_python",
            required_for_pipeline=False,
            setup_payload=moonbeam_setup,
            smoke_payload=moonbeam_smoke,
            configured_key="moonbeam_configured",
            available_key="moonbeam_available",
        ),
        _from_setup_and_smoke(
            witness_id="musicbert",
            witness_name="MusicBERT",
            witness_type="symbolic_understanding",
            backend="local_python",
            required_for_pipeline=True,
            setup_payload=musicbert_setup,
            smoke_payload=musicbert_smoke,
            configured_key="musicbert_configured",
            available_key="musicbert_available",
        ),
        _from_setup_and_smoke(
            witness_id="midigpt",
            witness_name="MIDI-GPT",
            witness_type="symbolic_generation",
            backend="local_python",
            required_for_pipeline=False,
            setup_payload=midigpt_setup,
            smoke_payload=midigpt_smoke,
            configured_key="midigpt_configured",
            available_key="midigpt_available",
        ),
        _from_setup_and_smoke(
            witness_id="text2midi",
            witness_name="Text2MIDI",
            witness_type="symbolic_generation",
            backend="local_python",
            required_for_pipeline=False,
            setup_payload=text2midi_setup,
            smoke_payload=text2midi_smoke,
            configured_key="text2midi_configured",
            available_key="text2midi_available",
        ),
        ModelWitnessStatus(
            witness_id="transcription_witnesses",
            witness_name="Transcription witnesses",
            witness_type="transcription",
            backend="local_policy_gate",
            required_for_pipeline=False,
            configured=_bool(transcription_setup.get("yourmt3_configured", False) or transcription_setup.get("basic_pitch_configured", False)),
            installed=False,
            smoke_test_passed=False,
            available=_bool(transcription_setup.get("yourmt3_available", False) or transcription_setup.get("basic_pitch_available", False)),
            gate_status="pass" if _bool(transcription_setup.get("yourmt3_available", False) or transcription_setup.get("basic_pitch_available", False)) else "blocked",
            unavailable_reason=str(
                transcription_setup.get("yourmt3_unavailable_reason")
                or transcription_setup.get("basic_pitch_unavailable_reason")
                or "unavailable"
            ),
            blockers=["no_local_transcription_backend"] if not _bool(transcription_setup.get("yourmt3_available", False) or transcription_setup.get("basic_pitch_available", False)) else [],
            next_setup_step=str(transcription_setup.get("next_setup_step", "")),
            metadata={
                "yourmt3_available": _bool(transcription_setup.get("yourmt3_available", False)),
                "basic_pitch_available": _bool(transcription_setup.get("basic_pitch_available", False)),
            },
        ),
        ModelWitnessStatus(
            witness_id="source_separation_witness",
            witness_name="Source separation witness",
            witness_type="source_separation",
            backend="local_policy_gate",
            required_for_pipeline=False,
            configured=_bool(separation_setup.get("demucs_configured", False)),
            installed=False,
            smoke_test_passed=False,
            available=_bool(separation_setup.get("demucs_available", False)),
            gate_status="pass" if _bool(separation_setup.get("demucs_available", False)) else "blocked",
            unavailable_reason=str(separation_setup.get("demucs_unavailable_reason") or "unavailable"),
            blockers=["no_local_demucs_backend"] if not _bool(separation_setup.get("demucs_available", False)) else [],
            next_setup_step=str(separation_setup.get("next_setup_step", "")),
            metadata={"witness_policy": separation_setup.get("witness_policy", "weak_evidence_not_truth")},
        ),
        ModelWitnessStatus(
            witness_id="mt3_basicpitch_omnizart",
            witness_name="MT3/BasicPitch/Omnizart",
            witness_type="transcription_and_symbolic_audio",
            backend="local_policy_gate",
            required_for_pipeline=False,
            configured=_bool(transcription_setup.get("yourmt3_configured", False) or transcription_setup.get("basic_pitch_configured", False)),
            installed=False,
            smoke_test_passed=False,
            available=_bool(
                transcription_setup.get("yourmt3_available", False)
                or transcription_setup.get("basic_pitch_available", False)
                or separation_setup.get("demucs_available", False)
            ),
            gate_status=(
                "pass"
                if _bool(
                    transcription_setup.get("yourmt3_available", False)
                    or transcription_setup.get("basic_pitch_available", False)
                    or separation_setup.get("demucs_available", False)
                )
                else "blocked"
            ),
            unavailable_reason=(
                "not_configured_or_unavailable"
                if not _bool(
                    transcription_setup.get("yourmt3_available", False)
                    or transcription_setup.get("basic_pitch_available", False)
                    or separation_setup.get("demucs_available", False)
                )
                else ""
            ),
            blockers=(
                ["no_mt3_basicpitch_omnizart_backend"]
                if not _bool(
                    transcription_setup.get("yourmt3_available", False)
                    or transcription_setup.get("basic_pitch_available", False)
                    or separation_setup.get("demucs_available", False)
                )
                else []
            ),
            next_setup_step="Configure at least one local MT3/BasicPitch/Omnizart-compatible witness backend and smoke-test it.",
            metadata={
                "yourmt3_available": _bool(transcription_setup.get("yourmt3_available", False)),
                "basic_pitch_available": _bool(transcription_setup.get("basic_pitch_available", False)),
                "demucs_available": _bool(separation_setup.get("demucs_available", False)),
            },
        ),
        ModelWitnessStatus(
            witness_id="texture_witness",
            witness_name="Texture witness",
            witness_type="texture_understanding",
            backend="local_unconfigured",
            required_for_pipeline=False,
            configured=False,
            installed=False,
            smoke_test_passed=False,
            available=False,
            gate_status="blocked",
            unavailable_reason="no_texture_backend_configured",
            blockers=["no_texture_backend_configured"],
            next_setup_step="Configure a local texture witness backend and smoke-test it before use.",
            metadata={},
        ),
    ]

    counters = Counter()
    blockers: list[str] = []
    for witness in witnesses:
        counters["total_witnesses"] += 1
        counters["available"] += 1 if witness.available else 0
        counters["blocked"] += 1 if not witness.available else 0
        if witness.required_for_pipeline and not witness.available:
            counters["required_blocked"] += 1
        blockers.extend([f"{witness.witness_id}:{tag}" for tag in witness.blockers])

    return ModelWitnessAudit(
        generated_at=now_iso(),
        gate_rule="use witness only when configured, installed, and smoke_test_passed are all true",
        witnesses=witnesses,
        counters=dict(counters),
        blockers=sorted(set(blockers)),
        limitations=[
            "No cloud APIs were called by this audit.",
            "No model training was performed.",
            "No source-audio understanding was faked; unavailable systems remain unavailable.",
        ],
    )


def _write_outputs(audit: ModelWitnessAudit) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = audit.to_dict()
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = [
        "# Model Witness Audit",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- gate_rule: `{payload['gate_rule']}`",
        f"- total_witnesses: `{payload['counters'].get('total_witnesses', 0)}`",
        f"- available: `{payload['counters'].get('available', 0)}`",
        f"- blocked: `{payload['counters'].get('blocked', 0)}`",
        f"- required_blocked: `{payload['counters'].get('required_blocked', 0)}`",
        "",
        "## Witnesses",
    ]
    for row in payload["witnesses"]:
        lines.append(
            f"- `{row['witness_name']}` (`{row['witness_id']}`): available=`{str(row['available']).lower()}` "
            f"configured=`{str(row['configured']).lower()}` smoke_test_passed=`{str(row['smoke_test_passed']).lower()}` "
            f"reason=`{row['unavailable_reason']}`"
        )
    lines.extend(["", "## Blockers"])
    if payload["blockers"]:
        lines.extend([f"- {item}" for item in payload["blockers"]])
    else:
        lines.append("- none")
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return REPORT_JSON, REPORT_MD


def main() -> int:
    audit = build_model_witness_audit()
    json_path, md_path = _write_outputs(audit)
    payload = audit.to_dict()
    print(f"MODEL_WITNESS_AUDIT_JSON={json_path.as_posix()}")
    print(f"MODEL_WITNESS_AUDIT_MD={md_path.as_posix()}")
    print(f"MODEL_WITNESS_TOTAL={payload['counters'].get('total_witnesses', 0)}")
    print(f"MODEL_WITNESS_AVAILABLE={payload['counters'].get('available', 0)}")
    print(f"MODEL_WITNESS_BLOCKED={payload['counters'].get('blocked', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
