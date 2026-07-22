#!/usr/bin/env python3
"""Initialize project-local completion-discipline files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "0.1.0"

SESSION_TEMPLATE = """# Session Goal

## Source

{source}

## Requirements

- [REQ-001] Replace this placeholder with the first requirement — needs: test

## Open decisions

- None.

## Constraints

- None.
"""

TASK_TEMPLATE = {
    "version": VERSION,
    "tasks": [
        {
            "task_id": "TASK-001",
            "title": "Replace this placeholder with an implementation task",
            "req_ids": ["REQ-001"],
            "status": "pending",
            "reason": "",
            "next_action": "",
            "disclosed_to_user": False,
        }
    ],
}


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return "kept"
    path.write_text(content, encoding="utf-8")
    return "written"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Target project root (default: current directory)")
    parser.add_argument("--workdir-name", default=".ai-work", help="Project-local work directory name")
    parser.add_argument("--source", default="User request or supplied source material", help="Source text for session-goal.md")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    workdir = root / args.workdir_name
    workdir.mkdir(parents=True, exist_ok=True)

    results = {
        "session-goal.md": write_file(workdir / "session-goal.md", SESSION_TEMPLATE.format(source=args.source), args.force),
        "task-queue.json": write_file(
            workdir / "task-queue.json",
            json.dumps(TASK_TEMPLATE, ensure_ascii=False, indent=2) + "\n",
            args.force,
        ),
        "evidence.jsonl": write_file(workdir / "evidence.jsonl", "", args.force),
        "followups.jsonl": write_file(workdir / "followups.jsonl", "", args.force),
    }

    print(f"completion-discipline {VERSION}: initialized {workdir}")
    for name, status in results.items():
        print(f"- {status}: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
