#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from aicl.completion_migration import atomic_write, migrate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate Completion Discipline 0.1.x .ai-work data."
    )
    parser.add_argument("--workdir", default=".ai-work")
    parser.add_argument(
        "--output",
        default=".ai-control/control-record.json",
    )
    parser.add_argument("--record-id", default="AICR-completion-migration")
    parser.add_argument("--contract-id", default="ACON-completion-migration")
    parser.add_argument("--risk-id", default="RPA-completion-migration")
    parser.add_argument("--title", default="Migrated Completion Discipline task")
    parser.add_argument(
        "--objective",
        default="Preserve and reconcile migrated requirements.",
    )
    parser.add_argument("--repository", default="unknown/repository")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--scope", default="MODULE:migrated-task")
    parser.add_argument(
        "--default-criticality",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default="MEDIUM",
    )
    args = parser.parse_args()

    record, result = migrate(args)
    if record is None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    atomic_write(Path(args.output), record)
    print(
        json.dumps(
            {"output": args.output, **result},
            ensure_ascii=False,
            indent=2,
        )
    )
    if result["status"] == "COMPLETE":
        return 0
    if result["status"] == "CLOSED_WITH_EXCEPTIONS":
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
