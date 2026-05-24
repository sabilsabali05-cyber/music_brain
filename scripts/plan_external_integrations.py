from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "integrations"
INVENTORY_JSON = REPORT_DIR / "integration_inventory.json"
INVENTORY_MD = REPORT_DIR / "integration_inventory.md"

FIELD_ORDER = [
    "name",
    "category",
    "role in music_brain",
    "priority",
    "required credentials",
    "cost risk",
    "privacy risk",
    "training/legal risk",
    "local vs cloud",
    "first practical use",
    "blocked_by",
    "recommended dev task name",
]

PRIORITY_RULES = {
    "Hugging Face": "now",
    "Max for Live bridge": "now",
    "DuckDB/Postgres metadata DB": "soon",
    "Qdrant/Chroma vector DB": "soon",
    "Modal/HF Jobs GPU execution": "soon",
    "W&B/MLflow eval tracking": "later",
    "DVC dataset versioning": "later",
}

PRIVATE_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\Users\\|/Users/|/home/)", re.IGNORECASE)


def _inventory_rows() -> list[dict[str, Any]]:
    return [
        {
            "name": "Hugging Face",
            "category": "model-hosting-and-artifacts",
            "role in music_brain": "Primary model/dataset registry and optional bucket target.",
            "priority": "now",
            "required credentials": "HF token (scoped), optional org write permission.",
            "cost risk": "low",
            "privacy risk": "medium",
            "training/legal risk": "medium",
            "local vs cloud": "hybrid",
            "first practical use": "Mirror approved model metadata and publish non-sensitive evaluation artifacts.",
            "blocked_by": ["privacy redaction policy", "artifact allowlist"],
            "recommended dev task name": "sync-hf-integration-metadata",
        },
        {
            "name": "Modal/HF Jobs GPU execution",
            "category": "remote-execution",
            "role in music_brain": "Burst GPU execution for heavy witness/eval jobs, never default local path.",
            "priority": "soon",
            "required credentials": "Modal token or HF Jobs token with project scope.",
            "cost risk": "high",
            "privacy risk": "medium",
            "training/legal risk": "medium",
            "local vs cloud": "cloud",
            "first practical use": "Run bounded witness jobs for approved batches with explicit run manifests.",
            "blocked_by": ["budget caps", "egress policy", "job provenance logging"],
            "recommended dev task name": "pilot-remote-gpu-batch-runner",
        },
        {
            "name": "Replicate",
            "category": "external-model-inference",
            "role in music_brain": "Optional external witness inference for comparison-only analyses.",
            "priority": "later",
            "required credentials": "Replicate API token.",
            "cost risk": "high",
            "privacy risk": "high",
            "training/legal risk": "medium",
            "local vs cloud": "cloud",
            "first practical use": "Compare one witness model output against local baseline on redacted fixtures.",
            "blocked_by": ["data minimization gate", "provider legal review"],
            "recommended dev task name": "prototype-replicate-witness-adapter",
        },
        {
            "name": "RunPod/Lambda/Paperspace",
            "category": "alternative-gpu-vendors",
            "role in music_brain": "Fallback compute vendors for overflow capacity if primary remote path is constrained.",
            "priority": "later",
            "required credentials": "Vendor API keys and per-project billing controls.",
            "cost risk": "high",
            "privacy risk": "high",
            "training/legal risk": "medium",
            "local vs cloud": "cloud",
            "first practical use": "Documented fallback profile only; no runtime wiring until cost controls are mature.",
            "blocked_by": ["vendor review", "cost alerts", "security review"],
            "recommended dev task name": "draft-fallback-gpu-vendor-profile",
        },
        {
            "name": "W&B/MLflow eval tracking",
            "category": "experiment-tracking",
            "role in music_brain": "Track evaluation metrics, run metadata, and comparison dashboards.",
            "priority": "later",
            "required credentials": "W&B API key or MLflow tracking endpoint token.",
            "cost risk": "medium",
            "privacy risk": "medium",
            "training/legal risk": "low",
            "local vs cloud": "hybrid",
            "first practical use": "Log non-audio eval metrics from deterministic fixture runs.",
            "blocked_by": ["metrics schema freeze", "artifact redaction policy"],
            "recommended dev task name": "add-eval-tracking-abstraction",
        },
        {
            "name": "DVC dataset versioning",
            "category": "dataset-governance",
            "role in music_brain": "Version controlled manifests for approved dataset slices and lineage.",
            "priority": "later",
            "required credentials": "Git remote plus optional object storage credentials.",
            "cost risk": "medium",
            "privacy risk": "medium",
            "training/legal risk": "medium",
            "local vs cloud": "hybrid",
            "first practical use": "Track manifest-only dataset revisions before any training export.",
            "blocked_by": ["dataset schema lock", "storage backend choice"],
            "recommended dev task name": "introduce-dvc-manifest-tracking",
        },
        {
            "name": "LakeFS",
            "category": "dataset-governance",
            "role in music_brain": "Branchable data lake workflows for larger-scale data governance.",
            "priority": "later",
            "required credentials": "LakeFS access key and secret key.",
            "cost risk": "medium",
            "privacy risk": "medium",
            "training/legal risk": "medium",
            "local vs cloud": "cloud",
            "first practical use": "Evaluate branch/merge semantics on synthetic metadata only.",
            "blocked_by": ["infrastructure ownership", "object storage decision"],
            "recommended dev task name": "evaluate-lakefs-branching-fit",
        },
        {
            "name": "Qdrant/Chroma vector DB",
            "category": "retrieval-memory",
            "role in music_brain": "Store embeddings for retrieval against segment and symbolic metadata.",
            "priority": "soon",
            "required credentials": "None for local; API token for hosted deployments.",
            "cost risk": "medium",
            "privacy risk": "medium",
            "training/legal risk": "low",
            "local vs cloud": "hybrid",
            "first practical use": "Prototype retrieval over text-safe feature summaries, not raw audio.",
            "blocked_by": ["embedding schema", "retention policy"],
            "recommended dev task name": "prototype-vector-retrieval-index",
        },
        {
            "name": "Weaviate",
            "category": "retrieval-memory",
            "role in music_brain": "Alternative vector-native retrieval backend with schema tooling.",
            "priority": "later",
            "required credentials": "Endpoint key for hosted cluster.",
            "cost risk": "medium",
            "privacy risk": "medium",
            "training/legal risk": "low",
            "local vs cloud": "hybrid",
            "first practical use": "Schema benchmark against Qdrant/Chroma using synthetic records.",
            "blocked_by": ["vector backend decision"],
            "recommended dev task name": "benchmark-weaviate-schema-overhead",
        },
        {
            "name": "DuckDB/Postgres metadata DB",
            "category": "metadata-storage",
            "role in music_brain": "Canonical structured metadata store for runs, policies, and manifests.",
            "priority": "soon",
            "required credentials": "None for DuckDB; Postgres user/password for server mode.",
            "cost risk": "low",
            "privacy risk": "low",
            "training/legal risk": "low",
            "local vs cloud": "hybrid",
            "first practical use": "Persist run summaries and integration statuses in deterministic tables.",
            "blocked_by": ["metadata schema version 1"],
            "recommended dev task name": "bootstrap-metadata-db-schema",
        },
        {
            "name": "SQLite",
            "category": "metadata-storage",
            "role in music_brain": "Minimal local fallback metadata DB for quick prototypes.",
            "priority": "later",
            "required credentials": "None.",
            "cost risk": "low",
            "privacy risk": "low",
            "training/legal risk": "low",
            "local vs cloud": "local",
            "first practical use": "Standalone local experiments when Postgres is unavailable.",
            "blocked_by": ["decision to support extra local backend"],
            "recommended dev task name": "assess-sqlite-fallback-scope",
        },
        {
            "name": "S3/R2/Hugging Face Buckets",
            "category": "object-storage",
            "role in music_brain": "Store sanitized artifacts, manifests, and reproducible report bundles.",
            "priority": "soon",
            "required credentials": "Access key/secret pair scoped to artifact bucket.",
            "cost risk": "medium",
            "privacy risk": "high",
            "training/legal risk": "medium",
            "local vs cloud": "cloud",
            "first practical use": "Publish report bundles that are already privacy-checked and path-scrubbed.",
            "blocked_by": ["bucket lifecycle policy", "public/private boundary rules"],
            "recommended dev task name": "define-artifact-bucket-publishing-policy",
        },
        {
            "name": "Max for Live bridge",
            "category": "daw-integration",
            "role in music_brain": "Bridge runtime control between generated plans and Ableton Live sessions.",
            "priority": "now",
            "required credentials": "None; requires local Ableton + Max environment.",
            "cost risk": "low",
            "privacy risk": "low",
            "training/legal risk": "low",
            "local vs cloud": "local",
            "first practical use": "Trigger clip/scene metadata exchange via local bridge shim.",
            "blocked_by": ["bridge protocol spec", "local Ableton smoke fixture"],
            "recommended dev task name": "define-max-for-live-bridge-contract",
        },
        {
            "name": "Ableton Live API",
            "category": "daw-integration",
            "role in music_brain": "Read/write session metadata and transport control inside Live projects.",
            "priority": "soon",
            "required credentials": "None; local DAW access.",
            "cost risk": "low",
            "privacy risk": "low",
            "training/legal risk": "low",
            "local vs cloud": "local",
            "first practical use": "Extract deterministic session state snapshot from fixture Live Set.",
            "blocked_by": ["Max for Live bridge contract"],
            "recommended dev task name": "add-live-api-session-snapshot-export",
        },
        {
            "name": "OSC/WebSocket/Node for Max",
            "category": "bridge-transport",
            "role in music_brain": "Transport layer for real-time message passing between Python and Max patchers.",
            "priority": "soon",
            "required credentials": "None for local loopback; certs if remote relay is added.",
            "cost risk": "low",
            "privacy risk": "low",
            "training/legal risk": "low",
            "local vs cloud": "local",
            "first practical use": "Local loopback event stream for cue and section control events.",
            "blocked_by": ["message schema", "bridge protocol tests"],
            "recommended dev task name": "prototype-max-transport-loopback",
        },
        {
            "name": "Essentia/Librosa analysis stack",
            "category": "audio-analysis-libraries",
            "role in music_brain": "Feature extraction and signal-level descriptors for witness analysis.",
            "priority": "soon",
            "required credentials": "None.",
            "cost risk": "low",
            "privacy risk": "medium",
            "training/legal risk": "low",
            "local vs cloud": "local",
            "first practical use": "Compute deterministic descriptor summaries from approved local fixtures only.",
            "blocked_by": ["analysis schema freeze"],
            "recommended dev task name": "stabilize-local-audio-descriptor-schema",
        },
        {
            "name": "Demucs",
            "category": "source-separation",
            "role in music_brain": "Optional source separation witness path for stem-oriented review.",
            "priority": "soon",
            "required credentials": "None for local model weights already available.",
            "cost risk": "medium",
            "privacy risk": "medium",
            "training/legal risk": "medium",
            "local vs cloud": "local",
            "first practical use": "Produce stem witness metadata on policy-approved local test clips.",
            "blocked_by": ["source authorization policy", "model availability check"],
            "recommended dev task name": "formalize-demucs-witness-manifest",
        },
        {
            "name": "Basic Pitch/YourMT3",
            "category": "transcription-witnesses",
            "role in music_brain": "Parallel transcription witnesses to improve confidence scoring, not ground truth.",
            "priority": "soon",
            "required credentials": "None for local; remote token if cloud fallback is enabled.",
            "cost risk": "medium",
            "privacy risk": "medium",
            "training/legal risk": "medium",
            "local vs cloud": "hybrid",
            "first practical use": "Generate side-by-side witness MIDI confidence reports from fixture inputs.",
            "blocked_by": ["witness-not-truth policy", "confidence aggregation rules"],
            "recommended dev task name": "add-transcription-witness-consensus-report",
        },
        {
            "name": "miditok/pretty_midi/mido/music21",
            "category": "symbolic-midi-tooling",
            "role in music_brain": "Tokenization, parsing, transformation, and music-theory feature derivation for MIDI.",
            "priority": "now",
            "required credentials": "None.",
            "cost risk": "low",
            "privacy risk": "low",
            "training/legal risk": "low",
            "local vs cloud": "local",
            "first practical use": "Build deterministic symbolic feature transforms for generated and witness MIDI.",
            "blocked_by": ["symbolic schema version 1"],
            "recommended dev task name": "lock-symbolic-midi-transform-pipeline",
        },
        {
            "name": "FastAPI",
            "category": "service-layer",
            "role in music_brain": "Expose local orchestration endpoints for tools and DAW bridge adapters.",
            "priority": "soon",
            "required credentials": "None for local dev; auth secret if network exposure is added.",
            "cost risk": "low",
            "privacy risk": "medium",
            "training/legal risk": "low",
            "local vs cloud": "hybrid",
            "first practical use": "Serve a local-only integration status endpoint consumed by Max bridge tooling.",
            "blocked_by": ["API contract", "local auth mode decision"],
            "recommended dev task name": "create-local-integration-status-api",
        },
    ]


