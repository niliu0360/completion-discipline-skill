# 模式二：执行对账

## 原则

先更新需求台账，再更新任务视图。只写进 Todo、没有进入 REQ 台账的新发现，仍可能在最终复核时消失。

## 任务状态

| 状态 | 含义 | 必填信息 |
|---|---|---|
| `pending` | 尚未开始 | 无 |
| `in_progress` | 正在处理 | 无 |
| `completed` | 实现工作已经完成 | 验证证据按 REQ 单独检查 |
| `deferred` | 明确延期 | `reason`、`next_action` |
| `rejected` | 明确决定不做 | `reason`、`disclosed_to_user: true` |

## 证据记录

在 `evidence.jsonl` 中每行追加一个 JSON 对象：

```json
{"evidence_id":"EV-001","req_ids":["REQ-001"],"type":"test","status":"pass","summary":"导入测试通过","command":"pytest tests/test_import.py -q","reference":"12 passed"}
```

规则：

- `status` 只能是 `pass` 或 `fail`；
- 只有同一次验证确实能证明多个 REQ 时，才允许一条证据关联多个 REQ；
- 失败记录不能满足 `needs`，修复后应追加新的通过记录；
- 不得记录实际没有执行过的命令。

## Followup 记录

在 `followups.jsonl` 中每行保存一个当前 followup：

```json
{"followup_id":"FU-001","req_ids":["REQ-004"],"category":"deferred","status":"pending","reason":"外部测试环境不可用","next_action":"环境恢复后完成验证"}
```

支持的分类：`deferred`、`verification`、`decision`、`other`。
支持的状态：`pending`、`in_progress`、`completed`、`dismissed`。

一个延期 REQ 只有在存在未关闭的 `category=deferred` 记录，并且原因和下一步都不为空时，才算被显式对账。

## 范围变化

用户新增、删除或调整范围时：

1. 更新 `session-goal.md`；
2. 新增或修改关联任务；
3. 在决策或约束中解释变化；
4. 运行 `reconcile_requirements.py`；
5. 明确告诉用户哪些需求被拒绝或移出本轮范围。
