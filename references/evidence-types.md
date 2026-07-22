# 证据类型

`session-goal.md` 中的每个需求都以 `— needs: ...` 结尾。

## 封闭词表

| 值 | 适用情况 | 满足条件 |
|---|---|---|
| `test` | 可以通过自动化或可重复命令验证行为 | 存在 `type=test`、`status=pass` 的证据，并包含命令或产物引用 |
| `review` | 正确性依赖结构化评审 | 存在 `type=review`、`status=pass` 的评审证据 |
| `db-probe` | 需要验证数据库迁移、查询或数据结果 | 存在 `type=db-probe`、`status=pass` 的查询结果或引用 |
| `real-host-verify` | 必须在真实主机、设备或外部环境验证 | 存在 `type=real-host-verify`、`status=pass` 的环境和观察记录 |
| `deploy-probe` | 必须验证部署后的服务或版本 | 存在 `type=deploy-probe`、`status=pass` 的健康检查、日志或端点引用 |
| `(none)` | 产物是文档、分析、决策或不需要执行验证的输出 | 不要求证据记录 |

多个证据类型使用逗号分隔：

```markdown
- [REQ-001] 增加导入接口 — needs: review, test
- [REQ-002] 验证部署后的接口 — needs: deploy-probe, real-host-verify
- [REQ-003] 输出架构说明 — needs: (none)
```

不要自行增加 `lint`、`e2e` 等新标签。使用最接近的现有类型，通常是 `test`，并在证据记录中写清实际命令。
