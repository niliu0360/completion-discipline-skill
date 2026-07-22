# 文件格式

## `session-goal.md`

```markdown
# Session Goal

## Source

<需求来源>

## Requirements

- [REQ-001] <需求描述> — needs: test
- [REQ-002] <需求描述> — needs: (none)

## Open decisions

- None.

## Constraints

- None.
```

REQ ID 必须匹配 `REQ-[0-9]{3,}`，并且不能重复。

## `task-queue.json`

见 `schemas/task-queue.schema.json`。

## `evidence.jsonl`

每个非空行是一个 JSON 对象。见 `schemas/evidence-record.schema.json`。

## `followups.jsonl`

每个非空行是一个 JSON 对象。见 `schemas/followup-record.schema.json`。

## `completion-report.json`

由 `completion_check.py` 生成。见 `schemas/completion-report.schema.json`。
