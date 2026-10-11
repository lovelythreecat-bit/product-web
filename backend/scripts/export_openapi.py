"""uv run --project backend python backend/scripts/export_openapi.py [--check]"""

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    # Explicit values neutralize the caller's environment. No DB or network I/O.
    settings = Settings(
        mode="mock",
        test_only=True,
        database_url=None,
        redis_url=None,
        storage_root=None,
        storage_persistent=False,
    )
    schema = create_app(settings).openapi()
    serialized = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    target = BACKEND_ROOT.parent / "contracts" / "openapi.json"
    if args.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != serialized:
            print("OpenAPI is stale; run export_openapi.py and frontend contracts:generate.")
            return 1
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8", newline="\n")
    print("OpenAPI is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
