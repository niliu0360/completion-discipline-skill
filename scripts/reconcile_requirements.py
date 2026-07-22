#!/usr/bin/env python3
"""Validate REQ coverage and cross-file references without judging completion evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import VERSION, linked, load_bundle


def build_report(workdir: Path) -> dict[str, object]:
    bundle = load_bundle(workdir)
    unmapped: list[str] = []
    for req_id in bundle.requirements:
        if not linked(bundle.tasks, req_id) and not linked(bundle.followups, req_id):
            unmapped.append(req_id)

    errors = list(bundle.errors)
    if unmapped:
        errors.append(f"requirements without task or followup mapping: {', '.join(unmapped)}")

    return {
        "version": VERSION,
        "status": "PASS" if not errors else "FAIL",
        "workdir": str(workdir),
        "counts": {
            "requirements": len(bundle.requirements),
            "tasks": len(bundle.tasks),
            "evidence": len(bundle.evidence),
            "followups": len(bundle.followups),
        },
        "unmapped_requirements": unmapped,
        "errors": errors,
        "warnings": bundle.warnings,
    }


def render_text(report: dict[str, object]) -> str:
    counts = report["counts"]
    lines = [
        f"RECONCILIATION {report['status']}",
        f"requirements={counts['requirements']} tasks={counts['tasks']} evidence={counts['evidence']} followups={counts['followups']}",
    ]
    for warning in report["warnings"]:
        lines.append(f"WARN: {warning}")
    for error in report["errors"]:
        lines.append(f"ERROR: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", default=".ai-work", help="Path to the project-local work directory")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    args = parser.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    report = build_report(workdir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
