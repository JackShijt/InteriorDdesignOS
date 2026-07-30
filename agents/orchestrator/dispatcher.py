"""
InteriorDesignOS · Dispatcher

本模块遵守 PROJECT_RULES.md 的最高约束。

分发器（Phase 2 §6 / PROJECT_RULES §2.3、§4.2）：
- 不负责业务
- 仅负责：根据 TaskGraph 寻找 Ready Task → 调用对应 Agent → 收集结果 → 更新状态
- 所有 Agent 调用须经 Dispatcher（禁止 Agent 之间直接调用）
- 执行过程发布事件；异常统一经 error_handler 归一

执行流程（单任务）：
  READY → RUNNING → (Agent.run) → COMPLETED / FAILED
  成功后保存检查点（Checkpoint），再发布 TaskFinished
"""

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from runtime.event_bus import EventBus
from runtime.logger import UnifiedLogger
from runtime.message import Event, EventType
from agents.orchestrator.task_graph import TaskGraph
from agents.orchestrator.agent import AgentContext, AgentRegistry, Result
from agents.orchestrator.context_manager import ContextManager
from agents.orchestrator.checkpoint import Checkpoint
from agents.orchestrator.error_handler import (
    FatalError, ValidationError, to_orchestrator_error,
)


class Dispatcher:
    """任务分发执行器。"""

    def __init__(self, project_id: str, task_graph: TaskGraph,
                 registry: AgentRegistry, context_manager: ContextManager,
                 checkpoint: Checkpoint, event_bus: EventBus, logger: UnifiedLogger,
                 stage_advancer: Optional[Callable[[str, str], None]] = None):
        self._project_id = project_id
        self._graph = task_graph
        self._registry = registry
        self._cm = context_manager
        self._checkpoint = checkpoint
        self._bus = event_bus
        self._logger = logger
        # 可选：阶段推进回调（Phase 3.5 §4：Dispatcher 在任务成功后推进阶段）
        self._stage_advancer = stage_advancer
        # 可选：阶段 -> schema 路径（用于产出校验，PROJECT_RULES §6.3）
        self.schema_map: Dict[str, str] = {}

    def execute(self, task_id: str, save_checkpoint: bool = True) -> Result:
        """执行单任务。

        save_checkpoint=False 用于并行阶段（Phase 5 §8）：多个任务共享同一
        stage 检查点文件，禁止并发写入；由调用方在 Fan-in 后统一保存。
        """
        task = self._graph.get_task(task_id)
        if task is None:
            raise FatalError(f"任务不存在: {task_id}")

        # READY -> RUNNING
        self._graph.update_status(task_id, "RUNNING")
        self._bus.publish(Event(
            EventType.TASK_STARTED,
            {"project_id": self._project_id, "task_id": task_id,
             "agent": task.agent, "stage": task.stage},
        ))
        self._logger.agent("task_started", agent=task.agent, task_id=task_id,
                           project_id=self._project_id, stage=task.stage)

        # 取 Agent（必须经过注册表；禁止直接调用）
        agent = self._registry.get(task.agent)
        if agent is None:
            return self._fail(task_id, task,
                              FatalError(f"未注册 Agent: {task.agent}"))

        context = AgentContext(
            project_id=self._project_id,
            task_id=task_id,
            stage=task.stage,
            context_manager=self._cm,
            logger=self._logger,
            event_bus=self._bus,
            input_refs=task.input_refs or [],
            parameters=task.parameters or {},
        )

        # 执行并归一异常
        try:
            result = agent.run(context)
            if not isinstance(result, Result):
                raise ValidationError(
                    f"Agent {task.agent} 未返回 Result 对象（违反 Phase 2 §13）")
            self._maybe_validate(task.stage, result.output_model)
        except Exception as e:  # 统一异常归一
            oe = to_orchestrator_error(e)
            return self._fail(task_id, task, oe)

        # Agent 显式返回失败：归入 FAILED（不写 COMPLETED）
        if not result.success:
            return self._fail(
                task_id, task,
                FatalError("Agent 返回 success=False: " + "; ".join(result.messages)))

        # 成功：保存检查点（并行阶段由调用方在 Fan-in 后统一保存）
        if save_checkpoint:
            if result.success and result.output_model is not None:
                path = self._checkpoint.save_stage(
                    self._project_id, task.stage, result.output_model)
                if path is not None:
                    self._graph.update_task(task_id, result_ref=str(path))
            self._checkpoint.save_project(self._project_id)

        # 任务状态机：RUNNING -> VALIDATING -> COMPLETED（PROJECT_RULES §13.1）
        self._graph.update_status(task_id, "VALIDATING")
        self._graph.update_status(task_id, "COMPLETED")
        # 事件（Phase 3.5 §9：所有事件经过 EventBus）
        self._bus.publish(Event(
            EventType.TASK_FINISHED,
            {"project_id": self._project_id, "task_id": task_id,
             "agent": task.agent, "stage": task.stage,
             "quality": result.quality},
        ))
        self._bus.publish(Event(
            EventType.TASK_COMPLETED,
            {"project_id": self._project_id, "task_id": task_id,
             "agent": task.agent, "stage": task.stage,
             "quality": result.quality},
        ))
        # Phase 3.5 §4：Dispatcher 任务成功后推进阶段（不写死，经回调）
        if self._stage_advancer:
            try:
                self._stage_advancer(self._project_id, task.stage)
            except Exception as e:  # 推进失败不应吞掉任务成功
                self._logger.error("stage_advance_failed", error=str(e),
                                   project_id=self._project_id, stage=task.stage)
        self._logger.agent("task_finished", agent=task.agent, task_id=task_id,
                           project_id=self._project_id, stage=task.stage)
        return result

    # ---- 内部 ----
    def _fail(self, task_id: str, task, err: Exception) -> Result:
        self._graph.update_status(task_id, "FAILED")
        self._logger.error("task_failed", error=err,
                           project_id=self._project_id, agent=task.agent,
                           task_id=task_id, stage=task.stage)
        self._bus.publish(Event(
            EventType.TASK_FAILED,
            {"project_id": self._project_id, "task_id": task_id,
             "agent": task.agent, "stage": task.stage,
             "error_category": getattr(err, "category", "FATAL"),
             "error": str(err)},
        ))
        return Result(success=False, messages=[str(err)])

    def _maybe_validate(self, stage: str, model: Optional[Dict[str, Any]]) -> None:
        schema_path = self.schema_map.get(stage)
        if not schema_path or model is None:
            return
        try:
            import json
            from jsonschema import Draft202012Validator
            from referencing import Registry, Resource
            # 轻量跨文件 $ref 解析：扫描 schemas 根目录构建 Registry
            from pathlib import Path as _P
            from scripts.validate_schema import build_registry, schemas_root_of
            registry = build_registry(schemas_root_of(_P(schema_path)))
            schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema, registry=registry)
            errors = sorted(validator.iter_errors(model), key=lambda e: list(e.path))
            if errors:
                msgs = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors]
                raise ValidationError(f"产出校验失败[{stage}]: " + "; ".join(msgs))
        except ImportError:
            self._logger.error("schema_validation_skipped",
                               error="jsonschema/referencing 不可用",
                               project_id=self._project_id, stage=stage)
        except ValidationError:
            raise
        except Exception as e:
            # 校验框架自身异常不应中断流程，仅记录
            self._logger.error("schema_validation_error", error=e,
                               project_id=self._project_id, stage=stage)


__all__ = ["Dispatcher"]
