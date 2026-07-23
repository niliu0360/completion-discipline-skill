# Completion Status

- `COMPLETE`：所有活动 REQ 均有完成任务，且所有 ACC / INV 的证据要求满足。
- `CLOSED_WITH_EXCEPTIONS`：仅剩已披露的延期、拒绝或 out-of-scope。
- `IN_PROGRESS`：存在未完成任务、OPEN action、缺失证据或未映射要求。
- `INVALID`：Control Record 结构或引用关系无效。

这些状态不授予 MERGE、PUSH、RELEASE 或 DEPLOY 权限。
