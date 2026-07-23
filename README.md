# completion-discipline 0.2.0-beta.1

Completion Profile for the AI Engineering Control Layer.

它解决一个具体问题：

> AI 把 Todo 全部完成，不代表把用户原始需求全部完成。

## 0.2 的变化

- 新任务使用 `.ai-control/control-record.json`。
- REQ 关联独立可验证的 ACC，并可增加业务不变量 INV。
- Evidence Ledger 改为追加式记录，覆盖关系使用显式 `supersedes`。
- 完成状态由共享 Control Layer Runtime 计算。
- 保留原有三个命令入口，但脚本只是一层轻量包装。
- 旧 `.ai-work/` 可通过迁移脚本导入。

## 快速开始

```bash
python3 scripts/init_workspace.py --project-root .
python3 scripts/reconcile_requirements.py
python3 scripts/completion_check.py --write-report
```

实际执行前必须把初始化占位内容替换为真实 REQ、ACC 和 TASK。

## 旧版迁移

```bash
python3 scripts/migrate_legacy_workspace.py \
  --workdir .ai-work \
  --output .ai-control/control-record.json
```

## 安全边界

本 Skill 不运行测试，不调用 Git，不访问网络，不合并、不推送、不部署、不删除文件。它只维护并检查已经记录的契约、任务、证据和例外。

`COMPLETE` 只表示 Completion Profile 对账完成，不表示可以合并或上线。

## 生成来源

本仓库中的 Runtime、Schema 和兼容脚本由 `ai-engineering-control-layer` 的构建脚本生成。生成文件不应在分发仓库中手工维护。
