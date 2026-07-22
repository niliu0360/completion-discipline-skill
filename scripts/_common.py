#!/usr/bin/env python3
"""Shared parsing and validation helpers for completion-discipline."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

VERSION = "0.1.0"
REQ_PATTERN = re.compile(
    r"^\s*-\s*\[(REQ-\d{3,})\]\s+(.+?)\s+—\s+needs:\s*(.+?)\s*$"
)
VALID_NEEDS = {
    "test",
    "review",
    "db-probe",
    "real-host-verify",
    "deploy-probe",
    "(none)",
}
VALID_TASK_STATUSES = {"pending", "in_progress", "completed", "deferred", "rejected"}
VALID_EVIDENCE_TYPES = VALID_NEEDS - {"(none)"}
VALID_EVIDENCE_STATUSES = {"pass", "fail"}
VALID_FOLLOWUP_CATEGORIES = {"deferred", "verification", "decision", "other"}
VALID_FOLLOWUP_STATUSES = {"pending", "in_progress", "completed", "dismissed"}


@dataclass(frozen=True)
class Requirement:
    req_id: str
    description: str
    needs: tuple[str, ...]


@dataclass
class DataBundle:
    requirements: dict[str, Requirement]
    tasks: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    followups: list[dict[str, Any]]
    errors: list[str]
    warnings: list[str]


def _read_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}")
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
    return None


def _read_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return records
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
        return records

    for number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSONL in {path}:{number}: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"invalid record in {path}:{number}: expected JSON object")
            continue
        value["_line"] = number
        records.append(value)
    return records


def _parse_requirements(path: Path, errors: list[str], warnings: list[str]) -> dict[str, Requirement]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return {}
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
        return {}

    requirements: dict[str, Requirement] = {}
    saw_requirement_section = False
    in_requirement_section = False

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped == "## Requirements":
            saw_requirement_section = True
            in_requirement_section = True
            continue
        if in_requirement_section and stripped.startswith("## "):
            in_requirement_section = False
        if not in_requirement_section or not stripped.startswith("-"):
            continue

        match = REQ_PATTERN.match(line)
        if not match:
            errors.append(
                f"invalid requirement format in {path}:{number}; expected '- [REQ-001] description — needs: test'"
            )
            continue
        req_id, description, raw_needs = match.groups()
        if req_id in requirements:
            errors.append(f"duplicate requirement ID {req_id} in {path}:{number}")
            continue

        needs = tuple(part.strip() for part in raw_needs.split(",") if part.strip())
        if not needs:
            errors.append(f"requirement {req_id} has no needs value in {path}:{number}")
            continue
        unknown = [need for need in needs if need not in VALID_NEEDS]
        if unknown:
            errors.append(f"requirement {req_id} uses unknown needs: {', '.join(unknown)}")
        if "(none)" in needs and len(needs) > 1:
            errors.append(f"requirement {req_id} cannot combine (none) with other needs")
        requirements[req_id] = Requirement(req_id, description.strip(), needs)

    if not saw_requirement_section:
        errors.append(f"missing '## Requirements' section in {path}")
    elif not requirements:
        errors.append(f"no requirements found in {path}")
    return requirements


def _as_req_ids(value: Any, context: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{context}: req_ids must be an array of strings")
        return []
    if not value:
        errors.append(f"{context}: req_ids must not be empty")
    return value


def _validate_tasks(data: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        errors.append("task-queue.json root must be an object")
        return []
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        errors.append("task-queue.json must contain a tasks array")
        return []

    seen: set[str] = set()
    valid: list[dict[str, Any]] = []
    for index, task in enumerate(tasks, start=1):
        context = f"task #{index}"
        if not isinstance(task, dict):
            errors.append(f"{context}: expected object")
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            errors.append(f"{context}: task_id is required")
            continue
        if task_id in seen:
            errors.append(f"duplicate task_id: {task_id}")
        seen.add(task_id)
        if not isinstance(task.get("title"), str) or not task.get("title", "").strip():
            errors.append(f"{task_id}: title is required")
        status = task.get("status")
        if status not in VALID_TASK_STATUSES:
            errors.append(f"{task_id}: invalid status {status!r}")
        task["req_ids"] = _as_req_ids(task.get("req_ids"), task_id, errors)
        if status in {"deferred", "rejected"} and not str(task.get("reason", "")).strip():
            errors.append(f"{task_id}: {status} task requires reason")
        if status == "deferred" and not str(task.get("next_action", "")).strip():
            errors.append(f"{task_id}: deferred task requires next_action")
        if status == "rejected" and task.get("disclosed_to_user") is not True:
            errors.append(f"{task_id}: rejected task requires disclosed_to_user=true")
        valid.append(task)
    return valid


def _validate_evidence(records: list[dict[str, Any]], errors: list[str]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for record in records:
        line = record.get("_line")
        context = f"evidence.jsonl:{line}"
        evidence_id = record.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"{context}: evidence_id is required")
        elif evidence_id in seen:
            errors.append(f"duplicate evidence_id: {evidence_id}")
        else:
            seen.add(evidence_id)
        record["req_ids"] = _as_req_ids(record.get("req_ids"), context, errors)
        if record.get("type") not in VALID_EVIDENCE_TYPES:
            errors.append(f"{context}: invalid evidence type {record.get('type')!r}")
        if record.get("status") not in VALID_EVIDENCE_STATUSES:
            errors.append(f"{context}: invalid evidence status {record.get('status')!r}")
        if not str(record.get("summary", "")).strip():
            errors.append(f"{context}: summary is required")
        if not any(str(record.get(field, "")).strip() for field in ("command", "reference", "artifact")):
            errors.append(f"{context}: one of command, reference, or artifact is required")
    return records


def _validate_followups(records: list[dict[str, Any]], errors: list[str]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for record in records:
        line = record.get("_line")
        context = f"followups.jsonl:{line}"
        followup_id = record.get("followup_id")
        if not isinstance(followup_id, str) or not followup_id:
            errors.append(f"{context}: followup_id is required")
        elif followup_id in seen:
            errors.append(f"duplicate followup_id: {followup_id}")
        else:
            seen.add(followup_id)
        record["req_ids"] = _as_req_ids(record.get("req_ids"), context, errors)
        if record.get("category") not in VALID_FOLLOWUP_CATEGORIES:
            errors.append(f"{context}: invalid category {record.get('category')!r}")
        if record.get("status") not in VALID_FOLLOWUP_STATUSES:
            errors.append(f"{context}: invalid status {record.get('status')!r}")
        if record.get("category") == "deferred" and record.get("status") in {"pending", "in_progress"}:
            if not str(record.get("reason", "")).strip():
                errors.append(f"{context}: open deferred followup requires reason")
            if not str(record.get("next_action", "")).strip():
                errors.append(f"{context}: open deferred followup requires next_action")
    return records


def load_bundle(workdir: Path) -> DataBundle:
    errors: list[str] = []
    warnings: list[str] = []
    requirements = _parse_requirements(workdir / "session-goal.md", errors, warnings)
    tasks = _validate_tasks(_read_json(workdir / "task-queue.json", errors), errors)
    evidence = _validate_evidence(_read_jsonl(workdir / "evidence.jsonl", errors), errors)
    followups = _validate_followups(_read_jsonl(workdir / "followups.jsonl", errors), errors)

    known = set(requirements)
    for record_type, records, id_field in (
        ("task", tasks, "task_id"),
        ("evidence", evidence, "evidence_id"),
        ("followup", followups, "followup_id"),
    ):
        for record in records:
            unknown = sorted(set(record.get("req_ids", [])) - known)
            if unknown:
                errors.append(
                    f"{record_type} {record.get(id_field, '<unknown>')} references unknown requirements: {', '.join(unknown)}"
                )

    return DataBundle(requirements, tasks, evidence, followups, errors, warnings)


def linked(records: Iterable[dict[str, Any]], req_id: str) -> list[dict[str, Any]]:
    return [record for record in records if req_id in record.get("req_ids", [])]


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}
