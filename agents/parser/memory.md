# Parser Agent - Memory

## 记忆结构
Parser 为**无状态确定性 Agent**，不维护长期会话记忆；运行上下文来自 `AgentContext` 与输入文件。

```json
{
  "agent": "parser",
  "session_context": {
    "project_id": "<由 Orchestrator 提供>",
    "task_id": "<由 Orchestrator 提供>",
    "input_refs": ["<输入文件绝对路径>"]
  },
  "history": [
    { "event": "parser_finished", "project_id": "...", "success": true }
  ]
}
```

## 策略
- 短期：当前 `AgentContext` + 输入文件元数据（Hash / MIME 可复核输入未变）。
- 长期：不缓存设计偏好（Parser 不做设计）；可复用的是落盘产物 `original_model.json` 与 Checkpoint，供下游 Agent 读取。
- 复盘：通过 `workspace/logs/` 中的统一日志（ISO8601）追踪每次解析。
