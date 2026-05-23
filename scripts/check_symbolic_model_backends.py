from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.symbolic_models.backends.registry import check_symbolic_model_backends, list_symbolic_model_providers


def check_backends(output_dir: Path, *, stub_mode: bool = False) -> tuple[Path, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    providers = list_symbolic_model_providers(stub_mode=stub_mode)
    availability = check_symbolic_model_backends(stub_mode=stub_mode)

    payload = {
        "stub_mode": stub_mode,
        "providers": [provider.__dict__ for provider in providers],
        "availability": [item.__dict__ for item in availability],
    }
    json_path = output_dir / "symbolic_model_backends_report.json"
    md_path = output_dir / "symbolic_model_backends_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# Symbolic Model Backend Availability",
        "",
        f"- stub_mode: `{stub_mode}`",
        "",
        "## Providers",
    ]
    for provider in providers:
        lines.append(
            f"- `{provider.provider_id}` ({provider.display_name}) role `{provider.default_role}` capabilities `{provider.capabilities}`"
        )
    lines.extend(["", "## Availability"])
    for item in availability:
        lines.append(
            f"- `{item.provider_id}` available=`{item.available}` role_hint=`{item.role_hint}` "
            f"installation_hint=`{item.installation_hint}` limitations=`{item.limitations}`"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check symbolic model backend availability.")
    parser.add_argument("--output-dir", default="reports/symbolic_models", help="Folder for output report files")
    parser.add_argument("--stub-mode", action="store_true", help="Treat all providers as available stubs")
    args = parser.parse_args()
    json_path, md_path = check_backends(Path(args.output_dir), stub_mode=args.stub_mode)
    print(f"SYMBOLIC_BACKENDS_REPORT_JSON={json_path.as_posix()}")
    print(f"SYMBOLIC_BACKENDS_REPORT_MD={md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
