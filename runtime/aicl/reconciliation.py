from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

from .record_io import utc_now

OPEN_TASK_STATUSES = {"PENDING", "IN_PROGRESS"}
EXCEPTION_DISPOSITIONS = {
    "DEFERRED": "deferred",
    "REJECTED": "rejected",
    "OUT_OF_SCOPE": "out_of_scope",
}


def _parse_datetime(value: str) -> Optional[datetime]:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def effective_evidence(
    record: Dict[str, Any],
    evaluated_at: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    entries = record.get("evidence_ledger", [])
    superseded: Set[str] = {
        ref
        for entry in entries
        for ref in entry.get("supersedes", [])
        if isinstance(ref, str)
    }
    repository_context = record.get("repository_context", {})
    current_repository = repository_context.get("repository")
    current_commit = repository_context.get("head_commit")
    now = evaluated_at or datetime.now(timezone.utc)

    result: List[Dict[str, Any]] = []
    for entry in entries:
        evidence_id = entry.get("evidence_id")
        if evidence_id in superseded or entry.get("status") == "REVOKED":
            continue
        applicability = entry.get("applicability", {})
        evidence_repository = applicability.get("repository")
        evidence_commit = applicability.get("commit")
        if (
            current_repository
            and evidence_repository
            and evidence_repository != current_repository
        ):
            continue
        if current_commit and evidence_commit and evidence_commit != current_commit:
            continue
        valid_until = applicability.get("valid_until")
        if isinstance(valid_until, str):
            expiry = _parse_datetime(valid_until)
            if expiry is None or expiry < now:
                continue
        result.append(entry)
    return result


def _refs_for_requirement(requirement: Dict[str, Any]) -> Set[str]:
    return {
        requirement.get("req_id"),
        *requirement.get("acc_refs", []),
        *requirement.get("inv_refs", []),
    } - {None}


def _linked_by_refs(
    rows: Iterable[Dict[str, Any]],
    refs: Set[str],
) -> List[Dict[str, Any]]:
    return [
        row
        for row in rows
        if refs.intersection(set(row.get("subject_refs", [])))
    ]


def structural_reconciliation(
    record: Dict[str, Any],
    semantic_errors: Optional[List[str]] = None,
    require_task_mapping: bool = True,
) -> Dict[str, Any]:
    errors = list(semantic_errors or [])
    requirements = record.get("acceptance_contract", {}).get("requirements", [])
    tasks = record.get("execution_plan", {}).get("tasks", [])
    unmapped: List[str] = []

    for requirement in requirements:
        if requirement.get("disposition") != "ACTIVE":
            continue
        refs = _refs_for_requirement(requirement)
        linked_tasks = _linked_by_refs(tasks, refs)
        if require_task_mapping and not linked_tasks:
            req_id = str(requirement.get("req_id"))
            unmapped.append(req_id)

    if unmapped:
        errors.append(
            "active requirements without task mapping: " + ", ".join(sorted(unmapped))
        )

    return {
        "version": "0.2.0",
        "profile": "completion-discipline",
        "status": "PASS" if not errors else "FAIL",
        "counts": {
            "requirements": len(requirements),
            "tasks": len(tasks),
            "evidence": len(record.get("evidence_ledger", [])),
            "actions": len(record.get("open_actions", [])),
        },
        "unmapped_requirements": sorted(unmapped),
        "errors": errors,
        "warnings": [],
    }


def _required_categories(
    requirement: Dict[str, Any],
    criteria: Dict[str, Dict[str, Any]],
    invariants: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    for ref in requirement.get("acc_refs", []):
        subject = criteria.get(ref)
        if subject is None:
            result.append({"subject_ref": ref, "category": "definition"})
            continue
        for category in subject.get("verification", {}).get(
            "required_categories", []
        ):
            result.append({"subject_ref": ref, "category": category})
    for ref in requirement.get("inv_refs", []):
        subject = invariants.get(ref)
        if subject is None:
            result.append({"subject_ref": ref, "category": "definition"})
            continue
        for category in subject.get("verification", {}).get(
            "required_categories", []
        ):
            result.append({"subject_ref": ref, "category": category})
    return result


def completion_reconciliation(
    record: Dict[str, Any],
    semantic_errors: Optional[List[str]] = None,
    require_task_mapping: bool = True,
) -> Dict[str, Any]:
    errors = list(semantic_errors or [])
    contract = record.get("acceptance_contract", {})
    requirements = contract.get("requirements", [])
    if errors:
        return {
            "version": "0.2.0",
            "profile": "completion-discipline",
            "status": "INVALID",
            "evaluated_at": utc_now(),
            "summary": {"total": len(requirements)},
            "requirements": [],
            "errors": errors,
            "warnings": [],
        }

    criteria = {
        item["acc_id"]: item
        for item in contract.get("acceptance_criteria", [])
    }
    invariants = {
        item["inv_id"]: item
        for item in contract.get("invariants", [])
    }
    tasks = record.get("execution_plan", {}).get("tasks", [])
    actions = record.get("open_actions", [])
    evidence = effective_evidence(record)
    evidence_ids = {
        item.get("evidence_id")
        for item in evidence
        if isinstance(item.get("evidence_id"), str)
    }

    rows: List[Dict[str, Any]] = []
    counts = {
        key: 0
        for key in (
            "completed",
            "deferred",
            "rejected",
            "out_of_scope",
            "in_progress",
            "missing",
        )
    }

    for requirement in requirements:
        req_id = str(requirement.get("req_id"))
        disposition = requirement.get("disposition")
        refs = _refs_for_requirement(requirement)
        linked_tasks = _linked_by_refs(tasks, refs)
        linked_actions = _linked_by_refs(actions, refs)
        matched_evidence: List[str] = []
        missing_evidence: List[Dict[str, Any]] = []
        reasons: List[str] = []

        if disposition in EXCEPTION_DISPOSITIONS:
            state = EXCEPTION_DISPOSITIONS[disposition]
            reasons.append(
                str(
                    requirement.get("disposition_reason")
                    or f"requirement disposition is {disposition}"
                )
            )
        else:
            if require_task_mapping and not linked_tasks:
                state = "missing"
                reasons.append("no linked task or explicit requirement disposition")
            else:
                state = "completed"
                if any(
                    item.get("status") in OPEN_TASK_STATUSES
                    for item in linked_tasks
                ):
                    state = "in_progress"
                    reasons.append("linked task is pending or in progress")
                elif any(
                    item.get("status") != "COMPLETED"
                    for item in linked_tasks
                ):
                    state = "in_progress"
                    reasons.append(
                        "linked task exception is not reflected in requirement disposition"
                    )

                open_actions = [
                    item
                    for item in linked_actions
                    if item.get("status") == "OPEN"
                ]
                if open_actions:
                    state = "in_progress"
                    reasons.append("open action remains for the requirement")

                for need in _required_categories(
                    requirement, criteria, invariants
                ):
                    subject_ref = need["subject_ref"]
                    category = need["category"]
                    matching = [
                        item
                        for item in evidence
                        if item.get("category") == category
                        and subject_ref in item.get("subject_refs", [])
                    ]
                    failures = [
                        item for item in matching if item.get("status") == "FAIL"
                    ]
                    passing = [
                        item for item in matching if item.get("status") == "PASS"
                    ]
                    if failures:
                        state = "in_progress"
                        missing_evidence.append(
                            {
                                **need,
                                "reason": "effective_failure",
                                "evidence_ids": [
                                    str(item["evidence_id"]) for item in failures
                                ],
                            }
                        )
                    elif passing:
                        matched_evidence.extend(
                            str(item["evidence_id"]) for item in passing
                        )
                    else:
                        state = "in_progress"
                        missing_evidence.append(
                            {**need, "reason": "missing_pass"}
                        )

                if missing_evidence:
                    missing_names = ", ".join(
                        f"{item['subject_ref']}:{item['category']}:{item['reason']}"
                        for item in missing_evidence
                    )
                    reasons.append(
                        "unsatisfied effective evidence: " + missing_names
                    )

                if state == "completed":
                    reasons.append(
                        "linked tasks are complete and declared evidence requirements are satisfied"
                    )

        counts[state] += 1
        rows.append(
            {
                "req_id": req_id,
                "statement": requirement.get("statement", ""),
                "state": state,
                "reasons": reasons,
                "task_ids": [
                    item.get("task_id") for item in linked_tasks
                ],
                "evidence_ids": sorted(
                    set(matched_evidence).intersection(evidence_ids)
                ),
                "action_ids": [
                    item.get("action_id") for item in linked_actions
                ],
                "missing_evidence": missing_evidence,
            }
        )

    if counts["in_progress"] or counts["missing"]:
        status = "IN_PROGRESS"
    elif counts["deferred"] or counts["rejected"] or counts["out_of_scope"]:
        status = "CLOSED_WITH_EXCEPTIONS"
    else:
        status = "COMPLETE"

    return {
        "version": "0.2.0",
        "profile": "completion-discipline",
        "status": status,
        "evaluated_at": utc_now(),
        "summary": {"total": len(rows), **counts},
        "requirements": rows,
        "effective_evidence_ids": sorted(evidence_ids),
        "errors": [],
        "warnings": [],
    }
