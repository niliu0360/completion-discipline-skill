# 模式一：需求建账

## 目标

在实现过程把原始要求压缩成更少的 Todo 之前，先建立稳定、可追溯的需求清单。

## 触发条件

满足任一条件就使用：

- 请求包含三项以上需求、缺陷、验收标准或评审意见；
- 用户提供多张相互关联的表格或清单；
- 用户使用“全部”“所有”“逐项”“一次性处理”等完整性表述；
- 用户询问是否还有遗漏。

## 操作步骤

### 1. 保留来源

在 `session-goal.md` 中记录需求来源：用户消息、报告、Issue、评审文档或上传文件。

### 2. 展开为独立 REQ

每个可以独立验收的结果都有一个稳定 ID：

```markdown
## Requirements

- [REQ-001] 按约定字段导入 CSV — needs: test
- [REQ-002] 返回逐行校验错误 — needs: review, test
- [REQ-003] 更新操作手册 — needs: (none)
```

即使 REQ-001 和 REQ-002 最终由同一段实现完成，也不能在建账时合并成一项。

### 3. 对齐多个来源

如果报告同时包含问题表和优先级表，必须逐行映射。无法对应或互相矛盾的条目写入 `## Open decisions`，不能直接选一张表开始实现。

### 4. 建立执行视图

在 `task-queue.json` 创建任务：

```json
{
  "version": "0.1.0",
  "tasks": [
    {
      "task_id": "TASK-001",
      "title": "实现 CSV 解析和校验",
      "req_ids": ["REQ-001", "REQ-002"],
      "status": "pending",
      "reason": "",
      "next_action": "",
      "disclosed_to_user": false
    },
    {
      "task_id": "TASK-002",
      "title": "更新操作手册",
      "req_ids": ["REQ-003"],
      "status": "pending",
      "reason": "",
      "next_action": "",
      "disclosed_to_user": false
    }
  ]
}
```

一个任务可以关联多个 REQ，但完成检查仍会逐项判定每个 REQ。

### 5. 立即运行结构对账

运行 `reconcile_requirements.py`，在开始实现前修复未映射 REQ 和未知引用。
