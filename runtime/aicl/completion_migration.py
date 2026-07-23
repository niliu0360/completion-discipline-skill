from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

from .legacy_completion import Bundle, OPEN, linked, load_bundle, snapshot

NEED_TO_CATEGORY = {
    "test": "automated_test",
    "review": "review",
    "db-probe": "db_probe",
    "real-host-verify": "real_host_verify",
    "deploy-probe": "deploy_probe",
}
TASK_STATUS_MAP = {
    "pending": "PENDING",
    "in_progress": "IN_PROGRESS",
    "completed": "COMPLETED",
    "deferred": "DEFERRED",
    "rejected": "REJECTED",
}


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def acc_id(req_id: str) -> str:
    return "ACC-" + req_id.split("-", 1)[1]


def _reason(tasks: list[dict[str, Any]], followups: list[dict[str, Any]], fallback: str) -> tuple[str, str]:
    for item in tasks:
        if item.get("status") in {"deferred", "rejected"}:
            return str(item.get("reason", fallback)), str(item.get("next_action", ""))
    for item in followups:
        if item.get("status") in OPEN and item.get("category") == "deferred":
            return str(item.get("reason", fallback)), str(item.get("next_action", ""))
    return fallback, ""


def _contract(bundle: Bundle, legacy: dict[str, Any], args: Any, timestamp: datetime) -> dict[str, Any]:
    state_by_req = {item["req_id"]: item["state"] for item in legacy["requirements"]}
    requirements: list[dict[str, Any]] = []
    criteria: list[dict[str, Any]] = []
    for req in bundle.requirements.values():
        state = state_by_req[req.req_id]
        tasks = linked(bundle.tasks, req.req_id)
        followups = linked(bundle.followups, req.req_id)
        disposition, reason, disclosed = "ACTIVE", "", False
        if state == "deferred":
            disposition = "DEFERRED"
            reason, _ = _reason(tasks, followups, "Migrated deferred requirement")
            disclosed = True
        elif state == "rejected":
            disposition = "REJECTED"
            reason, _ = _reason(tasks, followups, "Migrated rejected requirement")
            disclosed = True
        row = {
            "req_id": req.req_id,
            "statement": req.statement,
            "source_refs": ["completion-discipline:session-goal.md"],
            "kind": "DOCUMENTATION" if req.needs == ("(none)",) else "FUNCTIONAL",
            "priority": args.default_criticality,
            "disposition": disposition,
            "disclosed_to_user": disclosed,
            "acc_refs": [acc_id(req.req_id)],
            "inv_refs": [],
        }
        if reason:
            row["disposition_reason"] = reason
        requirements.append(row)
        categories = [] if req.needs == ("(none)",) else [NEED_TO_CATEGORY[item] for item in req.needs]
        criteria.append({
            "acc_id": acc_id(req.req_id),
            "statement": req.statement,
            "req_refs": [req.req_id],
            "criticality": args.default_criticality,
            "verification": {
                "required_categories": categories,
                "pass_condition": (
                    "Linked tasks are fully accounted for; no execution evidence is required by the legacy contract."
                    if not categories else
                    "The latest effective migrated evidence for every required category is PASS."
                ),
            },
        })
    return {
        "contract_id": args.contract_id,
        "version": 1,
        "status": "DRAFT",
        "profile": "TASK",
        "created_at": iso(timestamp),
        "updated_at": iso(timestamp),
        "objective": {"statement": args.objective},
        "scope": {
            "allowed": [{"ref": args.scope, "description": "Migrated completion-discipline task scope"}],
            "forbidden": [],
            "out_of_scope": [],
        },
        "requirements": requirements,
        "acceptance_criteria": criteria,
        "invariants": [],
        "assumptions": [],
        "open_decisions": [],
        "change_control": {
            "triggers": ["ACCEPTANCE_CRITERIA_CHANGE", "INVARIANT_CHANGE", "FORBIDDEN_SCOPE_TOUCHED"],
            "reapproval_required": True,
        },
    }


def _tasks(bundle: Bundle) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in bundle.tasks:
        subjects: list[str] = []
        for req_id in item.get("req_ids", []):
            subjects.extend([req_id, acc_id(req_id)])
        result.append({
            "task_id": item["task_id"],
            "title": item.get("title", item["task_id"]),
            "subject_refs": list(dict.fromkeys(subjects)),
            "status": TASK_STATUS_MAP[item["status"]],
            "reason": str(item.get("reason", "")),
            "next_action": str(item.get("next_action", "")),
            "disclosed_to_user": bool(item.get("disclosed_to_user", False)),
        })
    return result


