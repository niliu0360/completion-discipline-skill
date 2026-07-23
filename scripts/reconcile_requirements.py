#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from aicl.record_io import read_json_object  # noqa: E402
from aicl.reconciliation import structural_reconciliation  # noqa: E402
from aicl.validation import validate  # noqa: E402


def render(report: dict) -> str:
    counts = report["counts"]
    lines = [
        f"RECONCILIATION {report['status']}",
        (
            f"requirements={counts['requirements']} "
            f"tasks={counts['tasks']} "
            f"evidence={counts['evidence']} "
            f"actions={counts['actions']}"
        ),
    ]
    lines.extend(f"WARN: {item}" for item in report["warnings"])
    lines.extend(f"ERROR: {item}" for item in report["errors"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Completion Discipline structure and mappings."
    )
    parser.add_argument(
        "--record",
        default=".ai-control/control-record.json",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    record = read_json_object(args.record)
    report = structural_reconciliation(
        record,
        semantic_errors=validate(record),
        require_task_mapping=True,
    )
    print(
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.json
        else render(report)
    )
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
