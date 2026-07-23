from __future__ import annotations

from typing import Any, Dict, List, Set


def _add_ids(
    items: List[Dict[str, Any]],
    key: str,
    label: str,
    errors: List[str],
) -> Set[str]:
    seen: Set[str] = set()
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{label} item is missing {key}")
            continue
        if value in seen:
            errors.append(f"duplicate {label} id: {value}")
        seen.add(value)
    return seen


def _detect_cycle(graph: Dict[str, List[str]]) -> List[str]:
    visiting: Set[str] = set()
    visited: Set[str] = set()
    path: List[str] = []

    def visit(node: str) -> List[str]:
        if node in visiting:
            start = path.index(node)
            return path[start:] + [node]
        if node in visited:
            return []
        visiting.add(node)
        path.append(node)
        for target in graph.get(node, []):
            cycle = visit(target)
            if cycle:
                return cycle
        path.pop()
        visiting.remove(node)
        visited.add(node)
        return []

    for node in graph:
        cycle = visit(node)
        if cycle:
            return cycle
    return []


def validate(record: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if record.get("schema_version") != "0.2.0":
        errors.append("schema_version must be 0.2.0")

    contract = record.get("acceptance_contract")
    risk_profile = record.get("risk_profile")
    if not isinstance(contract, dict):
        return errors + ["acceptance_contract must be an object"]
    if not isinstance(risk_profile, dict):
        return errors + ["risk_profile must be an object"]

    requirements = contract.get("requirements", [])
    criteria = contract.get("acceptance_criteria", [])
    invariants = contract.get("invariants", [])
    assumptions = contract.get("assumptions", [])
    questions = contract.get("open_decisions", [])
    risks = risk_profile.get("risk_items", [])
    understandings = risk_profile.get("understanding_requirements", [])
    evidence = record.get("evidence_ledger", [])
    decisions = record.get("policy_decisions", [])
    adapters = record.get("adapter_results", [])
    tasks = record.get("execution_plan", {}).get("tasks", [])
    actions = record.get("open_actions", [])

    collections = [
        requirements, criteria, invariants, assumptions, questions, risks,
        understandings, evidence, decisions, adapters, tasks, actions,
    ]
    if not all(isinstance(items, list) for items in collections):
        return errors + ["record entity collections must be arrays"]

    req_ids = _add_ids(requirements, "req_id", "REQ", errors)
    acc_ids = _add_ids(criteria, "acc_id", "ACC", errors)
    inv_ids = _add_ids(invariants, "inv_id", "INV", errors)
    asm_ids = _add_ids(assumptions, "assumption_id", "ASM", errors)
    question_ids = _add_ids(questions, "question_id", "Q", errors)
    risk_ids = _add_ids(risks, "risk_id", "RISK", errors)
    under_ids = _add_ids(understandings, "understanding_id", "UNDER", errors)
    ev_ids = _add_ids(evidence, "evidence_id", "EV", errors)
    dec_ids = _add_ids(decisions, "decision_id", "DEC", errors)
    adp_ids = _add_ids(adapters, "adapter_result_id", "ADP", errors)
    task_ids = _add_ids(tasks, "task_id", "TASK", errors)
    action_ids = _add_ids(actions, "action_id", "ACT", errors)

    for req in requirements:
        req_id = req.get("req_id", "<unknown>")
        for ref in req.get("acc_refs", []):
            if ref not in acc_ids:
                errors.append(f"{req_id} references missing ACC: {ref}")
        for ref in req.get("inv_refs", []):
            if ref not in inv_ids:
                errors.append(f"{req_id} references missing INV: {ref}")
        if req.get("disposition") == "ACTIVE" and not req.get("acc_refs") and not req.get("inv_refs"):
            errors.append(f"active requirement has no ACC or INV mapping: {req_id}")
        if req.get("disposition") in {"DEFERRED", "REJECTED", "OUT_OF_SCOPE"}:
            if not req.get("disposition_reason"):
                errors.append(f"{req_id} disposition requires disposition_reason")
            if req.get("disclosed_to_user") is not True:
                errors.append(f"{req_id} disposition must be disclosed_to_user=true")

    for acc in criteria:
        acc_id = acc.get("acc_id", "<unknown>")
        for ref in acc.get("req_refs", []):
            if ref not in req_ids:
                errors.append(f"{acc_id} references missing REQ: {ref}")

    for inv in invariants:
        inv_id = inv.get("inv_id", "<unknown>")
        for ref in inv.get("req_refs", []):
            if ref not in req_ids:
                errors.append(f"{inv_id} references missing REQ: {ref}")

    contract_ids = (
        {contract.get("contract_id")}
        if isinstance(contract.get("contract_id"), str)
        else set()
    )
    assessment_ids = (
        {risk_profile.get("assessment_id")}
        if isinstance(risk_profile.get("assessment_id"), str)
        else set()
    )
    known_refs = (
        req_ids | acc_ids | inv_ids | asm_ids | question_ids | risk_ids |
        under_ids | ev_ids | dec_ids | adp_ids | task_ids | action_ids |
        contract_ids | assessment_ids
    )
    allowed_prefixes = ("PATH:", "MODULE:", "SERVICE:", "API:", "DB:", "ENV:")

    def validate_refs(owner: str, refs: Any) -> None:
        if not isinstance(refs, list) or not refs:
            errors.append(f"{owner} subject_refs must be a non-empty array")
            return
        for ref in refs:
            if (
                not isinstance(ref, str)
                or (ref not in known_refs and not ref.startswith(allowed_prefixes))
            ):
                errors.append(f"{owner} references unknown subject: {ref}")

    for task in tasks:
        validate_refs(task.get("task_id", "<task>"), task.get("subject_refs"))
    for action in actions:
        validate_refs(action.get("action_id", "<action>"), action.get("subject_refs"))
    for risk in risks:
        validate_refs(risk.get("risk_id", "<risk>"), risk.get("subject_refs"))
        for ref in risk.get("evidence_refs", []):
            if ref not in ev_ids:
                errors.append(f"{risk.get('risk_id')} references missing EV: {ref}")
    for item in understandings:
        owner = item.get("understanding_id", "<understanding>")
        validate_refs(owner, item.get("subject_refs"))
        for ref in item.get("triggered_by_risk_refs", []):
            if ref not in risk_ids:
                errors.append(f"{owner} references missing RISK: {ref}")

    supersession_graph: Dict[str, List[str]] = {}
    for ev in evidence:
        ev_id = ev.get("evidence_id", "<unknown>")
        validate_refs(ev_id, ev.get("subject_refs"))
        targets = ev.get("supersedes", [])
        if not isinstance(targets, list):
            errors.append(f"{ev_id} supersedes must be an array")
            targets = []
        supersession_graph[ev_id] = targets
        for target in targets:
            if target not in ev_ids:
                errors.append(f"{ev_id} supersedes missing EV: {target}")
            if target == ev_id:
                errors.append(f"{ev_id} cannot supersede itself")
        if ev.get("status") == "REVOKED" and not targets:
            errors.append(f"{ev_id} is REVOKED but supersedes no evidence")

    cycle = _detect_cycle(supersession_graph)
    if cycle:
        errors.append("evidence supersession cycle: " + " -> ".join(cycle))

    for dec in decisions:
        dec_id = dec.get("decision_id", "<unknown>")
        based_on = dec.get("based_on", {})
        if based_on.get("contract_id") != contract.get("contract_id"):
            errors.append(f"{dec_id} uses a different contract_id")
        if based_on.get("contract_version") != contract.get("version"):
            errors.append(f"{dec_id} does not snapshot the current contract version")
        if based_on.get("risk_assessment_id") != risk_profile.get("assessment_id"):
            errors.append(f"{dec_id} uses a different risk_assessment_id")
        for ref in based_on.get("evidence_refs", []):
            if ref not in ev_ids:
                errors.append(f"{dec_id} references missing EV: {ref}")
        for ref in based_on.get("adapter_result_refs", []):
            if ref not in adp_ids:
                errors.append(f"{dec_id} references missing ADP: {ref}")
        for ref in dec.get("supersedes", []):
            if ref not in dec_ids:
                errors.append(f"{dec_id} supersedes missing DEC: {ref}")
        outcome = dec.get("outcome")
        if outcome == "ALLOW_WITH_CONDITIONS" and not dec.get("conditions"):
            errors.append(f"{dec_id} ALLOW_WITH_CONDITIONS requires conditions")
        if outcome == "REQUIRE_HUMAN_APPROVAL":
            approval = dec.get("human_approval", {})
            if approval.get("required") is not True or not approval.get("roles"):
                errors.append(f"{dec_id} REQUIRE_HUMAN_APPROVAL requires roles")
        if outcome == "BLOCK" and not dec.get("blocking_items"):
            errors.append(f"{dec_id} BLOCK requires blocking_items")

    for action_name, ref in record.get("current_decision_refs", {}).items():
        if ref not in dec_ids:
            errors.append(
                f"current decision for {action_name} references missing DEC: {ref}"
            )

    return errors
