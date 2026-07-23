# Changelog

## 0.2.0-beta.1 — 2026-07-24

- 新任务切换到统一的 `.ai-control/control-record.json`。
- 使用 REQ、ACC、INV、TASK、EV 和 ACT 统一完成对账。
- 完成状态改由 AI Engineering Control Layer 共享 Runtime 计算。
- Evidence Ledger 改为追加式记录，并使用显式 `supersedes` 关系。
- 有效 PASS 与 FAIL 冲突时保守判定为未完成。
- 保留原有三个命令名作为轻量兼容包装。
- 增加 Evidence 追加和旧 `.ai-work` 迁移入口。
- Runtime、Schema、示例和 Manifest 由 Control Layer 确定性构建。
- `COMPLETE` 不再被表述为合并、推送或发布授权。

## 0.1.0 — 2026-07-22

- 将项目重构为单一入口的 `completion-discipline` Skill。
- 内部提供三个模式：需求建账、执行对账、完成检查。
- 使用项目本地 `.ai-work` 保存需求、任务、证据和 followup。
- 增加三个只依赖 Python 标准库的确定性脚本。
- 增加 JSON Schema、完整示例和自动化测试。
- 空需求台账现在判定为 `INVALID`，避免零条 REQ 被误判为 `COMPLETE`。
- 同一 REQ、同一证据类型改为以最后一条记录为准，后续失败不再被旧 pass 掩盖。
- 增加 Python 3.9–3.13 CI、Public Beta 状态和公共贡献/安全说明。
- 公开包不再包含自动 hooks、全局会话状态、Git/worktree 拦截、自动清理、外部通知、固定项目名、固定路径和固定时区。