def _evidence(bundle: Bundle, args: Any, timestamp: datetime) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    latest: dict[tuple[str, str], str] = {}
    for index, item in enumerate(bundle.evidence):
        category = NEED_TO_CATEGORY[item["type"]]
        supersedes: list[str] = []
        for req_id in item["req_ids"]:
            previous = latest.get((req_id, item["type"]))
            if previous and previous not in supersedes:
                supersedes.append(previous)
        source: dict[str, Any] = {}
        if item.get("command"):
            source["command"] = str(item["command"])
        if item.get("reference"):
            source["observed_output"] = str(item["reference"])
        if item.get("artifact"):
            source["artifact_refs"] = [str(item["artifact"])]
        subjects: list[str] = []
        for req_id in item["req_ids"]:
            subjects.extend([req_id, acc_id(req_id)])
        result.append({
            "evidence_id": item["evidence_id"],
            "evidence_key": "+".join(sorted(item["req_ids"])) + ":" + category,
            "recorded_at": iso(timestamp + timedelta(microseconds=index)),
            "producer": {"type": "SYSTEM", "name": "completion-discipline-migrator", "version": "0.2.0-dev"},
            "subject_refs": list(dict.fromkeys(subjects)),
            "category": category,
            "subtype": "legacy-import",
            "status": "PASS" if item["status"] == "pass" else "FAIL",
            "summary": str(item["summary"]),
            "supports_claims": [str(item["summary"])] if item["status"] == "pass" else [],
            "limitations": [
                "Migrated from completion-discipline 0.1.x.",
                "The legacy evidence did not require commit, environment, or execution timestamp fields.",
            ],
            "applicability": {"repository": args.repository, "environment": "legacy-import"},
            "source": source,
            "supersedes": supersedes,
        })
        for req_id in item["req_ids"]:
            latest[(req_id, item["type"])] = item["evidence_id"]
    return result


def _actions(bundle: Bundle, legacy: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    states = {item["req_id"]: item["state"] for item in legacy["requirements"]}
    for item in bundle.followups:
        if item.get("status") not in OPEN:
            continue
        action_id = "ACT-" + str(item["followup_id"]).replace("FOLLOWUP-", "FU-")
        if action_id in seen:
            continue
        seen.add(action_id)
        subjects: list[str] = []
        for req_id in item["req_ids"]:
            subjects.extend([req_id, acc_id(req_id)])
        result.append({
            "action_id": action_id,
            "subject_refs": list(dict.fromkeys(subjects)),
            "statement": str(item.get("next_action") or item.get("reason") or item.get("summary") or "Resolve migrated follow-up"),
            "status": "OPEN",
            "owner": str(item.get("owner") or "unassigned"),
            "required_evidence": ["human_approval"] if item.get("category") == "decision" else [],
        })
    for req in bundle.requirements.values():
        state = states[req.req_id]
        if state in {"in_progress", "missing"}:
            action_id = f"ACT-migration-{req.req_id.lower()}"
            if action_id not in seen:
                seen.add(action_id)
                result.append({
                    "action_id": action_id,
                    "subject_refs": [req.req_id, acc_id(req.req_id)],
                    "statement": "Complete the linked task/evidence accounting for the migrated requirement.",
                    "status": "OPEN",
                    "owner": "implementation owner",
                    "required_evidence": [NEED_TO_CATEGORY[item] for item in req.needs if item != "(none)"],
                })
        elif state == "deferred":
            reason, next_action = _reason(linked(bundle.tasks, req.req_id), linked(bundle.followups, req.req_id), "Migrated deferred requirement")
            result.append({
                "action_id": f"ACT-deferred-{req.req_id.lower()}",
                "subject_refs": [req.req_id, acc_id(req.req_id)],
                "statement": next_action or reason,
                "status": "DEFERRED",
                "owner": "implementation owner",
                "required_evidence": [NEED_TO_CATEGORY[item] for item in req.needs if item != "(none)"],
            })
    return result


def migrate(args: Any) -> Tuple[Optional[dict[str, Any]], dict[str, Any]]:
    workdir = Path(args.workdir).expanduser().resolve()
    bundle = load_bundle(workdir)
    if bundle.errors:
        return None, {"status": "INVALID", "errors": bundle.errors}
    legacy = snapshot(bundle)
    timestamp = datetime.now(timezone.utc)
    record = {
        "schema_version": "0.2.0",
        "record_id": args.record_id,
        "title": args.title,
        "created_at": iso(timestamp),
        "updated_at": iso(timestamp),
        "lifecycle_phase": "VERIFYING",
        "repository_context": {"repository": args.repository, "base_ref": args.base_ref},
        "acceptance_contract": _contract(bundle, legacy, args, timestamp),
        "risk_profile": {
            "assessment_id": args.risk_id,
            "status": "DRAFT",
            "overall_risk": {
                "level": "UNKNOWN",
                "rationale": "Risk was not classified by completion-discipline 0.1.x and must be assessed separately.",
                "method": "JUDGMENT",
            },
            "dimensions": {},
            "risk_items": [],
            "understanding_requirements": [],
        },
        "execution_plan": {"tasks": _tasks(bundle)},
        "evidence_ledger": _evidence(bundle, args, timestamp),
        "adapter_results": [],
        "policy_decisions": [],
        "open_actions": _actions(bundle, legacy),
        "current_decision_refs": {},
        "derived_views": {
            "completion_snapshot": {
                **legacy,
                "source": "completion-discipline-0.1.x-equivalent",
                "evaluated_at": iso(timestamp),
            },
            "migration": {
                "status": "MIGRATED",
                "warnings": [
                    "Legacy evidence has no commit/environment timestamp guarantees.",
                    "Deferred items are marked disclosed to preserve the legacy CLOSED_WITH_EXCEPTIONS classification; review this assumption.",
                ],
            },
        },
        "legacy_sources": [{
            "system": "completion-discipline",
            "version": "0.1.x",
            "source_ref": str(workdir),
            "migration_notes": "REQ/TASK IDs preserved; ACC generated; evidence supersession made explicit; completion-report.json ignored.",
        }],
    }
    return record, {"status": legacy["status"], "errors": []}


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
