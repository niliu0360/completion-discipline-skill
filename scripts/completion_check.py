#!/usr/bin/env python3
"""Classify every requirement and generate a deterministic completion report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _common import VERSION, Requirement, clean_record, linked, load_bundle

OPEN = {"pending", "in_progress"}


def _passing_evidence(evidence: list[dict[str, Any]], need: str) -> list[dict[str, Any]]:
    return [item for item in evidence if item.get("type") == need and item.get("status") == "pass"]


def classify_requirement(
    req: Requirement,
    tasks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    followups: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    missing_needs: list[str] = []
    task_statuses = {task.get("status") for task in tasks}
    open_followups = [item for item in followups if item.get("status") in OPEN]
    deferred_followups = [item for item in open_followups if item.get("category") == "deferred"]
    blocking_followups = [item for item in open_followups if item.get("category") != "deferred"]

    if any(status in OPEN for status in task_statuses):
        reasons.append("linked task is pending or in progress")
    if blocking_followups:
        reasons.append("open verification, decision, or other followup remains")

    if reasons:
        state = "in_progress"
    else:
        deferred_tasks = [task for task in tasks if task.get("status") == "deferred"]
        rejected_tasks = [task for task in tasks if task.get("status") == "rejected"]

        if deferred_followups or deferred_tasks:
            state = "deferred"
            reasons.append("explicitly deferred with a recorded reason and next action")
        elif rejected_tasks:
            state = "rejected"
            reasons.append("explicitly rejected and disclosed to the user")
        elif not tasks:
            state = "missing"
            reasons.append("no linked task or valid exception")
        elif any(task.get("status") != "completed" for task in tasks):
            state = "in_progress"
            reasons.append("linked task has no final accounted state")
        else:
            if req.needs != ("(none)",):
                for need in req.needs:
                    if not _passing_evidence(evidence, need):
                        missing_needs.append(need)
            if missing_needs:
                state = "in_progress"
                reasons.append(f"missing passing evidence: {', '.join(missing_needs)}")
            else:
                state = "completed"
                reasons.append("all linked tasks completed and declared evidence needs satisfied")

    return {
        "req_id": req.req_id,
        "description": req.description,
        "needs": list(req.needs),
        "state": state,
        "reasons": reasons,
        "missing_needs": missing_needs,
        "task_ids": [task.get("task_id") for task in tasks],
        "evidence_ids": [item.get("evidence_id") for item in evidence if item.get("status") == "pass"],
        "followup_ids": [item.get("followup_id") for item in followups],
    }


def build_report(workdir: Path) -> dict[str, Any]:
    bundle = load_bundle(workdir)
    if bundle.errors:
        return {
            "version": VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "INVALID",
            "summary": {"total": len(bundle.requirements)},
            "requirements": [],
            "errors": bundle.errors,
            "warnings": bundle.warnings,
        }

    results = []
    for req in bundle.requirements.values():
        results.append(
            classify_requirement(
                req,
                linked(bundle.tasks, req.req_id),
                linked(bundle.evidence, req.req_id),
                linked(bundle.followups, req.req_id),
            )
        )

    counts = {state: 0 for state in ("completed", "deferred", "rejected", "in_progress", "missing")}
    for result in results:
        counts[result["state"]] += 1

    if counts["in_progress"] or counts["missing"]:
        status = "IN_PROGRESS"
    elif counts["deferred"] or counts["rejected"]:
        status = "CLOSED_WITH_EXCEPTIONS"
    else:
        status = "COMPLETE"

    return {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "summary": {"total": len(results), **counts},
        "requirements": results,
        "errors": [],
        "warnings": bundle.warnings,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [f"COMPLETION STATUS: {report['status']}"]
    if report["status"] == "INVALID":
        for error in report["errors"]:
            lines.append(f"ERROR: {error}")
        return "\n".join(lines)

    summary = report["summary"]
    lines.append(
        " ".join(
            f"{key}={summary[key]}"
            for key in ("total", "completed", "deferred", "rejected", "in_progress", "missing")
        )
    )
    for item in report["requirements"]:
        details = "; ".join(item["reasons"])
        lines.append(f"- {item['req_id']} [{item['state']}]: {details}")
    for warning in report["warnings"]:
        lines.append(f"WARN: {warning}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", default=".ai-work", help="Path to the project-local work directory")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    parser.add_argument("--write-report", action="store_true", help="Write completion-report.json in the work directory")
    args = parser.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    report = build_report(workdir)
    if args.write_report:
        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "completion-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))

    if report["status"] == "COMPLETE":
        return 0
    if report["status"] == "CLOSED_WITH_EXCEPTIONS":
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
