# completion-discipline 0.1.0

> **Status: Public Beta** — explicit workflow, deterministic checks, no automatic enforcement.

Requirement reconciliation and evidence-based completion checks for AI coding agents.

一个用于 AI Coding 的单入口 Skill，防止用户原始需求在执行过程中被 TodoList 悄悄收敛、遗漏。

## 它解决什么问题

AI 把 Todo 全部完成，不代表把用户的全部需求都完成了。

本 Skill 提供三个模式：

1. **需求建账**：从用户原始需求提取稳定的 `REQ-xxx` 锚点。
2. **执行对账**：让任务、验证证据、延期和拒绝都能追溯到 REQ。
3. **完成检查**：宣布完成前逐项分类，明确区分真正完成、带例外收口和仍在进行中。

## 为什么是 Skill，不是 Plugin

0.1.0 只保留最通用的需求对账能力。它不会：

- 注册生命周期 hooks；
- 拦截 Git 命令；
- 管理 worktree；
- 自动删除文件或分支；
- 记录所有工具调用；
- 发送外部通知；
- 写入全局 AI 工具目录。

## 安装

将整个 `completion-discipline` 目录复制到 AI Coding 工具支持的 Skills 目录，或者在项目中直接引用 `SKILL.md`。

确定性脚本要求 Python 3.9 及以上，只使用标准库。

支持情况：

- Linux：通过 GitHub Actions 测试；
- macOS：脚本仅依赖 Python 标准库，预期兼容，尚未纳入 CI；
- Windows WSL2：已人工验证；
- Windows 原生：尚未验证。

## 快速开始

在目标项目根目录运行：

```bash
python3 /path/to/completion-discipline/scripts/init_workspace.py
```

编辑 `.ai-work/session-goal.md` 和 `.ai-work/task-queue.json`，然后执行：

```bash
python3 /path/to/completion-discipline/scripts/reconcile_requirements.py --workdir .ai-work
python3 /path/to/completion-discipline/scripts/completion_check.py --workdir .ai-work --write-report
```

同一 REQ、同一证据类型以 `evidence.jsonl` 中最后一条记录为当前有效证据；后续失败会覆盖旧的通过记录，新的通过也可以覆盖旧失败。

## 测试与退出码

```bash
bash tests/run_all.sh
```

| 退出码 | 含义 |
|---:|---|
| `0` | `COMPLETE` |
| `3` | `CLOSED_WITH_EXCEPTIONS` |
| `2` | `IN_PROGRESS` 或 `INVALID` |

## 数据与安全

- 所有状态文件都位于项目本地 `.ai-work/`。
- 初始化脚本默认不会覆盖已有文件，只有显式使用 `--force` 才会覆盖。
- 检查脚本不会运行测试、Git、网络请求、部署操作或删除操作。
- `evidence.jsonl` 只记录已经真实执行过的验证；脚本不会自动执行或编造证据。
- `.ai-work/` 可以作为本地临时数据加入项目 `.gitignore`，也可以作为团队协作台账提交到仓库。证据可能包含路径、命令和环境信息，提交前必须审查。

## 版本定位

`0.1.0` 是 Public Beta，范围刻意限制在需求建账、执行对账和完成报告；它提供显式工作流和确定性检查，不提供自动强制执行。
