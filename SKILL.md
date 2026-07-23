---
name: completion-discipline
description: Use when AI Coding 任务包含多项需求、缺陷、验收条件或评审意见，或用户要求“全部处理”“逐项完成”“检查遗漏”“确认是否完成”。以原始需求建立 REQ 和 ACC 契约，将任务、证据与例外写入统一 Control Record，并在宣布完成前确定性对账。不要把 Todo 全部完成等同于需求全部完成。
---

# Completion Discipline

完成判定必须回到用户原始需求。Todo 只是执行视图，不能代替需求真源。

本 Skill 是 AI Engineering Control Layer 的 Completion Profile。它是自包含发布包，不要求用户另外安装 Control Layer。

## 核心链路

**原始需求 → REQ → ACC / INV → TASK → EV 或显式例外 → Completion Reconciliation。**

## 项目内状态

原生状态只使用：

```text
.ai-control/
├── control-record.json
└── derived/
    └── completion-report.json
```

旧版 `.ai-work/` 只作为 0.1.x 迁移输入，不再是新任务的状态真源。

## 模式一：需求建账

在开始实现前：

1. 重新阅读用户原始消息和全部材料。
2. 每个可独立验收的要求建立稳定 `REQ-xxx`。
3. 每个活动 REQ 至少关联一个可验证 `ACC-xxx` 或必要的 `INV-xxx`。
4. 不因两个要求可能由同一段代码实现而合并原始要求。
5. 将执行任务写入 `execution_plan.tasks`，并通过 `subject_refs` 关联 REQ、ACC 或 INV。
6. 不确定项写入 `open_decisions`，禁止静默选择。
7. 范围写入 allowed、forbidden 和 out_of_scope。

初始化最小记录：

```bash
python scripts/init_workspace.py --project-root .
```

初始化模板只是起点。必须根据真实需求修改 `.ai-control/control-record.json`。

## 模式二：执行对账

实现过程中：

1. 需求变化先更新 Acceptance Contract，再更新 TASK。
2. TASK 状态只使用 `PENDING`、`IN_PROGRESS`、`COMPLETED`、`DEFERRED`、`REJECTED`。
3. 验证完成后追加 EV，不得编造测试、评审或环境结果。
4. Evidence Ledger 只追加，不修改历史记录。
5. 新证据替代旧证据时必须显式填写 `supersedes`，不能依赖文件顺序。
6. 延期、拒绝和 out-of-scope 必须更新 REQ disposition、原因及 `disclosed_to_user: true`。
7. 未解决事项写入 `open_actions`。

追加一条已准备好的证据 JSON：

```bash
python scripts/append_evidence.py \
  --record .ai-control/control-record.json \
  --entry /path/to/evidence-entry.json
```

结构和映射检查：

```bash
python scripts/reconcile_requirements.py \
  --record .ai-control/control-record.json
```

## 模式三：完成检查

准备表述“完成”“全部处理完”之前必须执行：

```bash
python scripts/completion_check.py \
  --record .ai-control/control-record.json \
  --write-report
```

严格按结果表述：

- `COMPLETE`：全部活动 REQ 的任务和证据已经闭环。
- `CLOSED_WITH_EXCEPTIONS`：没有静默遗漏，但存在已披露的延期、拒绝或 out-of-scope。
- `IN_PROGRESS`：仍有任务、证据、动作或决策未闭环。
- `INVALID`：Control Record 结构、ID 或引用关系无效。

Completion 状态不等于允许 MERGE、PUSH 或 RELEASE。涉及这些动作时，应交给 Delivery Gate / Policy Gate。

## 旧版迁移

已有 `.ai-work/` 时运行：

```bash
python scripts/migrate_legacy_workspace.py \
  --workdir .ai-work \
  --output .ai-control/control-record.json
```

迁移后重新检查生成的 ACC、证据适用范围、延期披露和风险未知项。

## 不可违反的规则

1. REQ / ACC / INV 是完成判定真源，TASK 不是。
2. 每个活动 REQ 必须映射任务，并关联 ACC 或 INV。
3. 没有有效 PASS 证据时，不得把要求判定为完成。
4. 后续 FAIL 只有通过显式 `supersedes` 才会使旧 PASS 失效。
5. 延期和拒绝不等于实现完成，必须披露。
6. OPEN action、未完成任务、缺失证据或未知引用都会阻止 COMPLETE。
7. 不得把 Completion 结果描述成 Git、合并或发布授权。
8. 脚本只检查记录，不运行测试、Git、网络、部署或删除操作。
