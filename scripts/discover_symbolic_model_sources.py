from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT_DIR / "reports" / "model_integrations"
TIMEOUT_SECONDS = 15
USER_AGENT = "music-brain-source-discovery/1.0"


@dataclass(frozen=True)
class ModelSourceSpec:
    model_name: str
    github_repo: str | None
    github_tree_path: str | None
    huggingface_model: str | None
    paper_url: str | None
    weight_hint_url: str | None
    expected_terms: tuple[str, ...]


MODEL_SPECS: tuple[ModelSourceSpec, ...] = (
    ModelSourceSpec(
        model_name="Moonbeam",
        github_repo="aim-qmul/moonbeam-midi-foundation-model",
        github_tree_path=None,
        huggingface_model=None,
        paper_url="https://arxiv.org/abs/2505.15559",
        weight_hint_url="https://aim-qmul.github.io/moonbeam-midi-foundation-model/",
        expected_terms=("moonbeam", "midi foundation model"),
    ),
    ModelSourceSpec(
        model_name="Text2MIDI",
        github_repo="AMAAI-Lab/Text2midi",
        github_tree_path=None,
        huggingface_model="amaai-lab/text2midi",
        paper_url="https://arxiv.org/abs/2412.16526",
        weight_hint_url="https://huggingface.co/amaai-lab/text2midi",
        expected_terms=("text2midi", "symbolic music"),
    ),
    ModelSourceSpec(
        model_name="MIDI-GPT",
        github_repo="Metacreation-Lab/MIDI-GPT",
        github_tree_path=None,
        huggingface_model=None,
        paper_url="https://arxiv.org/abs/2501.17011",
        weight_hint_url=None,
        expected_terms=("midi-gpt", "multitrack"),
    ),
    ModelSourceSpec(
        model_name="MusicBERT",
        github_repo="microsoft/muzic",
        github_tree_path="musicbert",
        huggingface_model=None,
        paper_url="https://arxiv.org/abs/2106.05630",
        weight_hint_url="https://microsoft.github.io/muzic/musicbert/",
        expected_terms=("musicbert", "symbolic music understanding"),
    ),
)


def _fetch_text(url: str) -> str | None:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.1"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError, TimeoutError):
        return None


def _fetch_json(url: str) -> dict[str, Any] | None:
    text = _fetch_text(url)
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _contains_expected_terms(content: str | None, terms: tuple[str, ...]) -> bool:
    if not content:
        return False
    lowered = content.lower()
    return all(term in lowered for term in terms)


def _verify_arxiv_source(paper_url: str | None, model_name: str) -> bool:
    if not paper_url:
        return False
    content = _fetch_text(paper_url)
    if not content:
        return False
    token = re.sub(r"[^a-z0-9]+", "", model_name.lower())
    return token in re.sub(r"[^a-z0-9]+", "", content.lower())


def _verify_github_source(spec: ModelSourceSpec) -> tuple[bool, bool]:
    if not spec.github_repo:
        return False, False
    api_url = f"https://api.github.com/repos/{spec.github_repo}"
    payload = _fetch_json(api_url)
    if not payload:
        return False, False
    full_name = str(payload.get("full_name", "")).strip()
    source_verified = full_name.lower() == spec.github_repo.lower()
    license_found = isinstance(payload.get("license"), dict) and bool(payload["license"].get("spdx_id"))
    if source_verified and spec.github_tree_path:
        tree_url = f"https://github.com/{spec.github_repo}/tree/main/{spec.github_tree_path}"
        tree_content = _fetch_text(tree_url)
        source_verified = source_verified and _contains_expected_terms(tree_content, (spec.model_name.lower(),))
    return source_verified, license_found


