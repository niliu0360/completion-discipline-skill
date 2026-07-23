#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from aicl.completion_profile import EVIDENCE_CATEGORIES, new_record  # noqa: E402
from aicl.record_io import atomic_write_json  # noqa: E402

VERSION = "0.2.0-beta.1"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a native Completion Discipline Control Record."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--record-path",
        default=".ai-control/control-record.json",
        help="Path relative to project root unless absolute",
    )
    parser.add_argument(
        "--source",
        default="User request or supplied source material",
    )
    parser.add_argument("--title", default="Completion Discipline task")
    parser.add_argument(
        "--objective",
        default="Complete every recorded requirement without silent omission.",
    )
    parser.add_argument(
        "--requirement",
        default="Replace this placeholder with the first requirement",
    )
    parser.add_argument(
        "--acceptance",
        default="Replace this placeholder with an independently verifiable outcome",
    )
    parser.add_argument(
        "--evidence",
        choices=["none", *EVIDENCE_CATEGORIES],
        default="automated_test",
    )
    parser.add_argument(
        "--criticality",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default="MEDIUM",
    )
    parser.add_argument("--scope", default="MODULE:task-scope")
    parser.add_argument("--repository", default="unknown/repository")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--record-id", default="AICR-completion-task")
    parser.add_argument("--contract-id", default="ACON-completion-task")
    parser.add_argument("--risk-id", default="RPA-completion-task")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    record_path = Path(args.record_path).expanduser()
    if not record_path.is_absolute():
        record_path = project_root / record_path
    if record_path.exists() and not args.force:
        raise FileExistsError(
            f"{record_path} already exists; use --force to replace it"
        )

    record = new_record(
        record_id=args.record_id,
        contract_id=args.contract_id,
        risk_id=args.risk_id,
        title=args.title,
        objective=args.objective,
        requirement=args.requirement,
        acceptance=args.acceptance,
        source_ref=args.source,
        repository=args.repository,
        base_ref=args.base_ref,
        scope=args.scope,
        criticality=args.criticality,
        evidence_category=args.evidence,
    )
    atomic_write_json(record_path, record)
    print(
        json.dumps(
            {
                "version": VERSION,
                "created": str(record_path),
                "record_id": args.record_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
