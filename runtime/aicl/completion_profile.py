from __future__ import annotations

from typing import Any, Dict, List, Optional

from .record_io import utc_now

EVIDENCE_CATEGORIES = [
    "automated_test",
    "manual_test",
    "review",
    "db_probe",
    "real_host_verify",
    "deploy_probe",
    "git_state",
    "ci",
    "static_analysis",
    "security_scan",
    "runtime_observation",
    "document",
    "human_approval",
    "assumption_validation",
    "other",
]


def new_record(
    *,
    record_id: str,
    contract_id: str,
    risk_id: str,
    title: str,
    objective: str,
    requirement: str,
    acceptance: str,
    source_ref: str,
    repository: str,
    base_ref: str,
    scope: str,
    criticality: str,
    evidence_category: Optional[str],
) -> Dict[str, Any]:
    timestamp = utc_now()
    categories: List[str] = (
        [] if evidence_category in {None, "none"} else [str(evidence_category)]
    )
    return {
        "schema_version": "0.2.0",
        "record_id": record_id,
        "title": title,
        "created_at": timestamp,
        "updated_at": timestamp,
        "lifecycle_phase": "CONTRACTED",
        "repository_context": {
            "repository": repository,
            "base_ref": base_ref,
        },
        "acceptance_contract": {
            "contract_id": contract_id,
            "version": 1,
            "status": "DRAFT",
            "profile": "TASK",
            "created_at": timestamp,
            "updated_at": timestamp,
            "objective": {"statement": objective},
            "scope": {
                "allowed": [
                    {
                        "ref": scope,
                        "description": "Initial completion-discipline task scope",
                    }
                ],
                "forbidden": [],
                "out_of_scope": [],
            },
            "requirements": [
                {
                    "req_id": "REQ-001",
                    "statement": requirement,
                    "source_refs": [source_ref],
                    "kind": "FUNCTIONAL",
                    "priority": criticality,
                    "disposition": "ACTIVE",
                    "disclosed_to_user": False,
                    "acc_refs": ["ACC-001"],
                    "inv_refs": [],
                }
            ],
            "acceptance_criteria": [
                {
                    "acc_id": "ACC-001",
                    "statement": acceptance,
                    "req_refs": ["REQ-001"],
                    "criticality": criticality,
                    "verification": {
                        "required_categories": categories,
                        "pass_condition": (
                            "The linked task is fully accounted for."
                            if not categories
                            else "The required evidence category has an effective PASS entry."
                        ),
                    },
                }
            ],
            "invariants": [],
            "assumptions": [],
            "open_decisions": [],
            "change_control": {
                "triggers": [
                    "ACCEPTANCE_CRITERIA_CHANGE",
                    "INVARIANT_CHANGE",
                    "FORBIDDEN_SCOPE_TOUCHED",
                    "VERIFICATION_BECOMES_UNAVAILABLE",
                ],
                "reapproval_required": True,
            },
        },
        "risk_profile": {
            "assessment_id": risk_id,
            "status": "DRAFT",
            "overall_risk": {
                "level": "UNKNOWN",
                "rationale": (
                    "Completion Discipline tracks requirement closure but does not "
                    "classify engineering risk."
                ),
                "method": "JUDGMENT",
            },
            "dimensions": {},
            "risk_items": [],
            "understanding_requirements": [],
        },
        "execution_plan": {
            "tasks": [
                {
                    "task_id": "TASK-001",
                    "title": "Implement and verify REQ-001",
                    "subject_refs": ["REQ-001", "ACC-001"],
                    "status": "PENDING",
                    "reason": "",
                    "next_action": "",
                    "disclosed_to_user": False,
                }
            ]
        },
        "evidence_ledger": [],
        "adapter_results": [],
        "policy_decisions": [],
        "open_actions": [],
        "current_decision_refs": {},
        "derived_views": {},
        "legacy_sources": [],
    }


def append_evidence(
    record: Dict[str, Any],
    entry: Dict[str, Any],
) -> None:
    evidence_id = entry.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id:
        raise ValueError("evidence entry requires evidence_id")
    ledger = record.setdefault("evidence_ledger", [])
    if evidence_id in {
        item.get("evidence_id")
        for item in ledger
    }:
        raise ValueError(f"duplicate evidence_id: {evidence_id}")
    supersedes = entry.get("supersedes")
    if not isinstance(supersedes, list):
        raise ValueError("evidence entry supersedes must be an array")
    known = {
        item.get("evidence_id")
        for item in ledger
    }
    missing = [
        ref for ref in supersedes
        if ref not in known
    ]
    if missing:
        raise ValueError(
            "supersedes references unknown evidence: " + ", ".join(missing)
        )
    ledger.append(entry)
    record["updated_at"] = utc_now()
