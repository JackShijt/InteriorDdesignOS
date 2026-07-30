"""
InteriorDesignOS · Orchestrator

本模块遵守 PROJECT_RULES.md 的最高约束。

编排核心（Phase 2 §1、§15 / PROJECT_RULES §2.1）：
- 建立完整 Agent 调度框架，使工作流可跑起来（不含装修算法 / CAD / LLM）
- 负责：创建 Project、构建 TaskGraph、调度虚拟 Agent、切换 Stage、
        保存 Checkpoint、恢复 Project、输出日志、发布事件、管理 Context

入口：
  orch = Orchestrator(project_id, name=...)
  summary = orch.run()        # 新建并跑完
  summary = orch.run()        # 已存在则自动恢复续跑（Phase 2 §8）
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime import ensure_workspace
from runtime.event_bus import EventBus
from runtime.logger import UnifiedLogger
from runtime.message import Event, EventType
from runtime.project_runtime import ProjectRuntime
from agents.orchestrator.state_manager import StateManager
from agents.orchestrator.task_graph import TaskGraph
from agents.orchestrator.context_manager import ContextManager
from agents.orchestrator.checkpoint import Checkpoint
from agents.orchestrator.scheduler import Scheduler
from agents.orchestrator.dispatcher import Dispatcher
from agents.orchestrator.agent import AgentRegistry


class Orchestrator:
    """控制核心：装配并驱动整个工作流框架。"""

    def __init__(self, project_id: str, name: Optional[str] = None,
                 registry: Optional[AgentRegistry] = None,
                 workspace_root: Optional[Path] = None,
                 log_dir: Optional[Path] = None):
        ensure_workspace()
        self.project_id = project_id
        self.name = name or project_id

        self._logger = UnifiedLogger(log_dir)
        self._bus = EventBus(self._logger)
        self._pr = ProjectRuntime(workspace_root)
        self._cm = ContextManager(workspace_root)
        self._state = StateManager(self._pr, self._bus, self._logger)
        self._graph = TaskGraph()
        self._checkpoint = Checkpoint(self._cm, self._pr, self._bus, self._logger)
        self._registry = registry or AgentRegistry().build_default()
        self._scheduler = Scheduler(self._graph, self._bus, self._logger)
        self._dispatcher = Dispatcher(
            self.project_id, self._graph, self._registry, self._cm,
            self._checkpoint, self._bus, self._logger,
        )
        self._graph_path = self._pr.project_dir(self.project_id) / "task_graph.json"
        self._events: List[Dict[str, Any]] = []
        self._subscribe_logging()

    # ---- 事件订阅（日志 + 收集）----
    def _subscribe_logging(self) -> None:
        def collect(ev: Event) -> None:
            self._events.append(ev.to_dict())

        for et in EventType:
            self._bus.subscribe(et, collect)

        self._bus.subscribe(EventType.TASK_FAILED, lambda ev: self._logger.error(
            "task_failed_event", error=ev.payload.get("error"),
            project_id=self.project_id, agent=ev.payload.get("agent"),
            task_id=ev.payload.get("task_id")))
        self._bus.subscribe(EventType.PROJECT_FINISHED, lambda ev: self._logger.runtime(
            "project_finished", project_id=self.project_id))

    # ---- 组件访问（供 Pipeline / 上层调度复用，Phase 3.5 §1 调度 Orchestrator）----
    @property
    def event_bus(self) -> EventBus:
        return self._bus

    @property
    def logger(self) -> UnifiedLogger:
        return self._logger

    @property
    def project_runtime(self) -> ProjectRuntime:
        return self._pr

    @property
    def context_manager(self) -> ContextManager:
        return self._cm

    @property
    def checkpoint(self) -> Checkpoint:
        return self._checkpoint

    @property
    def state_manager(self) -> StateManager:
        return self._state

    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

    @property
    def dispatcher(self) -> Dispatcher:
        return self._dispatcher

    @property
    def task_graph(self) -> TaskGraph:
        return self._graph

    @task_graph.setter
    def task_graph(self, g: TaskGraph) -> None:
        self._graph = g
        self._scheduler._graph = g
        self._dispatcher._graph = g

    # ---- 创建 / 恢复 ----
    def create_project(self) -> Dict[str, Any]:
        if self._pr.exists(self.project_id):
            return self._pr.load(self.project_id)
        project = self._pr.create(self.project_id, self.name)
        self._scheduler.build_default_graph(self.project_id)
        self._graph.save(self._graph_path)
        self._logger.runtime("project_created", project_id=self.project_id,
                             name=self.name)
        return project

    def _load_graph_or_build(self) -> None:
        if self._graph_path.exists():
            self._graph = TaskGraph.load(self._graph_path)
        else:
            self._scheduler.build_default_graph(self.project_id)
            self._graph.save(self._graph_path)
        # 保持 dispatcher / scheduler 引用同一图实例
        self._dispatcher._graph = self._graph
        self._scheduler._graph = self._graph

    def recover(self) -> Optional[str]:
        """恢复运行：保留已完成阶段，从首个未完成阶段续跑（Phase 2 §8）。"""
        self._load_graph_or_build()
        for t in self._graph.all_tasks():
            if t.status not in ("COMPLETED", "DELIVERED", "CANCELLED"):
                self._graph.reset_status(t.task_id, "PENDING")
        first = next((t for t in self._graph.all_tasks()
                      if t.status != "COMPLETED"), None)
        if first is not None:
            self._pr.set_stage(self.project_id, first.stage)
        self._logger.runtime("project_recovered", project_id=self.project_id,
                             resume_stage=first.stage if first else None)
        return first.stage if first else None

    # ---- 主运行循环 ----
    def run(self) -> Dict[str, Any]:
        if not self._pr.exists(self.project_id):
            self.create_project()
        else:
            self.recover()

        while True:
            ready = self._scheduler.next_ready()
            if not ready:
                if self._graph.has_failed():
                    self._graph.save(self._graph_path)
                    return self._summary("FAILED")
                if self._graph.is_complete():
                    break
                self._logger.error("scheduler_deadlock",
                                   error="无可调度任务且未全部完成/失败",
                                   project_id=self.project_id)
                self._graph.save(self._graph_path)
                return self._summary("DEADLOCK")

            for task in ready:
                result = self._dispatcher.execute(task.task_id)
                if result is None or not result.success:
                    self._logger.error("orchestration_branch_failed",
                                       error=str(result.messages) if result else "no result",
                                       project_id=self.project_id,
                                       task_id=task.task_id)
                    self._graph.save(self._graph_path)
                    return self._summary("FAILED")
                # 阶段推进（EXPORT 为终态，无后继）
                cur = self._state.current_stage(self.project_id)
                if task.stage == cur and cur != "EXPORT":
                    self._state.advance(self.project_id)

        self._pr.set_state(self.project_id, "COMPLETED")
        self._bus.publish(Event(
            EventType.PROJECT_FINISHED,
            {"project_id": self.project_id,
             "current_stage": self._state.current_stage(self.project_id)},
        ))
        self._graph.save(self._graph_path)
        return self._summary("COMPLETED")

    # ---- Professional Stage（Phase 5 §7：Parallel Fan-out → Fan-in）----
    def run_professional_stage(self, task_ids: List[str],
                               max_workers: Optional[int] = None,
                               max_retry: int = 1) -> Dict[str, Any]:
        """并行启动全部 Professional 任务并等待完成（Fan-out → Fan-in）。

        - 支持部分失败：单个 Agent 失败不影响其它 Agent
        - 失败任务按 max_retry 单独重跑（无需重新执行成功者，Phase 5 §8）
        - 检查点由调用方在 Fan-in 后统一保存（避免并发写同一 stage 文件）
        """
        from runtime.parallel import ParallelStageRunner  # 延迟导入避免环

        pending = [tid for tid in task_ids
                   if (t := self._graph.get_task(tid)) is not None
                   and t.status != "COMPLETED"]
        for tid in pending:
            task = self._graph.get_task(tid)
            if task.status == "PENDING":
                self._graph.update_status(tid, "READY")
            elif task.status != "READY":
                # FAILED / 残留中间态：恢复语义复位（绕过状态机，Phase 2 §8）
                self._graph.reset_status(tid, "READY")

        jobs = {tid: (lambda t=tid: self._dispatcher.execute(
            t, save_checkpoint=False)) for tid in pending}
        runner = ParallelStageRunner(max_workers=max_workers, max_retry=0)
        results = runner.run_once(jobs)  # Fan-out → Fan-in（等待全部完成）

        for _ in range(max(0, max_retry)):
            failed = sorted(t for t, r in results.items() if not r.success)
            if not failed:
                break
            for tid in failed:  # 只复位失败任务（其余不重跑）
                self._graph.reset_status(tid, "READY")
            self._logger.runtime("professional_retry",
                                 project_id=self.project_id,
                                 tasks=",".join(failed))
            results.update(runner.run_once({t: jobs[t] for t in failed}))

        self._graph.save(self._graph_path)
        return results

    # ---- 汇总 ----
    def _summary(self, status: str) -> Dict[str, Any]:
        cur = (self._state.current_stage(self.project_id)
               if self._pr.exists(self.project_id) else None)
        return {
            "project_id": self.project_id,
            "status": status,
            "current_stage": cur,
            "tasks": {t.task_id: t.status for t in self._graph.all_tasks()},
            "events": len(self._events),
            "checkpoints": self._checkpoint.list_checkpoints(self.project_id),
        }

    # 便于外部读取运行期事件（演示 / 测试）
    @property
    def events(self) -> List[Dict[str, Any]]:
        return self._events


__all__ = ["Orchestrator"]
