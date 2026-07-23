from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def run_cmd(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(expected, result.returncode, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    @staticmethod
    def write_json(path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_native_completion_and_supersession(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            record = project / ".ai-control" / "control-record.json"
            self.run_cmd(str(ROOT / "scripts" / "init_workspace.py"), "--project-root", str(project), "--repository", "example/repository")
            value = json.loads(record.read_text(encoding="utf-8"))
            value["execution_plan"]["tasks"][0]["status"] = "COMPLETED"
            self.write_json(record, value)
            base = {"evidence_key":"ACC-001:automated_test","producer":{"type":"AGENT","name":"distribution-test"},"subject_refs":["REQ-001","ACC-001"],"category":"automated_test","subtype":"unit","limitations":[],"applicability":{"repository":"example/repository","environment":"test"},"source":{"command":"python -m unittest"}}
            first = {**base,"evidence_id":"EV-001","recorded_at":"2026-07-24T00:00:00Z","status":"PASS","summary":"Tests passed.","supports_claims":["ACC-001 passed."],"supersedes":[]}
            first_path = project / "ev1.json"
            self.write_json(first_path, first)
            self.run_cmd(str(ROOT / "scripts" / "append_evidence.py"), "--record", str(record), "--entry", str(first_path))
            complete = self.run_cmd(str(ROOT / "scripts" / "completion_check.py"), "--record", str(record), "--json", "--write-report")
            self.assertEqual("COMPLETE", json.loads(complete.stdout)["status"])
            self.assertTrue((project / ".ai-control" / "derived" / "completion-report.json").is_file())
            failure = {**base,"evidence_id":"EV-002","recorded_at":"2026-07-24T00:01:00Z","status":"FAIL","summary":"Regression failed.","supports_claims":[],"supersedes":["EV-001"]}
            failure_path = project / "ev2.json"
            self.write_json(failure_path, failure)
            self.run_cmd(str(ROOT / "scripts" / "append_evidence.py"), "--record", str(record), "--entry", str(failure_path))
            reopened = self.run_cmd(str(ROOT / "scripts" / "completion_check.py"), "--record", str(record), "--json", expected=2)
            self.assertEqual("IN_PROGRESS", json.loads(reopened.stdout)["status"])

    def test_legacy_example_migrates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "control-record.json"
            result = self.run_cmd(str(ROOT / "scripts" / "migrate_legacy_workspace.py"), "--workdir", str(ROOT / "examples" / "legacy" / ".ai-work"), "--output", str(output))
            self.assertEqual("COMPLETE", json.loads(result.stdout)["status"])
            self.assertTrue(output.is_file())

    def test_generated_source_boundary(self) -> None:
        source = (ROOT / ".generated-source").read_text(encoding="utf-8")
        self.assertIn("niliu0360/ai-engineering-control-layer", source)
        self.assertFalse((ROOT / "scripts" / "_common.py").exists())
        self.assertTrue((ROOT / "runtime" / "aicl" / "reconciliation.py").is_file())
        self.assertTrue((ROOT / "schemas" / "control-record.schema.json").is_file())


if __name__ == "__main__":
    unittest.main()