def _validate_inventory(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        for field in FIELD_ORDER:
            if field not in row:
                raise ValueError(f"Missing field '{field}' in record '{row.get('name', '<unknown>')}'.")
        if row["priority"] not in {"now", "soon", "later"}:
            raise ValueError(f"Invalid priority '{row['priority']}' in '{row['name']}'.")
        if not isinstance(row["blocked_by"], list):
            raise ValueError(f"'blocked_by' must be a list in '{row['name']}'.")

    index = {row["name"]: row for row in rows}
    for name, required_priority in PRIORITY_RULES.items():
        current = index.get(name)
        if current is None:
            raise ValueError(f"Required integration '{name}' is missing.")
        if current["priority"] != required_priority:
            raise ValueError(
                f"Priority rule violation for '{name}': "
                f"expected '{required_priority}' got '{current['priority']}'."
            )


def _ordered_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in FIELD_ORDER}


def _render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Integration Inventory",
        "",
        "Deterministic inventory of external integrations for `music_brain` planning. "
        "This report does not process audio, call cloud services, or trigger training.",
        "",
        f"- integration_count: `{len(rows)}`",
        "- priority_scale: `now | soon | later`",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['name']}",
                f"- category: `{row['category']}`",
                f"- role in music_brain: {row['role in music_brain']}",
                f"- priority: `{row['priority']}`",
                f"- required credentials: {row['required credentials']}",
                f"- cost risk: `{row['cost risk']}`",
                f"- privacy risk: `{row['privacy risk']}`",
                f"- training/legal risk: `{row['training/legal risk']}`",
                f"- local vs cloud: `{row['local vs cloud']}`",
                f"- first practical use: {row['first practical use']}",
                f"- blocked_by: {', '.join(row['blocked_by']) if row['blocked_by'] else 'none'}",
                f"- recommended dev task name: `{row['recommended dev task name']}`",
                "",
            ]
        )
    return "\n".join(lines)


