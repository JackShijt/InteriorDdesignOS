"""
InteriorDesignOS · Scheduler

本模块遵守 PROJECT_RULES.md 的最高约束。

调度器（Phase 2 §4、§16 / PROJECT_RULES §16 动态 Task Graph）：
- 依据阶段顺序动态生成默认 Task Graph（最小化执行路径）
- 提供「当前可调度任务」：将依赖已满足的 PENDING 任务提升为 READY，并返回
- 不负责业务执行（交由 Dispatcher，PROJECT_RULES §2.3）

默认图为线性 DAG（12 阶段依次依赖），满足「支持 DAG、禁止循环依赖」。
"""

from typing import Callable, Dict, List, Optional

from runtime.event_bus import EventBus
from runtime.logger import UnifiedLogger
from runtime.message import Event, EventType
from runtime.project_runtime import STAGES
from agents.orchestrator.task_graph import Task, TaskGraph

# 阶段 -> 默认 Agent 名称（可被 registry 覆盖；虚拟阶段使用 stage.lower()）
DEFAULT_AGENT_FOR_STAGE: Dict[str, str] = {s: s.lower() for s in STAGES}


class Scheduler:
    """动态 Task Graph 构建与就绪任务供给。"""

    def __init__(self, task_graph: TaskGraph, event_bus: EventBus, logger: UnifiedLogger,
                 agent_for_stage: Optional[Callable[[str], str]] = None):
        self._graph = task_graph
        self._bus = event_bus
        self._logger = logger
        self._agent_for_stage = agent_for_stage or (lambda s: DEFAULT_AGENT_FOR_STAGE.get(s, s.lower()))

    def build_default_graph(self, project_id: str) -> List[Task]:
        """按 12 阶段顺序构建默认线性 DAG，每个任务依赖上一阶段任务。"""
        tasks: List[Task] = []
        prev_id: Optional[str] = None
        for stage in STAGES:
            task_id = f"{stage.lower()}-{project_id}"
            agent = self._agent_for_stage(stage)
            deps = [prev_id] if prev_id else []
            task = self._graph.create_task(
                task_id=task_id, agent=agent, stage=stage, dependencies=deps,
            )
            # 根任务（无依赖）立即置为 READY
            if not deps:
                self._graph.update_status(task.task_id, "READY")
            self._bus.publish(Event(
                EventType.TASK_CREATED,
                {"project_id": project_id, "task_id": task.task_id,
                 "agent": agent, "stage": stage},
            ))
            tasks.append(task)
            prev_id = task.task_id
        self._logger.runtime("task_graph_built", project_id=project_id,
                             task_count=len(tasks))
        return tasks

    def next_ready(self) -> List[Task]:
        """将依赖已满足的 PENDING 任务提升为 READY，并返回可调度任务。"""
        for t in self._graph.all_tasks():
            if t.status == "PENDING":
                deps = self._graph.get_dependencies(t.task_id)
                if all(d.status == "COMPLETED" for d in deps):
                    self._graph.update_status(t.task_id, "READY")
        return self._graph.get_runnable()


__all__ = ["DEFAULT_AGENT_FOR_STAGE", "Scheduler"]