def _verify_huggingface_source(model_id: str | None, expected_terms: tuple[str, ...]) -> tuple[bool, bool, bool]:
    if not model_id:
        return False, False, False
    payload = _fetch_json(f"https://huggingface.co/api/models/{model_id}")
    if not payload:
        return False, False, False
    resolved_id = str(payload.get("id", "")).strip().lower()
    source_verified = resolved_id == model_id.lower()
    card_data = payload.get("cardData")
    license_found = isinstance(card_data, dict) and bool(card_data.get("license"))
    page_content = _fetch_text(f"https://huggingface.co/{model_id}")
    weights_found = source_verified and _contains_expected_terms(page_content, expected_terms)
    return source_verified, license_found, weights_found


def _verify_weight_hint(url: str | None) -> bool:
    if not url:
        return False
    content = _fetch_text(url)
    if not content:
        return False
    lowered = content.lower()
    return "model weights" in lowered or "checkpoint" in lowered or "pretrained" in lowered


def discover_sources() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for spec in MODEL_SPECS:
        github_verified, github_license = _verify_github_source(spec)
        hf_verified, hf_license, hf_weights = _verify_huggingface_source(spec.huggingface_model, spec.expected_terms)
        paper_verified = _verify_arxiv_source(spec.paper_url, spec.model_name)
        source_found = github_verified or hf_verified or paper_verified
        source_verified = github_verified or hf_verified
        source_type = "unknown"
        if github_verified:
            source_type = "github"
        elif hf_verified:
            source_type = "huggingface"
        elif paper_verified:
            source_type = "paper_only"

        license_found = github_license or hf_license
        # Treat pretrained weights as verified only when we can confirm
        # a concrete official model artifact endpoint (HF model API).
        pretrained_weights_found = hf_weights
        download_allowed = source_verified and license_found and pretrained_weights_found

        blocker = ""
        if not source_verified:
            blocker = "blocked_unverified_source"
        elif not license_found:
            blocker = "license_unclear"
        elif not pretrained_weights_found:
            blocker = "weights_not_found"

        records.append(
            {
                "model_name": spec.model_name,
                "source_found": source_found,
                "source_type": source_type,
                "source_verified": source_verified,
                "license_found": license_found,
                "pretrained_weights_found": pretrained_weights_found,
                "download_allowed": download_allowed,
                "blocker": blocker,
            }
        )

    return {
        "status": "ok",
        "source_policy": "official_only_no_random_repositories",
        "cloud_called": False,
        "modal_called": False,
        "automatic_clone_performed": False,
        "automatic_download_performed": False,
        "models": records,
    }


def write_reports(payload: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "symbolic_model_source_discovery.json"
    md_path = output_dir / "symbolic_model_source_discovery.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Symbolic Model Source Discovery",
        "",
        "- status: `ok`",
        "- source_policy: `official_only_no_random_repositories`",
        "- automatic_clone_performed: `False`",
        "- automatic_download_performed: `False`",
        "",
        "## Models",
        "",
    ]
    for row in payload.get("models", []):
        lines.extend(
            [
                f"### {row['model_name']}",
                f"- source_found: `{row['source_found']}`",
                f"- source_type: `{row['source_type']}`",
                f"- source_verified: `{row['source_verified']}`",
                f"- license_found: `{row['license_found']}`",
                f"- pretrained_weights_found: `{row['pretrained_weights_found']}`",
                f"- download_allowed: `{row['download_allowed']}`",
                f"- blocker: `{row['blocker'] or 'none'}`",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover official symbolic model sources without cloning or downloading.")
    parser.add_argument("--output-dir", default=REPORT_DIR.as_posix())
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir

    payload = discover_sources()
    json_path, md_path = write_reports(payload, output_dir)
    print(f"SYMBOLIC_MODEL_SOURCE_DISCOVERY_JSON={json_path.as_posix()}")
    print(f"SYMBOLIC_MODEL_SOURCE_DISCOVERY_MD={md_path.as_posix()}")
    print(f"SOURCE_DISCOVERY_MODEL_COUNT={len(payload.get('models', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
