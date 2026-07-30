# Orchestrator Memory

## 会话记忆结构

```json
{
  "session_id": "uuid",
  "context": {
    "current_project": null,
    "current_stage": null,
    "user_preferences": {},
    "agent_states": {}
  },
  "history": []
}
```

## 记忆策略
- 短期记忆: 当前会话上下文
- 长期记忆: 用户偏好和历史项目模式
