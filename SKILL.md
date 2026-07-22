---
name: completion-discipline
description: Use when AI Coding 任务包含多项需求、缺陷、验收条件、评审意见，或用户要求“全部处理”“逐项完成”“检查遗漏”“确认是否完成”。以用户原始需求建立 REQ 台账，在执行过程中对账 Todo、证据和例外，并在宣布完成前逐项复核。不要用于没有实现或交付动作的简单单步问答。
---

# Completion Discipline

完成判定必须回到用户的原始需求。TodoList 只是执行视图，不能代替需求真源。

本 Skill 只有一个入口，内部包含三个工作模式。根据任务阶段选择模式，不要再拆成多个相互竞争的 Skill。

## 核心链路

**原始需求 → REQ 锚点 → 执行任务 → 验证证据或显式例外 → 完成前对账。**

Todo 全部勾选，不代表用户的全部需求已经完成。

## 项目内工作目录

统一使用项目本地 `.ai-work/`：

```text
.ai-work/
├── session-goal.md
├── task-queue.json
├── evidence.jsonl
├── followups.jsonl
└── completion-report.json   # 完成检查脚本生成
```

在目标项目根目录运行以下命令初始化：

```bash
python /path/to/completion-discipline/scripts/init_workspace.py
```

所有脚本仅使用 Python 标准库。

## 模式一：需求建账

适用于开始实现之前，特别是用户提供了多项需求、缺陷清单、多张表格、验收标准，或使用“全部”“逐项”“都处理”“不要遗漏”等表述时。

1. 阅读用户原始消息和所有提供的材料。
2. 将每个可以独立验收的要求展开为稳定锚点：`REQ-001`、`REQ-002`……
3. 保留原始含义。即使两个要求可能由同一段代码实现，也不要擅自合并。
4. 如果材料中有多张相关清单或表格，先做跨表映射；矛盾项写入约束或待决策，不要静默选择。
5. 按 `references/evidence-types.md` 为每个 REQ 标记 `needs`。
6. 在 `task-queue.json` 创建执行任务，每个任务必须引用一个或多个 REQ。
7. 运行结构对账：

```bash
python /path/to/completion-discipline/scripts/reconcile_requirements.py --workdir .ai-work
```

完整规则见 `references/01-requirement-ledger.md`。

## 模式二：执行对账

适用于实现过程中，特别是出现范围变化、新发现、验证失败，或者决定本轮不处理某项需求时。

1. 持续维护任务状态：`pending`、`in_progress`、`completed`、`deferred`、`rejected`。
2. 范围发生变化时，先更新 REQ 台账，再更新任务；不允许只改 Todo。
3. 完成实际验证后，将证据写入 `evidence.jsonl`。
4. 延期项写入 `followups.jsonl`，必须包含原因和下一步。
5. 拒绝项必须写明原因，并设置 `disclosed_to_user: true`，表示已经向用户明确说明。
6. 每次发生实质变化后重新运行结构对账脚本。

完整规则见 `references/02-execution-reconciliation.md`。

## 模式三：完成检查

在准备说“完成”“全部处理完”“可以交付”“可以合并”之前必须使用。

```bash
python /path/to/completion-discipline/scripts/completion_check.py \
  --workdir .ai-work \
  --write-report
```

严格按结果表述：

- `COMPLETE`：全部 REQ 已完成，并满足各自要求的验证证据。
- `CLOSED_WITH_EXCEPTIONS`：没有静默遗漏，但存在明确延期或明确拒绝的 REQ。不得描述成“全部已经实现”。
- `IN_PROGRESS`：仍有任务、证据、验证或决策没有闭环。
- `INVALID`：台账格式错误、ID 重复，或存在未知 REQ 引用。

面向用户输出时，至少列出：已完成项、例外项、未解决项和证据。不得隐藏 `deferred`、`rejected`、`missing` 或证据缺失。

完整规则见 `references/03-completion-check.md`。

## 不可违反的规则

1. 原始 REQ 台账是完成判定真源，`task-queue.json` 不是。
2. 每个任务、证据和 followup 都必须引用有效 REQ。
3. `## Requirements` 不得为空；零条 REQ 是无效台账，不能判定为完成。
4. 代码或配置类 REQ 被标记为完成时，必须有明确验证证据；“测试通过了”这句话本身不算证据。
5. 同一 REQ、同一证据类型以 `evidence.jsonl` 中最后一条记录为当前有效状态；后续失败会使旧 pass 失效。
6. 延期不等于完成，必须写明原因和下一步。
7. 拒绝项只有在向用户明确披露后，才算被完整对账。
8. 未映射 REQ、未知引用、未完成任务或证据缺失都会阻止 `COMPLETE`。
9. 不得编造证据。只记录真实执行过的命令、产物、评审或观察结果。

## 可选确定性脚本

| 脚本 | 用途 |
|---|---|
| `scripts/init_workspace.py` | 创建项目内台账文件；默认不覆盖已有文件。 |
| `scripts/reconcile_requirements.py` | 检查未映射需求、未知 REQ、重复 ID 和格式错误。 |
| `scripts/completion_check.py` | 逐项判定 REQ 状态，并生成确定性的完成报告。 |

脚本只能检查已记录的数据，不能代替重新阅读用户的原始需求。
