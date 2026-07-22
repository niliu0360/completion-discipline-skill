#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/tests/test_scripts.py"
python3 "$ROOT/scripts/reconcile_requirements.py" --workdir "$ROOT/examples/basic/.ai-work"
python3 "$ROOT/scripts/completion_check.py" --workdir "$ROOT/examples/basic/.ai-work"

for forbidden in 'CLAUDE_PLUGIN_ROOT' '/home/' '.claude-plugin/' 'hooks/hooks.json'; do
  if grep -R -n -F --exclude='run_all.sh' --exclude-dir='.git' --exclude-dir='__pycache__' "$forbidden" "$ROOT"; then
    echo "forbidden private/plugin residue found: $forbidden" >&2
    exit 1
  fi
done

echo "all completion-discipline tests passed"
