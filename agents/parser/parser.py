"""
InteriorDesignOS · Parser Agent（Phase 3 主入口）

完整闭环：
  输入（DWG / PDF / 图片 / 用户信息）
    ↓ 加载 (Input Loader)
    ↓ 识别 (Input Detector)
    ↓ 归一化 (Normalizer)
    ↓ 建模 (OriginalModel Builder)
    ↓ 校验 (Schema Validation)
    ↓ 落盘 (Workspace: original_model.json v1)
    ↓ 检查点 (Checkpoint: checkpoint_parser_v1.json)
    ↓ 返回 Result

Parser 不负责设计 / CAD 绘图（§14），只负责把输入解析成统一数据模型。

入口：
  - ParserAgent.run(context)        # 供 Dispatcher / Orchestrator 调度（框架安全：异常转 Result）
  - ParserAgent.process_file(...)   # 独立运行（异常会向上抛出，便于直接调用方处理）
  - run_parser(input_path, ...)      # 便捷函数
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime import PROJECTS_DIR, ensure_workspace
from runtime.logger import UnifiedLogger
from runtime.project_runtime import ProjectRuntime
from agents.orchestrator.agent import AgentContext, BaseAgent, Result
from agents.parser.exceptions import FatalError, to_orchestrator_error
from agents.parser.input_detector import InputType
from agents.parser.input_loader import load_input
from agents.parser.model_builder import build_original_model
from agents.parser.normalizer import normalize
from agents.parser.result_builder import build_result
from agents.parser.validator import assert_valid


class ParserAgent(BaseAgent):
    """系统入口 Agent：把输入解析为 OriginalModel。"""

    agent_name = "parser"

    def __init__(self, workspace_root: Optional[Path] = None,
                 log_dir: Optional[Path] = None):
        self._workspace_root = Path(workspace_root) if workspace_root else None
        self._log = UnifiedLogger(log_dir)

    # ---- 框架接口：供 Dispatcher / Orchestrator 调度 ----
    def run(self, context: AgentContext) -> Result:
        try:
            input_path = self._resolve_input(context)
            return self._process(input_path, context.project_id, context.task_id)
        except Exception as exc:  # 框架内不向上抛，统一以 Result 表达失败
            wrapped = to_orchestrator_error(exc)
            self._log.error("parser_failed", error=str(wrapped),
                            project_id=context.project_id, agent="parser",
                            task_id=context.task_id)
            return Result(success=False, messages=[str(wrapped)],
                          quality={}, next_tasks=[])

    # ---- 独立运行入口：异常向上抛出（供直接调用方 / 测试处理）----
    def process_file(self, input_path, project_id: Optional[str] = None,
                     task_id: Optional[str] = None) -> Result:
        p = Path(input_path)
        project_id = project_id or p.stem or "parser_cli"
        task_id = task_id or f"parser-{project_id}"
        result = self._process(p, project_id, task_id)  # 可能抛 ValidationError / FatalError
        self._sync_project(project_id)
        return result

    # ---- 核心流程（异常向上传播；成功返回 Result）----
    def _process(self, input_path: Path, project_id: str, task_id: str) -> Result:
        self._log.runtime("parser_started", project_id=project_id, agent="parser",
                          task_id=task_id, input=str(input_path))

        # 1) 加载
        loaded = load_input(input_path)
        self._log.runtime("input_loaded", project_id=project_id, agent="parser",
                          task_id=task_id, size=loaded.size_bytes,
                          mime=loaded.mime_type, hash=loaded.file_hash[:12])

        # 2) 识别类型
        itype = loaded.input_type
        self._log.runtime("input_type", project_id=project_id, agent="parser",
                          task_id=task_id, input_type=itype.value)

        # 3) 归一化
        ctx = normalize(loaded)

        # 4) 建模 OriginalModel
        hints = ctx.raw_json if itype is InputType.TEXT else None
        quality = self._assess_quality(itype, hints)
        model = build_original_model(
            project_id=project_id, task_id=task_id,
            input_type=itype, quality=quality, hints=hints,
        )

        # 5) Schema 校验（失败抛 ValidationError，不得继续执行）
        self._log.runtime("schema_validation", project_id=project_id, agent="parser",
                          task_id=task_id)
        assert_valid(model)
        self._log.runtime("schema_validation_ok", project_id=project_id, agent="parser",
                          task_id=task_id)

        # 6) 落盘 Workspace
        self._save_workspace(project_id, model)

        # 7) 检查点
        self._save_checkpoint(project_id, task_id, model)

        # 8) 返回统一 Result
        self._log.runtime("parser_finished", project_id=project_id, agent="parser",
                          task_id=task_id, success=True)
        return build_result(model, quality, messages=[f"输入类型: {itype.value}"])

    # ---- 辅助 ----
    def _resolve_input(self, context: AgentContext) -> Path:
        if context.input_refs:
            return Path(context.input_refs[0])
        path = context.parameters.get("input_path")
        if path:
            return Path(path)
        raise FatalError("Parser 缺少输入：input_refs / parameters.input_path 均为空")

    def _assess_quality(self, itype: InputType, hints: Any) -> Dict[str, Any]:
        """占位质量评估（无真实几何提取，置信度较低，诚实标注）。"""
        has_geo = isinstance(hints, dict) and any(
            isinstance(hints.get(k), list) and hints.get(k)
            for k in ("walls", "doors", "windows", "rooms")
        )
        if has_geo:
            confidence, score = 0.6, 60
        elif itype is InputType.UNKNOWN:
            confidence, score = 0.1, 10
        else:
            confidence, score = 0.3, 30
        return {"confidence": confidence, "quality_score": score,
                "validation_passed": True}

    def _project_dir(self, project_id: str) -> Path:
        if self._workspace_root:
            d = self._workspace_root / "projects" / project_id
        else:
            d = PROJECTS_DIR / project_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_workspace(self, project_id: str, model: Dict[str, Any]) -> None:
        ensure_workspace()
        out = self._project_dir(project_id) / "original_model.json"
        out.write_text(json.dumps(model, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        self._log.runtime("workspace_saved", project_id=project_id, agent="parser",
                          path=str(out), version="v1")

    def _save_checkpoint(self, project_id: str, task_id: str,
                         model: Dict[str, Any]) -> None:
        cp = self._project_dir(project_id) / "checkpoint_parser_v1.json"
        payload = {
            "version": "v1",
            "agent": "parser",
            "project_id": project_id,
            "task_id": task_id,
            "stage": "ORIGINAL_MODEL",
            "original_model": model,
            "task_status": {"parser": "COMPLETED"},
            "project_status": {"stage": "ORIGINAL_MODEL", "state": "COMPLETED"},
        }
        cp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        self._log.runtime("checkpoint_saved", project_id=project_id, agent="parser",
                          path=str(cp), checkpoint="checkpoint_parser_v1.json")

    def _sync_project(self, project_id: str) -> None:
        """独立运行模式下同步 Project 状态（框架模式下由 Orchestrator 负责）。"""
        try:
            pr = ProjectRuntime(self._workspace_root)
            if not pr.exists(project_id):
                pr.create(project_id, project_id)
            pr.set_stage(project_id, "ORIGINAL_MODEL")
            pr.set_state(project_id, "COMPLETED")
        except Exception:
            # 不阻塞解析主流程
            pass


def run_parser(input_path, project_id: Optional[str] = None,
               task_id: Optional[str] = None,
               workspace_root: Optional[Path] = None,
               log_dir: Optional[Path] = None) -> Result:
    """便捷函数：独立运行 Parser（Phase 3「Parser 可独立运行」）。"""
    agent = ParserAgent(workspace_root=workspace_root, log_dir=log_dir)
    return agent.process_file(input_path, project_id=project_id, task_id=task_id)


__all__ = ["ParserAgent", "run_parser"]
