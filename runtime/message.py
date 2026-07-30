"""
InteriorDesignOS · Messages & Events

本模块遵守 PROJECT_RULES.md 的最高约束。

定义事件类型与事件对象（Phase 2 §9）：
- TaskCreated / TaskStarted / TaskFinished / TaskFailed
- StageChanged / ProjectFinished
事件采用发布/订阅模式（见 event_bus.py）。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """系统事件类型（Phase 2 §9 / Phase 3.5 §9）。"""
    TASK_CREATED = "TaskCreated"
    TASK_STARTED = "TaskStarted"
    TASK_FINISHED = "TaskFinished"
    TASK_FAILED = "TaskFailed"
    STAGE_CHANGED = "StageChanged"
    PROJECT_FINISHED = "ProjectFinished"
    # Phase 3.5 统一事件流（§9）
    PROJECT_CREATED = "ProjectCreated"
    PROJECT_STARTED = "ProjectStarted"
    STAGE_STARTED = "StageStarted"
    STAGE_COMPLETED = "StageCompleted"
    TASK_COMPLETED = "TaskCompleted"
    CHECKPOINT_SAVED = "CheckpointSaved"
    WORKSPACE_UPDATED = "WorkspaceUpdated"
    PROJECT_COMPLETED = "ProjectCompleted"
    PROJECT_FAILED = "ProjectFailed"


@dataclass
class Event:
    """事件对象：类型 + 载荷 + ISO8601 时间戳。"""
    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


__all__ = ["EventType", "Event"]