def _privacy_check(text: str) -> None:
    if PRIVATE_PATH_PATTERN.search(text):
        raise ValueError("Generated output contains private/local absolute path patterns.")


def build_integration_inventory() -> list[dict[str, Any]]:
    rows = [_ordered_row(row) for row in _inventory_rows()]
    _validate_inventory(rows)
    return rows


def write_inventory_reports(
    json_path: Path = INVENTORY_JSON,
    markdown_path: Path = INVENTORY_MD,
) -> tuple[Path, Path, list[dict[str, Any]]]:
    rows = build_integration_inventory()
    json_payload = {"schema_version": 1, "integrations": rows}
    json_text = json.dumps(json_payload, indent=2, ensure_ascii=True) + "\n"
    markdown_text = _render_markdown(rows)
    _privacy_check(json_text)
    _privacy_check(markdown_text)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text, encoding="utf-8")
    markdown_path.write_text(markdown_text, encoding="utf-8")
    return json_path, markdown_path, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build integration inventory reports.")
    parser.add_argument("--json-output", default="reports/integrations/integration_inventory.json")
    parser.add_argument("--md-output", default="reports/integrations/integration_inventory.md")
    args = parser.parse_args()
    json_path, markdown_path, rows = write_inventory_reports(
        json_path=ROOT_DIR / args.json_output,
        markdown_path=ROOT_DIR / args.md_output,
    )
    print(f"INTEGRATION_INVENTORY_JSON={json_path.as_posix()}")
    print(f"INTEGRATION_INVENTORY_MD={markdown_path.as_posix()}")
    print(f"INTEGRATION_INVENTORY_COUNT={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
