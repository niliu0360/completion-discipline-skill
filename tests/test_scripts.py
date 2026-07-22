#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def write_workspace(
    root: Path,
    requirements: list[str],
    tasks: list[dict],
    evidence: list[dict] | None = None,
    followups: list[dict] | None = None,
) -> Path:
    workdir = root / ".ai-work"
    workdir.mkdir()
    goal = "# Session Goal\n\n## Source\n\nTest\n\n## Requirements\n\n" + "\n".join(requirements)
    goal += "\n\n## Open decisions\n\n- None.\n\n## Constraints\n\n- None.\n"
    (workdir / "session-goal.md").write_text(goal, encoding="utf-8")
    (workdir / "task-queue.json").write_text(
        json.dumps({"version": "0.1.0", "tasks": tasks}, indent=2), encoding="utf-8"
    )
    (workdir / "evidence.jsonl").write_text(
        "\n".join(json.dumps(item) for item in (evidence or [])) + ("\n" if evidence else ""),
        encoding="utf-8",
    )
    (workdir / "followups.jsonl").write_text(
        "\n".join(json.dumps(item) for item in (followups or [])) + ("\n" if followups else ""),
        encoding="utf-8",
    )
    return workdir


class ScriptTests(unittest.TestCase):
    def test_init_does_not_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first = run("init_workspace.py", "--project-root", temp)
            self.assertEqual(first.returncode, 0, first.stderr)
            goal = Path(temp) / ".ai-work" / "session-goal.md"
            goal.write_text("custom", encoding="utf-8")
            second = run("init_workspace.py", "--project-root", temp)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(goal.read_text(encoding="utf-8"), "custom")

    def test_reconcile_passes_for_mapped_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = write_workspace(
                Path(temp),
                ["- [REQ-001] Build feature — needs: test"],
                [{"task_id": "TASK-001", "title": "Build", "req_ids": ["REQ-001"], "status": "pending"}],
            )
            result = run("reconcile_requirements.py", "--workdir", str(workdir))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("RECONCILIATION PASS", result.stdout)

    def test_reconcile_detects_unmapped_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = write_workspace(
                Path(temp),
                [
                    "- [REQ-001] Build feature — needs: test",
                    "- [REQ-002] Add docs — needs: (none)",
                ],
                [{"task_id": "TASK-001", "title": "Build", "req_ids": ["REQ-001"], "status": "pending"}],
            )
            result = run("reconcile_requirements.py", "--workdir", str(workdir))
            self.assertEqual(result.returncode, 2)
            self.assertIn("REQ-002", result.stdout)

    def test_complete_requires_passing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = write_workspace(
                Path(temp),
                ["- [REQ-001] Build feature — needs: test"],
                [{"task_id": "TASK-001", "title": "Build", "req_ids": ["REQ-001"], "status": "completed"}],
                [{
                    "evidence_id": "EV-001",
                    "req_ids": ["REQ-001"],
                    "type": "test",
                    "status": "pass",
                    "summary": "Tests passed",
                    "command": "pytest -q",
                }],
            )
            result = run("completion_check.py", "--workdir", str(workdir), "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "COMPLETE")

    def test_missing_evidence_is_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = write_workspace(
                Path(temp),
                ["- [REQ-001] Build feature — needs: test"],
                [{"task_id": "TASK-001", "title": "Build", "req_ids": ["REQ-001"], "status": "completed"}],
            )
            result = run("completion_check.py", "--workdir", str(workdir), "--json")
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "IN_PROGRESS")
            self.assertEqual(report["requirements"][0]["missing_needs"], ["test"])

    def test_deferred_followup_closes_with_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = write_workspace(
                Path(temp),
                ["- [REQ-001] Verify on external host — needs: real-host-verify"],
                [],
                followups=[{
                    "followup_id": "FU-001",
                    "req_ids": ["REQ-001"],
                    "category": "deferred",
                    "status": "pending",
                    "reason": "Host unavailable",
                    "next_action": "Verify after restoration",
                }],
            )
            result = run("completion_check.py", "--workdir", str(workdir), "--json")
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "CLOSED_WITH_EXCEPTIONS")

    def test_rejected_task_requires_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = write_workspace(
                Path(temp),
                ["- [REQ-001] Remove legacy path — needs: test"],
                [{
                    "task_id": "TASK-001",
                    "title": "Remove legacy path",
                    "req_ids": ["REQ-001"],
                    "status": "rejected",
                    "reason": "Out of scope",
                    "disclosed_to_user": False,
                }],
            )
            result = run("completion_check.py", "--workdir", str(workdir), "--json")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "INVALID")

    def test_unknown_requirement_reference_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = write_workspace(
                Path(temp),
                ["- [REQ-001] Build feature — needs: test"],
                [{"task_id": "TASK-001", "title": "Build", "req_ids": ["REQ-999"], "status": "pending"}],
            )
            result = run("completion_check.py", "--workdir", str(workdir), "--json")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
