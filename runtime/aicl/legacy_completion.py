from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQ_PATTERN = re.compile(r"^\s*-\s*\[(REQ-\d{3,})\]\s+(.+?)\s+—\s+needs:\s*(.+?)\s*$")
VALID_NEEDS = {"test", "review", "db-probe", "real-host-verify", "deploy-probe", "(none)"}
TASK_STATUSES = {"pending", "in_progress", "completed", "deferred", "rejected"}
FOLLOWUP_CATEGORIES = {"deferred", "verification", "decision", "other"}
FOLLOWUP_STATUSES = {"pending", "in_progress", "completed", "dismissed"}
OPEN = {"pending", "in_progress"}


@dataclass(frozen=True)
class Requirement:
    req_id: str
    statement: str
    needs: tuple[str, ...]


@dataclass
class Bundle:
    requirements: dict[str, Requirement]
    tasks: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    followups: list[dict[str, Any]]
    errors: list[str]


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
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return rows
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
        return rows
    for number, raw in enumerate(lines, 1):
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
        row = dict(value)
        row["_line"] = number
        rows.append(row)
    return rows


def _parse_requirements(path: Path, errors: list[str]) -> dict[str, Requirement]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return {}
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
        return {}
    result: dict[str, Requirement] = {}
    saw = False
    inside = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "## Requirements":
            saw, inside = True, True
            continue
        if inside and stripped.startswith("## "):
            inside = False
        if not inside or not stripped.startswith("-"):
            continue
        match = REQ_PATTERN.match(line)
        if not match:
            errors.append(
                f"invalid requirement format in {path}:{number}; expected '- [REQ-001] description — needs: test'"
            )
            continue
        req_id, statement, raw_needs = match.groups()
        if req_id in result:
            errors.append(f"duplicate requirement ID {req_id} in {path}:{number}")
            continue
        needs = tuple(part.strip() for part in raw_needs.split(",") if part.strip())
        unknown = [item for item in needs if item not in VALID_NEEDS]
        if not needs:
            errors.append(f"requirement {req_id} has no needs value in {path}:{number}")
        if unknown:
            errors.append(f"requirement {req_id} uses unknown needs: {', '.join(unknown)}")
        if "(none)" in needs and len(needs) > 1:
            errors.append(f"requirement {req_id} cannot combine (none) with other needs")
        result[req_id] = Requirement(req_id, statement.strip(), needs)
    if not saw:
        errors.append(f"missing '## Requirements' section in {path}")
    elif not result:
        errors.append(f"no requirements found in {path}")
    return result


def _req_ids(value: Any, context: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        errors.append(f"{context}: req_ids must be a non-empty array of strings")
        return []
    return list(value)


def load_bundle(workdir: Path) -> Bundle:
    errors: list[str] = []
    requirements = _parse_requirements(workdir / "session-goal.md", errors)
    task_data = _read_json(workdir / "task-queue.json", errors)
    evidence = _read_jsonl(workdir / "evidence.jsonl", errors)
    followups = _read_jsonl(workdir / "followups.jsonl", errors)
    tasks: list[dict[str, Any]] = []
    if not isinstance(task_data, dict) or not isinstance(task_data.get("tasks"), list):
        errors.append("task-queue.json must contain a tasks array")
    else:
        seen: set[str] = set()
        for index, raw in enumerate(task_data["tasks"], 1):
            if not isinstance(raw, dict):
                errors.append(f"task #{index}: expected object")
                continue
            item = dict(raw)
            task_id = item.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                errors.append(f"task #{index}: task_id is required")
                continue
            if task_id in seen:
                errors.append(f"duplicate task_id: {task_id}")
            seen.add(task_id)
            if item.get("status") not in TASK_STATUSES:
                errors.append(f"{task_id}: invalid status {item.get('status')!r}")
            item["req_ids"] = _req_ids(item.get("req_ids"), task_id, errors)
            status = item.get("status")
            if status in {"deferred", "rejected"} and not str(item.get("reason", "")).strip():
                errors.append(f"{task_id}: {status} task requires reason")
            if status == "deferred" and not str(item.get("next_action", "")).strip():
                errors.append(f"{task_id}: deferred task requires next_action")
            if status == "rejected" and item.get("disclosed_to_user") is not True:
                errors.append(f"{task_id}: rejected task requires disclosed_to_user=true")
            tasks.append(item)
    _validate_evidence(evidence, errors)
    _validate_followups(followups, errors)
    known = set(requirements)
    for label, rows, key in (
        ("task", tasks, "task_id"),
        ("evidence", evidence, "evidence_id"),
        ("followup", followups, "followup_id"),
    ):
        for item in rows:
            unknown = sorted(set(item.get("req_ids", [])) - known)
            if unknown:
                errors.append(f"{label} {item.get(key, '<unknown>')} references unknown requirements: {', '.join(unknown)}")
    return Bundle(requirements, tasks, evidence, followups, errors)


def _validate_evidence(rows: list[dict[str, Any]], errors: list[str]) -> None:
    seen: set[str] = set()
    for item in rows:
        context = f"evidence.jsonl:{item.get('_line')}"
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"{context}: evidence_id is required")
        elif evidence_id in seen:
            errors.append(f"duplicate evidence_id: {evidence_id}")
        else:
            seen.add(evidence_id)
        item["req_ids"] = _req_ids(item.get("req_ids"), context, errors)
        if item.get("type") not in VALID_NEEDS - {"(none)"}:
            errors.append(f"{context}: invalid evidence type {item.get('type')!r}")
        if item.get("status") not in {"pass", "fail"}:
            errors.append(f"{context}: invalid evidence status {item.get('status')!r}")
        if not str(item.get("summary", "")).strip():
            errors.append(f"{context}: summary is required")
        if not any(str(item.get(field, "")).strip() for field in ("command", "reference", "artifact")):
            errors.append(f"{context}: one of command, reference, or artifact is required")


def _validate_followups(rows: list[dict[str, Any]], errors: list[str]) -> None:
    seen: set[str] = set()
    for item in rows:
        context = f"followups.jsonl:{item.get('_line')}"
        followup_id = item.get("followup_id")
        if not isinstance(followup_id, str) or not followup_id:
            errors.append(f"{context}: followup_id is required")
        elif followup_id in seen:
            errors.append(f"dup