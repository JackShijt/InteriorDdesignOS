"""
Phase 3.5 / Phase 4 End-to-End Project Pipeline Runner（v1.0）

职责（§1）：只负责流程控制，禁止业务逻辑。
  Project 生命周期（§2） -> StageController（§3） -> Dispatcher（§4，经 Agent Registry §5）
  -> Task 生命周期（§6） -> Workspace 自动更新（§7） -> Checkpoint 自动恢复（§8）
  -> 统一事件流（§9）。

阶段顺序（§3 / Phase 4 §13）：
  INITIALIZATION -> INPUT_ANALYSIS -> ORIGINAL_MODEL -> DESIGN_SPEC
  Parser 完成后进入 Design；Design 完成后 Project 自动结束（Layout 暂不进入）。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime import REPO_ROOT, ensure_workspace
from runtime.message import Event, EventType
from runtime.config import load_runtime_config
from runtime.project_runtime import ProjectRuntime
from runtime.agent_registry import (AgentRegistry, PROFESSIONAL_AGENTS,
                                    build_runtime_registry)
from agents.orchestrator.orchestrator import Orchestrator
from agents.orchestrator.task_graph import TaskGraph

# 支持的阶段顺序（§3 / Phase 4 §13）：INITIALIZATION -> INPUT_ANALYSIS
# -> ORIGINAL_MODEL -> DESIGN_SPEC（DESIGN_SPEC 为终点，Layout 暂不进入）
SUPPORTED_STAGES = ["INITIALIZATION", "INPUT_ANALYSIS", "ORIGINAL_MODEL", "DESIGN_SPEC"]
TERMINAL_STAGE = "DESIGN_SPEC"
# Phase 5：专业深化为独立并行阶段（Layout 未实现，主链路暂不进入；
# 通过 run_professional() 以 Mock LayoutModel 驱动）
PROFESSIONAL_STAGE = "PROFESSIONAL_DEEPENING"

# Project 生命周期状态机（§2）：不得跳跃
PROJECT_TRANSITIONS: Dict[str, List[str]] = {
    "CREATED": ["INITIALIZING"],
    "INITIALIZING": ["RUNNING"],
    "RUNNING": ["WAITING", "COMPLETED", "FAILED", "CANCELLED"],
    "WAITING": ["RUNNING", "CANCELLED", "FAILED"],
    "COMPLETED": [],
    "FAILED": [],
    "CANCELLED": [],
}


class StageController:
    """Phase 3.5 §3 阶段顺序控制（INITIALIZATION -> ... -> DESIGN_SPEC）。"""

    def __init__(self, pr: ProjectRuntime, bus, logger):
        self._pr = pr
        self._bus = bus
        self._logger = logger

    def start(self, project_id: str) -> None:
        self._pr.set_stage(project_id, SUPPORTED_STAGES[0])

    def current(self, project_id: str) -> str:
        return self._pr.load(project_id)["current_stage"]

    def is_terminal(self, stage: str) -> bool:
        return stage == TERMINAL_STAGE

    def advance(self, project_id: str, stage: str) -> str:
        """推进阶段；已是终点阶段则保持不变（Parser 完成后自动结束，§3）。"""
        if stage == TERMINAL_STAGE:
            self._logger.runtime("stage_terminal", project_id=project_id, stage=stage)
            return stage
        idx = SUPPORTED_STAGES.index(stage)
        nxt = SUPPORTED_STAGES[idx + 1]
        self._pr.set_stage(project_id, nxt)
        return nxt

    def publish_started(self, project_id: str, stage: str) -> None:
        self._bus.publish(Event(EventType.STAGE_STARTED,
                               {"project_id": project_id, "stage": stage}))

    def publish_completed(self, project_id: str, stage: str) -> None:
        self._bus.publish(Event(EventType.STAGE_COMPLETED,
                               {"project_id": project_id, "stage": stage}))


class Pipeline:
    """Phase 3.5 Project Pipeline Runner（§1）。"""

    def __init__(self, project_id: str,
                 config: Optional[Dict[str, Any]] = None,
                 registry: Optional[AgentRegistry] = None,
                 workspace_root: Optional[Path] = None,
                 log_dir: Optional[Path] = None):
        self.config = config or load_runtime_config()
        self.project_id = project_id
        self.workspace_root = Path(workspace_root or self.config["workspace_root"])
        self.log_dir = Path(log_dir or (self.workspace_root / "logs"))

        # §5 统一 Agent 注册表
        self.agent_registry = registry or build_runtime_registry(
            workspace_root=self.workspace_root, log_dir=self.log_dir)

        # §1 调度 Orchestrator（复用其 Dispatcher / Checkpoint / EventBus / 日志）
        self._orch = Orchestrator(project_id, registry=self.agent_registry,
                                  workspace_root=self.workspace_root,
                                  log_dir=self.log_dir)
        self.bus = self._orch.event_bus
        self.logger = self._orch.logger
        self.pr = self._orch.project_runtime
        self.cm = self._orch.context_manager
        self.checkpoint = self._orch.checkpoint

        # 自定义本阶段任务图（仅 ORIGINAL_MODEL 具有 Agent 任务；其余阶段由 Pipeline 内部驱动，§3/§14）
        self.graph = TaskGraph()
        self._orch.task_graph = self.graph
        self.stage_controller = StageController(self.pr, self.bus, self.logger)
        # §4 Dispatcher 在任务成功后推进阶段（不写死，经回调）
        self._orch.dispatcher._stage_advancer = self._on_task_done

    # ---- 公开：创建 ----
    def create(self) -> Dict[str, Any]:
        if self.pr.exists(self.project_id):
            return self.pr.load(self.project_id)
        proj = self.pr.create(self.project_id, name=self.project_id, state="CREATED")
        self.bus.publish(Event(EventType.PROJECT_CREATED,
                               {"project_id": self.project_id, "state": "CREATED"}))
        self._save_workspace()
        return proj

    # ---- 公开：运行（Parser -> Design，§12 / §13）----
    def run(self, input_path: Optional[str] = None,
            requirement: Optional[str] = None) -> Dict[str, Any]:
        ensure_workspace()
        if not self.pr.exists(self.project_id):
            self.create()
        proj = self.pr.load(self.project_id)
        if proj["state"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return self._summary()

        # Project 生命周期：CREATED -> INITIALIZING -> RUNNING（§2）
        self._transition_project("INITIALIZING")
        self.bus.publish(Event(EventType.PROJECT_STARTED,
                               {"project_id": self.project_id}))
        self._transition_project("RUNNING")

        self._ensure_parser_task(input_path)
        self._ensure_design_task(requirement)

        # 驱动阶段（可恢复：从当前阶段继续，§8）
        for i, stage in enumerate(SUPPORTED_STAGES):
            cur = self.pr.load(self.project_id)["current_stage"]
            cur_idx = (SUPPORTED_STAGES.index(cur)
                       if cur in SUPPORTED_STAGES else 0)
            if i < cur_idx:
                continue  # 已完成的阶段跳过
            self._process_stage(stage)
            if self.pr.load(self.project_id)["state"] == "FAILED":
                break

        if self.pr.load(self.project_id)["state"] not in ("FAILED", "CANCELLED"):
            self._transition_project("COMPLETED")
        return self._summary()

    # ---- 公开：恢复（§8）----
    def resume(self) -> Dict[str, Any]:
        if not self.pr.exists(self.project_id):
            raise FileNotFoundError(f"Project 不存在：{self.project_id}")
        proj = self.pr.load(self.project_id)
        if proj["state"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return self._summary()
        # 恢复 TaskGraph
        gp = self._graph_path()
        if gp.exists():
            self.graph = TaskGraph.load(gp)
            self._orch.task_graph = self.graph
        # 恢复 Context：AgentContext 在 Dispatcher 派发时按任务重建（无状态）
        self.logger.runtime("pipeline_resumed", project_id=self.project_id,
                            current_stage=proj["current_stage"])
        return self.run()

    # ---- 公开：直接运行 Design Agent（§14，python main.py design）----
    def run_design(self, requirement: Optional[str] = None,
                   original_model_path: Optional[str] = None) -> Dict[str, Any]:
        """直接运行 Design Agent（跳过 Parser，需已有 OriginalModel）。

        典型场景：某原始模型（如 DWG 解析结果）已存在于 Workspace，
        仅想独立生成 DesignSpec。
        """
        ensure_workspace()
        if not self.pr.exists(self.project_id):
            self.create()
        proj = self.pr.load(self.project_id)
        if proj["state"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return self._summary()

        self._transition_project("INITIALIZING")
        self.bus.publish(Event(EventType.PROJECT_STARTED,
                               {"project_id": self.project_id}))
        self._transition_project("RUNNING")

        # 确保 OriginalModel 存在（提供则写入 Workspace，供 Design 读取）
        if original_model_path:
            om = json.loads(Path(original_model_path).read_text(encoding="utf-8"))
            out = self.pr.project_dir(self.project_id) / "original_model.json"
            out.write_text(json.dumps(om, ensure_ascii=False, indent=2),
                           encoding="utf-8")

        self._ensure_design_task(requirement)
        # 直接进入 DESIGN_SPEC 阶段
        self.pr.set_stage(self.project_id, "DESIGN_SPEC")
        self._process_stage("DESIGN_SPEC")

        if self.pr.load(self.project_id)["state"] not in ("FAILED", "CANCELLED"):
            self._transition_project("COMPLETED")
        return self._summary()

    # ---- 公开：并行专业深化（Phase 5 §7/§8/§10）----
    def run_professional(self, layout_path: Optional[str] = None,
                         disciplines: Optional[List[str]] = None
                         ) -> Dict[str, Any]:
        """Mock Workflow：LayoutModel → Parallel Professional Agents
        → Validator（聚合校验）→ Export。

        - layout_path：LayoutModel JSON；缺省使用项目内 layout_model.json，
          再缺省回退到 schemas/examples/LayoutModel.example.json（Mock）
        - disciplines：要启动的专业（缺省全部 8 个）
        """
        ensure_workspace()
        if not self.pr.exists(self.project_id):
            self.create()
        proj = self.pr.load(self.project_id)
        if proj["state"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return self._summary()

        self._transition_project("INITIALIZING")
        self.bus.publish(Event(EventType.PROJECT_STARTED,
                               {"project_id": self.project_id}))
        self._transition_project("RUNNING")

        layout_file = self._ensure_layout_model(layout_path)
        wanted = list(disciplines) if disciplines else list(PROFESSIONAL_AGENTS)
        self._ensure_professional_tasks(wanted, layout_file)

        # 进入并行阶段：Fan-out → Fan-in（Orchestrator §7 / Runtime §8）
        self.pr.set_stage(self.project_id, PROFESSIONAL_STAGE)
        self.stage_controller.publish_started(self.project_id, PROFESSIONAL_STAGE)
        self.logger.runtime("stage_started", project_id=self.project_id,
                            stage=PROFESSIONAL_STAGE,
                            disciplines=",".join(wanted))
        task_ids = [self._professional_task_id(d) for d in wanted]
        self._orch.run_professional_stage(
            task_ids,
            max_workers=self.config.get("professional_max_workers"),
            max_retry=int(self.config.get("max_retry", 2)) - 1)

        failed = sorted(d for d in wanted
                        if self.graph.get_task(
                            self._professional_task_id(d)).status != "COMPLETED")
        if failed:
            err = f"专业深化任务失败: {failed}"
            self.logger.error("professional_failed", error=err,
                              project_id=self.project_id)
            self._transition_project("FAILED")
            self._save_workspace()
            return self._summary()

        # Fan-in 后：Validator 聚合校验（Phase 5 §9）
        from professional.validator import load_and_validate_dir
        layout = json.loads(layout_file.read_text(encoding="utf-8"))
        prof_dir = self.pr.project_dir(self.project_id) / "professional"
        report = load_and_validate_dir(prof_dir, layout)
        report_path = self.pr.project_dir(self.project_id) \
            / "professional_validation_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        if not report["passed"]:
            self.logger.error("professional_validation_failed",
                              error=json.dumps(report["errors"],
                                               ensure_ascii=False),
                              project_id=self.project_id)
            self._transition_project("FAILED")
            self._save_workspace()
            return self._summary()

        # Export（Mock：输出清单，禁止 DWG / CAD）
        self._export_professional(prof_dir, report_path)
        self._save_professional_checkpoint(wanted)
        self.stage_controller.publish_completed(self.project_id,
                                                PROFESSIONAL_STAGE)
        self._save_workspace()
        self._transition_project("COMPLETED")
        summary = self._summary()
        summary["professional"] = {
            "disciplines": wanted,
            "validation_passed": True,
            "report": str(report_path),
        }
        return summary

    # ---- 内部：阶段处理 ----
    def _process_stage(self, stage: str) -> None:
        self.stage_controller.publish_started(self.project_id, stage)
        self.logger.runtime("stage_started", project_id=self.project_id, stage=stage)
        if stage == "ORIGINAL_MODEL":
            self._run_parser_task()
        elif stage == "DESIGN_SPEC":
            self._run_design_task()
        else:
            # INITIALIZATION / INPUT_ANALYSIS：Pipeline 内部阶段，无 Agent 任务（§3/§14）
            self.logger.runtime("stage_internal", project_id=self.project_id, stage=stage)
            # 内部阶段自行推进；Agent 阶段（ORIGINAL_MODEL/DESIGN_SPEC）由 Dispatcher 回调推进
            self.stage_controller.advance(self.project_id, stage)
        self.stage_controller.publish_completed(self.project_id, stage)
        self._save_workspace()

    def _run_parser_task(self) -> None:
        task_id = self._parser_task_id()
        task = self.graph.get_task(task_id)
        if task is not None and task.status == "COMPLETED":
            self.logger.runtime("parser_task_skipped", project_id=self.project_id,
                                task_id=task_id, reason="already COMPLETED")
            return
        last_err: Optional[str] = None
        for _ in range(1, int(self.config.get("max_retry", 2)) + 1):
            if self.graph.get_task(task_id).status == "FAILED":
                self.graph.reset_status(task_id, "READY")  # 重试前复位（§13.1）
            self.graph.update_status(task_id, "READY")
            result = self._orch.dispatcher.execute(task_id)
            if result.success:
                self._save_checkpoint()
                return
            last_err = "; ".join(result.messages)
        self.logger.error("parser_failed", error=last_err, project_id=self.project_id)
        self._transition_project("FAILED")
        self.bus.publish(Event(EventType.PROJECT_FAILED,
                               {"project_id": self.project_id, "error": last_err}))

    def _run_design_task(self) -> None:
        task_id = self._design_task_id()
        task = self.graph.get_task(task_id)
        if task is not None and task.status == "COMPLETED":
            self.logger.runtime("design_task_skipped", project_id=self.project_id,
                                task_id=task_id, reason="already COMPLETED")
            return
        last_err: Optional[str] = None
        for _ in range(1, int(self.config.get("max_retry", 2)) + 1):
            if self.graph.get_task(task_id).status == "FAILED":
                self.graph.reset_status(task_id, "READY")  # 重试前复位（§13.1）
            self.graph.update_status(task_id, "READY")
            result = self._orch.dispatcher.execute(task_id)
            if result.success:
                self._save_checkpoint()
                return
            last_err = "; ".join(result.messages)
        self.logger.error("design_failed", error=last_err, project_id=self.project_id)
        self._transition_project("FAILED")
        self.bus.publish(Event(EventType.PROJECT_FAILED,
                               {"project_id": self.project_id, "error": last_err}))

    def _on_task_done(self, project_id: str, stage: str) -> None:
        # §4 Dispatcher 任务成功后推进阶段（ORIGINAL_MODEL/DESIGN_SPEC 经回调推进，
        # DESIGN_SPEC 为终点保持不变）
        # Phase 5：PROFESSIONAL_DEEPENING 等非主链路阶段由 run_professional
        # 在 Fan-in 后统一收尾，不做逐任务推进
        if stage not in SUPPORTED_STAGES:
            return
        self.stage_controller.advance(project_id, stage)

    # ---- 内部：任务图 ----
    def _ensure_parser_task(self, input_path: Optional[str]) -> None:
        task_id = self._parser_task_id()
        if self.graph.get_task(task_id) is not None:
            return
        if input_path:
            path = Path(input_path)
        else:
            path = REPO_ROOT / "examples" / "input" / "sample_json" / "sample.json"
        self.graph.create_task(task_id=task_id, agent="parser", stage="ORIGINAL_MODEL",
                               dependencies=[], input_refs=[str(path)])
        self.graph.save(self._graph_path())

    def _ensure_design_task(self, requirement: Optional[str]) -> None:
        task_id = self._design_task_id()
        if self.graph.get_task(task_id) is not None:
            return
        # Design 依赖 OriginalModel（若 Parser 任务存在则建立依赖；直接运行设计时不依赖）
        deps = [self._parser_task_id()] if self.graph.get_task(self._parser_task_id()) else []
        self.graph.create_task(task_id=task_id, agent="design", stage="DESIGN_SPEC",
                               dependencies=deps,
                               input_refs=[], parameters={"requirement": requirement or ""})
        self.graph.save(self._graph_path())

    def _parser_task_id(self) -> str:
        return f"original_model-{self.project_id}"

    def _design_task_id(self) -> str:
        return f"design-{self.project_id}"

    # ---- Phase 5 内部：专业深化任务图 ----
    def _ensure_layout_model(self, layout_path: Optional[str]) -> Path:
        """确保布局模型可用：参数 > 项目内 layout_model.json >
        示例 LayoutModel（Mock 回退）。返回最终路径。"""
        if layout_path:
            return Path(layout_path)
        proj_file = self.pr.project_dir(self.project_id) / "layout_model.json"
        if proj_file.exists():
            return proj_file
        from runtime import REPO_ROOT as _ROOT
        example = _ROOT / "schemas" / "examples" / "LayoutModel.example.json"
        data = json.loads(example.read_text(encoding="utf-8"))
        proj_file.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        self.logger.runtime("layout_model_fallback", project_id=self.project_id,
                            path=str(example))
        return proj_file

    def _ensure_professional_tasks(self, disciplines: List[str],
                                   layout_path: Path) -> None:
        for d in disciplines:
            task_id = self._professional_task_id(d)
            if self.graph.get_task(task_id) is not None:
                continue
            self.graph.create_task(
                task_id=task_id, agent=d, stage=PROFESSIONAL_STAGE,
                dependencies=[], input_refs=[str(layout_path)],
                parameters={"layout_path": str(layout_path)})
        self.graph.save(self._graph_path())

    def _professional_task_id(self, discipline: str) -> str:
        return f"professional-{discipline}-{self.project_id}"

    def _export_professional(self, prof_dir: Path, report_path: Path) -> None:
        models = sorted(p.name for p in prof_dir.glob("*_model.json"))
        manifest = {
            "version": "v1",
            "project_id": self.project_id,
            "stage": PROFESSIONAL_STAGE,
            "generated_at": datetime.now().isoformat(),
            "models": models,
            "validation_report": report_path.name,
        }
        out = self.pr.project_dir(self.project_id) \
            / "professional_export_manifest.json"
        out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    def _save_professional_checkpoint(self, disciplines: List[str]) -> None:
        cp = self.pr.project_dir(self.project_id) \
            / "checkpoint_professional_v1.json"
        payload = {
            "version": "v1",
            "project_id": self.project_id,
            "stage": PROFESSIONAL_STAGE,
            "state": "COMPLETED",
            "disciplines": disciplines,
            "task_status": {
                self._professional_task_id(d): self.graph.get_task(
                    self._professional_task_id(d)).status for d in disciplines},
            "updated_at": datetime.now().isoformat(),
        }
        cp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        self.bus.publish(Event(EventType.CHECKPOINT_SAVED,
                               {"project_id": self.project_id, "path": str(cp)}))

    def _graph_path(self) -> Path:
        return self.pr.project_dir(self.project_id) / "task_graph.json"

    # ---- 内部：Project 生命周期 ----
    def _transition_project(self, target: str) -> None:
        cur = self.pr.load(self.project_id)["state"]
        allowed = PROJECT_TRANSITIONS.get(cur, [])
        if target not in allowed:
            self.logger.error("project_transition_skipped",
                              error=f"不允许的状态转移: {cur} -> {target}",
                              current=cur, target=target, project_id=self.project_id)
            return
        self.pr.set_state(self.project_id, target)
        self.logger.runtime("project_state_changed", project_id=self.project_id,
                            from_state=cur, to_state=target)
        if target == "COMPLETED":
            self.bus.publish(Event(EventType.PROJECT_COMPLETED,
                                   {"project_id": self.project_id}))
        elif target == "FAILED":
            self.bus.publish(Event(EventType.PROJECT_FAILED,
                                   {"project_id": self.project_id}))

    # ---- 内部：Workspace / Checkpoint（§7 / §8）----
    def _save_workspace(self) -> None:
        if not self.config.get("auto_save", True):
            return
        self.pr.update(self.project_id)
        self.graph.save(self._graph_path())
        self.bus.publish(Event(EventType.WORKSPACE_UPDATED,
                               {"project_id": self.project_id,
                                "files": ["project.json", "task_graph.json",
                                          "original_model.json", "design_spec.json"]}))

    def _save_checkpoint(self) -> None:
        cp = self.pr.project_dir(self.project_id) / "checkpoint_pipeline_v1.json"
        payload = {
            "version": "v1",
            "project_id": self.project_id,
            "state": self.pr.load(self.project_id)["state"],
            "current_stage": self.pr.load(self.project_id)["current_stage"],
            "task_status": {tid: t.status for tid, t in self.graph.tasks.items()},
            "updated_at": datetime.now().isoformat(),
        }
        cp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        self.bus.publish(Event(EventType.CHECKPOINT_SAVED,
                               {"project_id": self.project_id, "path": str(cp)}))

    # ---- 汇总 ----
    def _summary(self) -> Dict[str, Any]:
        proj = self.pr.load(self.project_id)
        tasks = {tid: t.status for tid, t in self.graph.tasks.items()}
        return {
            "project_id": self.project_id,
            "status": proj["state"],
            "current_stage": proj["current_stage"],
            "tasks": tasks,
            "events": [ev["type"] for ev in self.events],
        }

    @property
    def events(self) -> List[Dict[str, Any]]:
        return self._orch.events


__all__ = ["SUPPORTED_STAGES", "TERMINAL_STAGE", "PROFESSIONAL_STAGE",
           "StageController", "Pipeline"]
