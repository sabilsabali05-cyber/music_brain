from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRUTHY = {"yes", "no", "unknown"}
LICENSE_STATUS = {"clear", "unclear", "unknown"}
TOKEN_COMPAT = {"compatible", "partially_compatible", "incompatible", "unknown"}
DIFFICULTY = {"low", "medium", "high", "very_high", "unknown"}
REQUIRED_BACKENDS = {"moonbeam", "midigpt", "text2midi", "musicbert"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_feasibility_report() -> dict[str, Any]:
    backends: list[dict[str, Any]] = [
        {
            "provider_id": "moonbeam",
            "display_name": "Moonbeam",
            "expected_input_format": "Tokenized symbolic sequences using Moonbeam's custom absolute+relative attribute tokenizer and checkpoint/tokenizer files.",
            "expected_output_format": "Generated symbolic token sequences decoded back to MIDI (continuation, conditional generation, and infilling workflows).",
            "public_code_installable": "yes",
            "pretrained_weights_required": "yes",
            "license_usage_status": "clear",
            "midi_tokenization_compatibility": "partially_compatible",
            "estimated_integration_difficulty": "high",
            "usable_with_current_repo_state": False,
            "evidence": [
                {
                    "title": "Moonbeam GitHub repository",
                    "url": "https://github.com/guozixunnicolas/moonbeam-midi-foundation-model",
                    "note": "Repository includes dependency installation instructions and checkpoint download instructions.",
                },
                {
                    "title": "Moonbeam project page",
                    "url": "https://aim-qmul.github.io/moonbeam-midi-foundation-model/",
                    "note": "States paper/code/pretrained weights release and Apache License 2.0 status.",
                },
                {
                    "title": "Moonbeam paper",
                    "url": "https://arxiv.org/html/2505.15559",
                    "note": "Describes custom tokenization and downstream continuation/infilling tasks.",
                },
            ],
            "unknowns": {},
            "notes": [
                "Most aligned with our first-generation backend use-case (continuation/infill).",
                "Requires tokenization conversion bridge from current generative examples.",
            ],
        },
        {
            "provider_id": "midigpt",
            "display_name": "MIDI-GPT",
            "expected_input_format": "MIDI-GPT event/token representation for multitrack bar/track infilling with attribute controls.",
            "expected_output_format": "Multitrack MIDI generation/infill outputs from model checkpoint and tokenizer config.",
            "public_code_installable": "yes",
            "pretrained_weights_required": "yes",
            "license_usage_status": "unknown",
            "midi_tokenization_compatibility": "partially_compatible",
            "estimated_integration_difficulty": "high",
            "usable_with_current_repo_state": False,
            "evidence": [
                {
                    "title": "MIDI-GPT GitHub repository",
                    "url": "https://github.com/Metacreation-Lab/MIDI-GPT",
                    "note": "Describes controllable multitrack generation/infill and bundled model checkpoints in repository artifacts.",
                },
                {
                    "title": "MIDI-GPT AAAI paper",
                    "url": "https://ojs.aaai.org/index.php/AAAI/article/view/32138",
                    "note": "Explains controllable multitrack architecture and infill tasks.",
                },
                {
                    "title": "MIDI-GPT Python package",
                    "url": "https://pypi.org/project/midigpt/",
                    "note": "Shows packaged tokenizer/model runtime and checkpoint format expectations.",
                },
            ],
            "unknowns": {
                "license_usage_status": "unknown",
            },
            "notes": [
                "Strong controllable multitrack fit, but representation conversion work is non-trivial.",
                "License status should be manually verified before production usage.",
            ],
        },
        {
            "provider_id": "text2midi",
            "display_name": "Text2MIDI",
            "expected_input_format": "Natural-language prompt with T5 encoder and REMI-based decoder vocabulary/config.",
            "expected_output_format": "Generated symbolic token sequence decoded to MIDI conditioned on text prompt.",
            "public_code_installable": "yes",
            "pretrained_weights_required": "yes",
            "license_usage_status": "unknown",
            "midi_tokenization_compatibility": "partially_compatible",
            "estimated_integration_difficulty": "medium",
            "usable_with_current_repo_state": False,
            "evidence": [
                {
                    "title": "Text2MIDI GitHub repository",
                    "url": "https://github.com/AMAAI-Lab/Text2midi",
                    "note": "Provides code and loading instructions tied to HuggingFace-hosted weights and REMI vocab.",
                },
                {
                    "title": "Text2MIDI HuggingFace model card",
                    "url": "https://huggingface.co/amaai-lab/text2midi",
                    "note": "Documents pretrained weight files and runtime loading process.",
                },
            ],
            "unknowns": {
                "license_usage_status": "unknown",
            },
            "notes": [
                "Good for prompt-driven sketch generation, less direct for continuation/infill from current examples.",
                "Prompt pathway useful but may not be best first backend for example-conditioned generation.",
            ],
        },
        {
            "provider_id": "musicbert",
            "display_name": "MusicBERT",
            "expected_input_format": "OctupleMIDI symbolic encoding for music understanding tasks using fairseq-style checkpoints.",
            "expected_output_format": "Embeddings, classification/similarity/reranking signals; not primarily a MIDI generator backend.",
            "public_code_installable": "yes",
            "pretrained_weights_required": "yes",
            "license_usage_status": "unknown",
            "midi_tokenization_compatibility": "incompatible",
            "estimated_integration_difficulty": "high",
            "usable_with_current_repo_state": False,
            "evidence": [
                {
                    "title": "MusicBERT README",
                    "url": "https://github.com/microsoft/muzic/blob/main/musicbert/README.md",
                    "note": "Describes symbolic understanding scope, OctupleMIDI encoding, and checkpoint requirements.",
                },
                {
                    "title": "Muzic project page",
                    "url": "https://microsoft.github.io/muzic/musicbert/",
                    "note": "Confirms understanding/evaluation orientation and pretrained checkpoint usage.",
                },
            ],
            "unknowns": {
                "license_usage_status": "unknown",
            },
            "notes": [
                "Best used as evaluator/ranker witness, not as first direct generation backend.",
                "Tokenization mismatch with current examples is significant for direct generation.",
            ],
        },
    ]

    return {
        "report_version": "v1",
        "generated_at_utc": _now_iso(),
        "research_constraints": [
            "No heavy dependency installation",
            "No model weight download",
            "No model training",
            "No audio processing",
            "No Modal / transcription workflows",
            "Memory-only claims avoided; explicit links or unknown markers used",
        ],
        "research_sources": sorted(
            {
                item["url"]
                for backend in backends
                for item in backend.get("evidence", [])
                if isinstance(item, dict) and isinstance(item.get("url"), str)
            }
        ),
        "backends": backends,
        "recommended_first_backend": {
            "provider_id": "moonbeam",
            "reason": "Most aligned with continuation/infill goals and has explicit public code + pretrained checkpoint documentation for symbolic generation.",
            "confidence": "medium",
            "prerequisites": [
                "Validate Moonbeam checkpoint/tokenizer licensing and usage terms in repo release artifacts.",
                "Implement deterministic conversion bridge between current generative example representation and Moonbeam tokenizer schema.",
                "Run non-production smoke tests on tiny symbolic fixtures before any weight download phase.",
            ],
            "alternative_candidates": [
                "midigpt for stronger multitrack control once representation bridge/licensing is validated",
                "text2midi for prompt-only sketch mode",
                "musicbert as evaluator/reranker witness",
            ],
        },
    }


def validate_feasibility_report(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["report payload must be an object"]
    if not isinstance(payload.get("report_version"), str):
        errors.append("report_version must be a string")
    if not isinstance(payload.get("generated_at_utc"), str):
        errors.append("generated_at_utc must be a string")

    backends = payload.get("backends")
    if not isinstance(backends, list):
        errors.append("backends must be a list")
        return errors

    seen_ids: set[str] = set()
    for idx, backend in enumerate(backends):
        if not isinstance(backend, dict):
            errors.append(f"backends[{idx}] must be an object")
            continue
        provider_id = backend.get("provider_id")
        if not isinstance(provider_id, str) or not provider_id.strip():
            errors.append(f"backends[{idx}].provider_id is required")
            continue
        seen_ids.add(provider_id)

        for key in ("display_name", "expected_input_format", "expected_output_format"):
            if not isinstance(backend.get(key), str) or not str(backend.get(key)).strip():
                errors.append(f"backends[{idx}].{key} must be a non-empty string")

        if backend.get("public_code_installable") not in TRUTHY:
            errors.append(f"backends[{idx}].public_code_installable must be yes/no/unknown")
        if backend.get("pretrained_weights_required") not in TRUTHY:
            errors.append(f"backends[{idx}].pretrained_weights_required must be yes/no/unknown")
        if backend.get("license_usage_status") not in LICENSE_STATUS:
            errors.append(f"backends[{idx}].license_usage_status must be clear/unclear/unknown")
        if backend.get("midi_tokenization_compatibility") not in TOKEN_COMPAT:
            errors.append(
                f"backends[{idx}].midi_tokenization_compatibility must be compatible/partially_compatible/incompatible/unknown"
            )
        if backend.get("estimated_integration_difficulty") not in DIFFICULTY:
            errors.append(f"backends[{idx}].estimated_integration_difficulty must be low/medium/high/very_high/unknown")
        if not isinstance(backend.get("usable_with_current_repo_state"), bool):
            errors.append(f"backends[{idx}].usable_with_current_repo_state must be boolean")

        evidence = backend.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"backends[{idx}].evidence must be a list")
        elif backend.get("usable_with_current_repo_state") is True and not evidence:
            errors.append(f"backends[{idx}] cannot be marked usable without evidence")

        unknowns = backend.get("unknowns", {})
        if not isinstance(unknowns, dict):
            errors.append(f"backends[{idx}].unknowns must be an object")
        else:
            for key, value in unknowns.items():
                if value != "unknown":
                    errors.append(f"backends[{idx}].unknowns.{key} must equal 'unknown'")

    missing = REQUIRED_BACKENDS - seen_ids
    if missing:
        errors.append(f"missing required backends: {sorted(missing)}")
    return errors


def write_feasibility_report(
    *,
    output_json: Path = Path("reports") / "symbolic_models" / "backend_feasibility_report.json",
    output_md: Path = Path("reports") / "symbolic_models" / "backend_feasibility_report.md",
) -> tuple[Path, Path]:
    payload = build_feasibility_report()
    errors = validate_feasibility_report(payload)
    if errors:
        raise ValueError(f"Feasibility report schema invalid: {errors}")

    output_json = output_json.resolve()
    output_md = output_md.resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Symbolic Backend Feasibility Report",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- recommended_first_backend: `{payload['recommended_first_backend']['provider_id']}`",
        f"- confidence: `{payload['recommended_first_backend']['confidence']}`",
        "",
        "## Recommendation",
        f"- reason: {payload['recommended_first_backend']['reason']}",
        "",
        "## Backend Findings",
    ]
    for backend in payload["backends"]:
        lines.extend(
            [
                "",
                f"### {backend['display_name']} (`{backend['provider_id']}`)",
                f"- expected_input_format: {backend['expected_input_format']}",
                f"- expected_output_format: {backend['expected_output_format']}",
                f"- public_code_installable: `{backend['public_code_installable']}`",
                f"- pretrained_weights_required: `{backend['pretrained_weights_required']}`",
                f"- license_usage_status: `{backend['license_usage_status']}`",
                f"- midi_tokenization_compatibility: `{backend['midi_tokenization_compatibility']}`",
                f"- estimated_integration_difficulty: `{backend['estimated_integration_difficulty']}`",
                f"- usable_with_current_repo_state: `{backend['usable_with_current_repo_state']}`",
                "- evidence:",
            ]
        )
        for ev in backend.get("evidence", []):
            lines.append(f"  - [{ev.get('title', 'source')}]({ev.get('url', '')}) - {ev.get('note', '')}")
        unknowns = backend.get("unknowns", {})
        if unknowns:
            lines.append(f"- unknowns: `{json.dumps(unknowns, ensure_ascii=True)}`")
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_json, output_md


def main() -> int:
    parser = argparse.ArgumentParser(description="Research symbolic backend feasibility using documented sources.")
    parser.add_argument("--output-json", default="reports/symbolic_models/backend_feasibility_report.json")
    parser.add_argument("--output-md", default="reports/symbolic_models/backend_feasibility_report.md")
    args = parser.parse_args()

    json_path, md_path = write_feasibility_report(
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
    )
    print(f"BACKEND_FEASIBILITY_REPORT_JSON={json_path.as_posix()}")
    print(f"BACKEND_FEASIBILITY_REPORT_MD={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
