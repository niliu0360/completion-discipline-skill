# Changelog

## 0.1.0 — 2026-07-22

- 将项目重构为单一入口的 `completion-discipline` Skill。
- 内部提供三个模式：需求建账、执行对账、完成检查。
- 使用项目本地 `.ai-work` 保存需求、任务、证据和 followup。
- 增加三个只依赖 Python 标准库的确定性脚本。
- 增加 JSON Schema、完整示例和自动化测试。
- 公开包不再包含自动 hooks、全局会话状态、Git/worktree 拦截、自动清理、外部通知、固定项目名、固定路径和固定时区。
