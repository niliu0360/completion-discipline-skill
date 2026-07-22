# 模式三：完成检查

## 单项判定

检查脚本为每个 REQ 分配一种状态：

| 状态 | 判定规则 |
|---|---|
| `completed` | 存在关联任务；关联任务全部完成；所有 `needs` 都有通过证据 |
| `deferred` | 存在原因和下一步完整的延期任务或未关闭延期 followup |
| `rejected` | 存在被拒绝的关联任务，并且已向用户披露 |
| `in_progress` | 仍有 pending/in_progress 任务、缺少证据，或验证/决策 followup 未关闭 |
| `missing` | 没有任务、followup 或有效例外能够解释该 REQ |

总体状态：

- `COMPLETE`：全部 REQ 都是 `completed`；
- `CLOSED_WITH_EXCEPTIONS`：没有 `in_progress` 或 `missing`，但至少存在一个 `deferred` 或 `rejected`；
- `IN_PROGRESS`：至少存在一个 `in_progress` 或 `missing`；
- `INVALID`：输入格式错误、ID 重复或引用未知 REQ。

`## Requirements` 存在但没有任何有效 REQ 时同样是 `INVALID`，不得把空台账解释为“没有未完成项”。

同一 REQ、同一 `evidence type` 以 `evidence.jsonl` 文件顺序中的最后一条记录为准。后续 `fail` 会覆盖旧 `pass`；只有最新记录为 `pass` 时，该类型的证据需求才算满足。

## 退出码

| 退出码 | 含义 |
|---:|---|
| `0` | `COMPLETE` |
| `3` | `CLOSED_WITH_EXCEPTIONS` |
| `2` | `IN_PROGRESS` 或 `INVALID` |

## 面向用户的输出约定

不能只给一个 PASS/FAIL。必须说明实际交付和未交付内容。

```markdown
## 完成状态

结论：CLOSED_WITH_EXCEPTIONS

### 已完成
- REQ-001：测试 `pytest ...`，12 passed
- REQ-002：评审记录 `review-17` 已通过

### 已延期
- REQ-003：外部环境不可用；下一步：环境恢复后验证

### 明确不做
- REQ-004：已移出范围，并已向用户说明

### 未解决
- 无
```

表述限制：

- `COMPLETE` 可以说“全部需求已完成”；
- `CLOSED_WITH_EXCEPTIONS` 只能说“全部需求已对账，但存在例外”，不能说“全部已经实现”；
- `IN_PROGRESS` 必须直接列出未闭环 REQ；
- 不得为了让总结更完整而隐藏例外。
