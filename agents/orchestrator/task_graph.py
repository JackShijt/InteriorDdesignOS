"""
InteriorDesignOS · Task Graph

本模块遵守 PROJECT_RULES.md 的最高约束。

动态 Task Graph（Phase 2 §4 / PROJECT_RULES §13、§16）：
- 创建 / 查询 / 更新 / 删除任务
- 获取依赖关系（dependencies）
- 获取可执行任务（所有依赖 COMPLETED 且状态为 READY/PENDING）
- 支持 DAG，禁止循环依赖（拓扑检测）
- 维护 Task State Machine 状态转移合法性（PROJECT_RULES §13.1）

数据契约遵循 schemas/core/task.schema.json：
  required: task_id / agent / stage / status
  status ∈ {PENDING, READY, RUNNING, WAITING_USER, WAITING_AGENT,
            RETRYING, VALIDATING, REPAIRING, COMPLETED, FAILED,
            CANCELLED, DELIVERED}
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from agents.orchestrator.error_handler import ValidationError

# 任务状态机（与 schemas/core/task.schema.json 一致）
TASK_STATUSES = [
    "PENDING", "READY", "RUNNING", "WAITING_USER", "WAITING_AGENT",
    "RETRYING", "VALIDATING", "REPAIRING", "COMPLETED", "FAILED",
    "CANCELLED", "DELIVERED",
]

# 任务状态机合法转移（PROJECT_RULES §13.1 / §13.4）
TASK_TRANSITIONS: Dict[str, List[str]] = {
    "PENDING": ["READY", "CANCELLED"],
    "READY": ["RUNNING", "CANCELLED", "WAITING_USER", "WAITING_AGENT"],
    "RUNNING": ["VALIDATING", "REPAIRING", "FAILED", "CANCELLED", "WAITING_USER"],
    "WAITING_USER": ["READY", "RUNNING", "CANCELLED"],
    "WAITING_AGENT": ["READY", "RUNNING", "CANCELLED"],
    "RETRYING": ["RUNNING", "READY", "FAILED", "CANCELLED"],
    "VALIDATING": ["COMPLETED", "REPAIRING", "FAILED", "CANCELLED"],
    "REPAIRING": ["VALIDATING", "COMPLETED", "FAILED", "CANCELLED"],
    "COMPLETED": ["DELIVERED", "CANCELLED"],
    "FAILED": ["RETRYING", "READY", "CANCELLED"],
    "CANCELLED": [],
    "DELIVERED": [],
}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


class TaskStatus(str, Enum):
    """任务状态枚举。"""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_USER = "WAITING_USER"
    WAITING_AGENT = "WAITING_AGENT"
    RETRYING = "RETRYING"
    VALIDATING = "VALIDATING"
    REPAIRING = "REPAIRING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DELIVERED = "DELIVERED"


@dataclass
class Task:
    """Task Graph 节点（对应 schemas/core/task.schema.json）。"""
    task_id: str
    agent: str
    stage: str
    status: str = "PENDING"
    dependencies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    # 非契约扩展字段（不写入 task schema 校验对象）
    result_ref: Optional[str] = None
    notes: str = ""
    input_refs: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Task":
        return cls(
            task_id=d["task_id"],
            agent=d["agent"],
            stage=d["stage"],
            status=d.get("status", "PENDING"),
            dependencies=list(d.get("dependencies", [])),
            created_at=d.get("created_at", _now_iso()),
            updated_at=d.get("updated_at", _now_iso()),
            result_ref=d.get("result_ref"),
            notes=d.get("notes", ""),
            input_refs=list(d.get("input_refs", [])),
            parameters=dict(d.get("parameters", {})),
        )


class TaskStateMachine:
    """任务状态机：校验状态转移合法性（PROJECT_RULES §13）。"""

    @staticmethod
    def can_transition(frm: str, to: str) -> bool:
        if frm not in TASK_TRANSITIONS:
            return False
        return to in TASK_TRANSITIONS[frm]

    @staticmethod
    def validate(frm: str, to: str) -> None:
        if not TaskStateMachine.can_transition(frm, to):
            raise ValidationError(f"非法任务状态转移: {frm} -> {to}")


class TaskGraph:
    """有向无环任务图（DAG）。"""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    # ---- CRUD ----
    @property
    def tasks(self) -> Dict[str, "Task"]:
        """任务字典（task_id -> Task），供上层只读访问。"""
        return self._tasks

    def create_task(self, task_id: str, agent: str, stage: str,
                    dependencies: Optional[List[str]] = None,
                    status: str = "PENDING",
                    input_refs: Optional[List[str]] = None,
                    parameters: Optional[Dict[str, Any]] = None) -> Task:
        if task_id in self._tasks:
            raise ValidationError(f"task_id 已存在: {task_id}")
        deps = list(dependencies or [])
        for d in deps:
            if d not in self._tasks:
                raise ValidationError(f"依赖不存在: {d}")
        task = Task(task_id=task_id, agent=agent, stage=stage,
                    status=status, dependencies=deps,
                    input_refs=list(input_refs or []),
                    parameters=dict(parameters or {}))
        self._tasks[task_id] = task
        # 创建后立即检测是否会引入环
        self._assert_no_cycle()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update_status(self, task_id: str, new_status: str) -> Task:
        task = self._require(task_id)
        TaskStateMachine.validate(task.status, new_status)
        task.status = new_status
        task.updated_at = _now_iso()
        return task

    def reset_status(self, task_id: str, new_status: str = "PENDING") -> Task:
        """恢复专用：直接重置状态，绕过状态机校验（Phase 2 §8 恢复运行）。"""
        task = self._require(task_id)
        task.status = new_status
        task.updated_at = _now_iso()
        return task

    def update_task(self, task_id: str, **changes: Any) -> Task:
        task = self._require(task_id)
        for k, v in changes.items():
            if k == "status":
                self.update_status(task_id, v)
            elif hasattr(task, k):
                setattr(task, k, v)
        task.updated_at = _now_iso()
        return task

    def delete_task(self, task_id: str) -> None:
        if task_id not in self._tasks:
            raise ValidationError(f"task_id 不存在: {task_id}")
        # 不允许删除仍被其它任务依赖的节点
        for t in self._tasks.values():
            if task_id in t.dependencies:
                raise ValidationError(f"任务 {task_id} 仍被 {t.task_id} 依赖，无法删除")
        del self._tasks[task_id]

    # ---- 查询 ----
    def all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def get_dependencies(self, task_id: str) -> List[Task]:
        task = self._require(task_id)
        return [self._tasks[d] for d in task.dependencies if d in self._tasks]

    def get_runnable(self) -> List[Task]:
        """返回当前可执行的任务：状态 READY 或 PENDING 且全部依赖已 COMPLETED。"""
        out = []
        for t in self._tasks.values():
            if t.status not in ("READY", "PENDING"):
                continue
            deps = self.get_dependencies(t.task_id)
            if all(d.status == "COMPLETED" for d in deps):
                out.append(t)
        return out

    def is_complete(self) -> bool:
        """所有任务均已 COMPLETED / DELIVERED / CANCELLED / FAILED。"""
        if not self._tasks:
            return False
        return all(t.status in ("COMPLETED", "DELIVERED", "CANCELLED", "FAILED")
                   for t in self._tasks.values())

    def has_failed(self) -> bool:
        return any(t.status == "FAILED" for t in self._tasks.values())

    # ---- 持久化 ----
    def to_dict(self) -> Dict[str, Any]:
        return {"tasks": [t.to_dict() for t in self._tasks.values()]}

    def save(self, path) -> None:
        import json
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path) -> "TaskGraph":
        import json
        from pathlib import Path
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        g = cls()
        for td in data.get("tasks", []):
            # load 时跳过 create_task 的环检测（图已存在）
            g._tasks[td["task_id"]] = Task.from_dict(td)
        return g

    # ---- 内部 ----
    def _require(self, task_id: str) -> Task:
        t = self._tasks.get(task_id)
        if t is None:
            raise ValidationError(f"task_id 不存在: {task_id}")
        return t

    def _assert_no_cycle(self) -> None:
        """拓扑排序检测环；存在环则抛 ValidationError。"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in self._tasks}

        def dfs(tid: str):
            color[tid] = GRAY
            for dep in self._tasks[tid].dependencies:
                if dep not in self._tasks:
                    continue
                if color[dep] == GRAY:
                    raise ValidationError(f"检测到循环依赖: {tid} -> {dep}")
                if color[dep] == WHITE:
                    dfs(dep)
            color[tid] = BLACK

        for tid in list(self._tasks):
            if color[tid] == WHITE:
                dfs(tid)


__all__ = [
    "TASK_STATUSES", "TASK_TRANSITIONS", "TaskStatus", "Task",
    "TaskStateMachine", "TaskGraph",
]
