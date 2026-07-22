# Contributing

Contributions are welcome during the Public Beta.

1. Open an issue describing the behavior or safety boundary being changed.
2. Keep the Skill single-entry and preserve the distinction between requirements, execution tasks, evidence, and explicit exceptions.
3. Add a regression test for every completion-classification change.
4. Run `bash tests/run_all.sh` before submitting a pull request.

Do not add automatic hooks, hidden network calls, destructive actions, or fabricated evidence.
