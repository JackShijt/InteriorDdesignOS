"""
InteriorDesignOS · BaseProfessionalAgent（Phase 5 §3 / Phase 5.1 重构）

所有 Professional Agent 的统一基类。统一提供：
  load_layout() / load_design_spec() / validate_input()
  generate_model() / publish_result() / export_model() / quality_check()

Phase 5.1 架构约束（TASK_005_1）：
- Professional 只依赖 core/ · models/ · schemas/（禁止 import runtime / orchestrator）
- Agent 通过 AgentContext 获取全部输入（不自行查找文件、无硬编码路径）
- Agent 不直接读写 Workspace 文件：所有输出经 ArtifactManager
- 数据流：Agent -> ProfessionalModel(dataclass) -> ArtifactManager -> workspace

业务约束（Phase 5 §一，保持不变）：
- 只能读取 LayoutModel（SSOT），返回深拷贝，禁止修改
- 可以读取 DesignSpec（同样只读）
- 不允许直接操作 DWG / 调用 AutoCAD MCP / 调用外部 AI

子类只需：
- 声明 discipline 与 rule_engine_class（专业规则引擎）
- 禁止重复实现公共逻辑（PROJECT_RULES：SOLID / DRY）
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional

from core import PROJECTS_DIR
from core.artifact import ArtifactManager
from core.context import AgentContext, BaseAgent, Result, make_metadata
from core.logging import build_logger
from professional.base.professional_model import BaseProfessionalModel
from professional.base.rule_engine import BaseRuleEngine


class ProfessionalError(Exception):
    """Professional Framework 统一异常基类。"""


class ProfessionalInputError(ProfessionalError):
    """输入（LayoutModel / DesignSpec）缺失或非法。"""


class BaseProfessionalAgent(BaseAgent):
    """专业深化 Agent 统一基类（Phase 5 §3 / Phase 5.1）。"""

    # 子类声明：小写专业名（同时作为 agent_name），如 "electrical"
    discipline: str = "base"
    version: str = "1.1"

    # 子类声明：专业规则引擎类（Phase 5.1 §9：Agent 管流程，RuleEngine 管规则）
    rule_engine_class: Optional[type] = None

    # LayoutModel 必备的输入键（validate_input 使用）
    REQUIRED_LAYOUT_KEYS = ("metadata", "version", "rooms", "walls")

    def __init__(self, workspace_root: Optional[Path] = None,
                 log_dir: Optional[Path] = None,
                 logger: Any = None,
                 artifact_manager: Optional[ArtifactManager] = None):
        self.agent_name = self.discipline
        self._workspace_root = Path(workspace_root) if workspace_root else None
        self._log = build_logger(log_dir, logger)
        self._artifact_manager = artifact_manager
        self._rule_engine: Optional[BaseRuleEngine] = (
            self.rule_engine_class() if self.rule_engine_class else None)

    # ================= 框架接口 =================
    def run(self, context: AgentContext) -> Result:
        """供上层调度（框架安全：异常转 Result）。

        流程（Phase 5.1 §10）：
            validate_input -> generate_model -> publish_result
        """
        try:
            layout = self.load_layout(context)
            design_spec = self.load_design_spec(context)
            self.validate_input(layout)
            model = self.generate_model(layout, design_spec,
                                        context.project_id, context.task_id)
            path = self.publish_result(model, context)
            context.outputs[f"{self.discipline}_model"] = str(path)
            return Result(
                success=True,
                output_model=model,
                messages=[f"[{self.discipline}] ProfessionalModel 已生成：{path.name}"],
                quality=model["quality"],
                next_tasks=[],
            )
        except Exception as exc:  # 框架内不向上抛，统一以 Result 表达失败
            msg = str(exc) or f"{self.discipline} agent 未知错误"
            self._log.error("professional_failed", error=msg,
                            project_id=getattr(context, "project_id", "?"),
                            agent=self.discipline,
                            task_id=getattr(context, "task_id", "?"))
            return Result(success=False, messages=[msg], quality={},
                          next_tasks=[])

    # ================= 公共步骤 =================
    def load_layout(self, context: AgentContext) -> Dict[str, Any]:
        """读取 LayoutModel（SSOT，只读：返回深拷贝）。

        全部数据来自 Context（Phase 5.1 §四），解析顺序：
        inputs.layout(dict) → inputs.layout_path → parameters.layout_path →
        input_refs(*.json) → <context.workspace 或注入根>/layout_model.json。
        """
        inline = context.inputs.get("layout")
        if isinstance(inline, dict):
            return copy.deepcopy(inline)
        p = context.inputs.get("layout_path") or \
            context.parameters.get("layout_path")
        if p:
            return self._read_json(Path(p))
        for ref in (context.input_refs or []):
            if str(ref).lower().endswith(".json"):
                return self._read_json(Path(ref))
        proj = self._project_dir(context) / "layout_model.json"
        if proj.exists():
            return self._read_json(proj)
        raise ProfessionalInputError(
            f"[{self.discipline}] 缺少 LayoutModel：请在 inputs.layout / "
            "inputs.layout_path / parameters.layout_path / input_refs 提供，"
            "或在项目 Workspace 放置 layout_model.json")

    def load_design_spec(self, context: AgentContext) -> Optional[Dict[str, Any]]:
        """读取 DesignSpec（可选，只读：返回深拷贝；缺失返回 None）。"""
        inline = context.inputs.get("design_spec")
        if isinstance(inline, dict):
            return copy.deepcopy(inline)
        p = context.inputs.get("design_spec_path") or \
            context.parameters.get("design_spec_path")
        if p:
            return self._read_json(Path(p))
        proj = self._project_dir(context) / "design_spec.json"
        if proj.exists():
            return self._read_json(proj)
        return None

    def validate_input(self, layout: Dict[str, Any]) -> None:
        """校验 LayoutModel 输入完整性（缺键 / 缺版本即失败）。"""
        if not isinstance(layout, dict):
            raise ProfessionalInputError(
                f"[{self.discipline}] LayoutModel 必须是 JSON 对象")
        missing = [k for k in self.REQUIRED_LAYOUT_KEYS if k not in layout]
        if missing:
            raise ProfessionalInputError(
                f"[{self.discipline}] LayoutModel 缺少必备字段: {missing}")
        version = (layout.get("version") or {}).get("model_version")
        if not version:
            raise ProfessionalInputError(
                f"[{self.discipline}] LayoutModel 缺少 version.model_version")

    def generate_model(self, layout: Dict[str, Any],
                       design_spec: Optional[Dict[str, Any]],
                       project_id: str, task_id: str) -> Dict[str, Any]:
        """组装 ProfessionalModel（公共流程；专业规则在 RuleEngine）。"""
        model_obj = self._build_model(layout, design_spec)
        model_obj.layout_model_version = layout["version"]["model_version"]
        model_obj.quality = self.quality_check(model_obj)
        model_obj.metadata = make_metadata(project_id, self.discipline, task_id,
                                           "COMPLETED", model_obj.quality)
        model = model_obj.to_dict()
        # Schema 校验（失败抛 ProfessionalValidationError，不得落盘）
        from professional.validator import assert_model_valid
        assert_model_valid(model)
        self._log.runtime("professional_model_generated", project_id=project_id,
                          agent=self.discipline, task_id=task_id,
                          objects=len(model["objects"]))
        return model

    def publish_result(self, model: Dict[str, Any],
                       context: AgentContext) -> Path:
        """发布 ProfessionalModel（Phase 5.1 §6）：

            Agent -> ProfessionalModel -> ArtifactManager -> workspace
        """
        manager = self._get_artifact_manager(context)
        path = manager.save(f"professional/{self.discipline}_model.json", model)
        self._log.runtime("professional_model_exported",
                          project_id=context.project_id,
                          agent=self.discipline, path=str(path))
        return path

    def export_model(self, model: Dict[str, Any], project_id: str) -> Path:
        """（兼容接口）按 project_id 导出模型；内部同样经 ArtifactManager。"""
        ctx = AgentContext(project_id=project_id, task_id="manual-export",
                           agent_name=self.discipline)
        return self.publish_result(model, ctx)

    def quality_check(self, model_obj: BaseProfessionalModel) -> Dict[str, Any]:
        """确定性质量评估（无 LLM，Mock 阶段）。"""
        count = model_obj.object_count()
        score = 60 + min(count * 3, 35) if count else 40
        return {
            "confidence": round(min(score, 95) / 100.0, 2),
            "quality_score": min(score, 95),
            "validation_passed": count > 0,
        }

    # ================= 子类扩展点 =================
    def _build_model(self, layout: Dict[str, Any],
                     design_spec: Optional[Dict[str, Any]]
                     ) -> BaseProfessionalModel:
        """默认委托 RuleEngine 生成模型（Phase 5.1 §9）。

        Agent 负责流程；专业规则全部在 rule_engine_class 中。
        """
        if self._rule_engine is None:
            raise ProfessionalError(
                f"[{self.discipline}] 未声明 rule_engine_class，无法生成模型")
        return self._rule_engine.build(layout, design_spec)

    def capabilities(self) -> list[str]:
        return [f"professional:{self.discipline}"]

    # ================= 内部工具 =================
    def _get_artifact_manager(self, context: AgentContext) -> ArtifactManager:
        if self._artifact_manager is not None:
            return self._artifact_manager
        return ArtifactManager(self._project_dir(context))

    def _read_json(self, path: Path) -> Dict[str, Any]:
        """读取 JSON 并返回深拷贝（保证 SSOT 只读）。"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return copy.deepcopy(data)

    def _project_dir(self, context: AgentContext) -> Path:
        """解析项目工作区：context.workspace → 注入的 workspace_root → 默认。

        context.workspace 语义 = 项目工作区目录（workspace/projects/<pid>）。
        """
        if context.workspace is not None:
            d = Path(context.workspace)
        elif self._workspace_root:
            d = self._workspace_root / "projects" / context.project_id
        else:
            d = PROJECTS_DIR / context.project_id
        d.mkdir(parents=True, exist_ok=True)
        return d


__all__ = [
    "BaseProfessionalAgent", "ProfessionalError", "ProfessionalInputError",
]
