#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from aicl.record_io import atomic_write_json, read_json_object  # noqa: E402
from aicl.reconciliation import completion_reconciliation  # noqa: E402
from aicl.validation import validate  # noqa: E402


def render(report: dict) -> str:
    lines = [f"COMPLETION STATUS: {report['status']}"]
    if report["status"] == "INVALID":
        lines.extend(f"ERROR: {item}" for item in report["errors"])
        return "\n".join(lines)
    summary = report["summary"]
    lines.append(
        " ".join(
            f"{key}={summary.get(key, 0)}"
            for key in (
                "total",
                "completed",
                "deferred",
                "rejected",
                "out_of_scope",
                "in_progress",
                "missing",
            )
        )
    )
    for item in report["requirements"]:
        lines.append(
            f"- {item['req_id']} [{item['state']}]: "
            + "; ".join(item["reasons"])
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive the Completion Discipline status from a Control Record."
    )
    parser.add_argument(
        "--record",
        default=".ai-control/control-record.json",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument(
        "--report",
        help=(
            "Output path for the derived report. Defaults to a derived directory "
            "beside the selected Control Record."
        ),
    )
    args = parser.parse_args()

    record = read_json_object(args.record)
    report = completion_reconciliation(
        record,
        semantic_errors=validate(record),
        require_task_mapping=True,
    )
    if args.write_report:
        report_path = (
            Path(args.report).expanduser()
            if args.report
            else Path(args.record).expanduser().resolve().parent
            / "derived"
            / "completion-report.json"
        )
        atomic_write_json(report_path, report)
    print(
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.json
        else render(report)
    )
    if report["status"] == "COMPLETE":
        return 0
    if report["status"] == "CLOSED_WITH_EXCEPTIONS":
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
