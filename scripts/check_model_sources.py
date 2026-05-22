from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from features.model_sources import list_model_sources


def main() -> int:
    for source in list_model_sources():
        print(
            json.dumps(
                {
                    "provider_id": source.get("provider_id"),
                    "provider_name": source.get("provider_name"),
                    "implementation_status": source.get("implementation_status"),
                    "trust_policy": source.get("trust_policy"),
                    "local_available": source.get("local_available", "unknown"),
                    "dependency_status": source.get("dependency_status"),
                },
                ensure_ascii=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
