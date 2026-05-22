from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.external_analyzers.registry import check_external_analyzers


def main() -> int:
    for item in check_external_analyzers():
        payload = {
            "provider_name": item.provider_name,
            "available": item.available,
            "provider_version": item.provider_version,
            "install_notes": item.install_notes,
            "limitations": item.limitations,
            "dependency_info": item.dependency_info,
        }
        print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
