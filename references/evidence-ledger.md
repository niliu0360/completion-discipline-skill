# Evidence Ledger

每条证据使用独立 `EV-xxx` ID，记录 producer、subject_refs、category、status、summary、applicability、source 和 limitations。

证据条目不可原地修改。重新执行验证后追加新 EV。

替代旧证据时显式写入：

```json
{"evidence_id":"EV-002","supersedes":["EV-001"]}
```

只有当前有效、适用且状态为 `PASS` 的证据才能满足 ACC 或 INV。
