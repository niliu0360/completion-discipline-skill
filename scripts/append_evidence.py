#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from aicl.completion_profile import append_evidence  # noqa: E402
from aicl.record_io import atomic_write_json, read_json_object  # noqa: E402
from aicl.validation import validate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append one immutable evidence entry to a Control Record."
    )
    parser.add_argument(
        "--record",
        default=".ai-control/control-record.json",
    )
    parser.add_argument("--entry", required=True)
    args = parser.parse_args()

    record = read_json_object(args.record)
    entry = read_json_object(args.entry)
    append_evidence(record, entry)
    errors = validate(record)
    if errors:
        print(
            json.dumps(
                {"status": "INVALID", "errors": errors},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    atomic_write_json(args.record, record)
    print(
        json.dumps(
            {
                "appended": entry["evidence_id"],
                "record": args.record,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
