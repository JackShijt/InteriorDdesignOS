"""
InteriorDesignOS · Design Agent（Phase 4 主入口）

完整闭环：
  用户需求 + OriginalModel
    ↓ 解析需求 (Requirement Parser)
    ↓ 提取约束 (Constraint Parser)
    ↓ 风格规划 (Style Planner)
    ↓ 预算规划 (Budget Planner)
    ↓ 家庭分析 (Family Analyzer)
    ↓ 材料规划 (Material Planner)
    ↓ 组装 (DesignSpec)
    ↓ 校验 (Schema Validation: design_spec.schema.json)
    ↓ 落盘 (Workspace: design_spec.json v1)
    ↓ 检查点 (Checkpoint: checkpoint_design_v1.json)
    ↓ 返回 Result

Design Agent 不负责布局 / 几何 / 绘图 / CAD（§17）：
它只把「用户想要什么 + 空间允许什么」固化为统一的 DesignSpec，
作为下游 LayoutModel 的唯一设计依据（SSOT）。

入口：
  - DesignAgent.run(context)        # 供 Dispatcher / Orchestrator 调度（框架安全：异常转 Result）
  - DesignAgent.generate(...)       # 独立运行（异常会向上抛出，便于直接调用方 / 测试处理）
  - run_design(...)                  # 便捷函数
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime import PROJECTS_DIR, ensure_workspace
from runtime.logger import UnifiedLogger
from agents.orchestrator.agent import AgentContext, BaseAgent, Result, make_metadata
from agents.design.budget_planner import plan_budget
from agents.design.constraint_parser import parse_constraints
from agents.design.exceptions import DesignError, ValidationError
from agents.design.family_analyzer import analyze_family
from agents.design.material_planner import plan_materials
from agents.design.requirement_parser import parse_requirement
from agents.design.result_builder import build_result
from agents.design.style_planner import plan_style
from agents.design.validator import assert_valid


class DesignAgent(BaseAgent):
    """把用户需求 + OriginalModel 转换为统一 DesignSpec。"""

    agent_name = "design"

    def __init__(self, workspace_root: Optional[Path] = None,
                 log_dir: Optional[Path] = None):
        self._workspace_root = Path(workspace_root) if workspace_root else None
        self._log = UnifiedLogger(log_dir)

    # ---- 框架接口：供 Dispatcher / Orchestrator 调度 ----
    def run(self, context: AgentContext) -> Result:
        try:
            original_model = self._resolve_original_model(context)
            requirement = self._resolve_requirement(context)
            return self.generate(original_model, requirement,
                                 context.project_id, context.task_id)
        except Exception as exc:  # 框架内不向上抛，统一以 Result 表达失败
            msg = str(exc) if exc else "Design Agent 未知错误"
            self._log.error("design_failed", error=msg,
                            project_id=getattr(context, "project_id", "?"),
                            agent="design",
                            task_id=getattr(context, "task_id", "?"))
            return Result(success=False, messages=[msg],
                          quality={}, next_tasks=[])

    # ---- 独立运行入口：异常向上抛出（供直接调用方 / 测试处理）----
    def generate(self, original_model: Dict[str, Any], requirement: str,
                 project_id: str, task_id: str,
                 save: bool = True) -> Result:
        """组装并校验 DesignSpec；save=True 时落盘 Workspace / Checkpoint。

        校验失败抛出 ValidationError（供测试断言）；正常返回 Result(success=True)。
        """
        self._log.runtime("design_started", project_id=project_id, agent="design",
                          task_id=task_id)
        spec = self.assemble(original_model, requirement, project_id, task_id)
        # Schema 校验（失败抛 ValidationError，不得继续落盘）
        assert_valid(spec)
        self._log.runtime("schema_validation_ok", project_id=project_id,
                          agent="design", task_id=task_id)
        if save:
            self._save_workspace(project_id, spec)
            self._save_checkpoint(project_id, task_id, spec)
        quality = self._assess_quality(requirement, spec)
        self._log.runtime("design_finished", project_id=project_id, agent="design",
                          task_id=task_id, success=True)
        return build_result(spec, quality, messages=["DesignSpec 已生成并通过校验"])

    # ---- 纯组装（无 IO / 无校验）----
    def assemble(self, original_model: Dict[str, Any], requirement: str,
                 project_id: str, task_id: str) -> Dict[str, Any]:
        req = parse_requirement(requirement)
        constraints = parse_constraints(original_model)

        style = plan_style(req)
        budget = plan_budget(req, area_m2=constraints.get("area_m2"))
        family = analyze_family(req)
        materials = plan_materials(req, constraints)
        rooms = self._build_rooms(original_model)
        preferences = self._build_preferences(req)
        lighting = self._build_lighting(req)
        storage = self._build_storage(req)
        special = req.get("special", []) or []

        quality = self._assess_quality(requirement, None)
        metadata = make_metadata(project_id, "design", task_id, "COMPLETED", quality)

        return {
            "metadata": metadata,
            "version": "v1",
            "design_goal": self._build_goal(req, style, family, special),
            "style": style,
            "budget": budget,
            "family": family,
            "rooms": rooms,
            "constraints": constraints,
            "preferences": preferences,
            "materials": materials,
            "lighting": lighting,
            "storage": storage,
            "special_requirements": special,
        }

    # ---- 辅助组装 ----
    def _build_goal(self, req, style, family, special) -> str:
        labels = "/".join(style.get("labels", [])) or "未定"
        parts = [f"{family.get('adults', 0)}人家庭"]
        if family.get("children"):
            parts.append("含儿童")
        if family.get("elders"):
            parts.append("含老人")
        if special:
            parts.append("需求：" + "/".join(special))
        return f"打造{labels}风格住宅（{'，'.join(parts)}），以 DesignSpec 固化全部设计决策。"

    def _build_rooms(self, original_model) -> List[Dict[str, Any]]:
        rooms = []
        for r in original_model.get("rooms", []) or []:
            rid = r.get("id") or r.get("name") or f"R{len(rooms) + 1:03d}"
            rooms.append({
                "room_id": rid,
                "name": r.get("name", rid),
                "function": r.get("type") or r.get("name") or "未定义",
                "priority": "medium",
                "notes": "",
            })
        return rooms

    def _build_preferences(self, req) -> Dict[str, Any]:
        lit = req.get("lighting_hints", []) or []
        pref = {
            "colors": req.get("color_hints", []) or [],
            "lighting_preference": lit[0] if lit else "neutral",
            "accessibility": bool(req.get("family_hints", {}).get("accessibility")),
            "notes": "",
        }
        return pref

    def _build_lighting(self, req) -> Dict[str, Any]:
        lit = req.get("lighting_hints", []) or []
        nat = "natural" in lit or "bright" in lit
        return {
            "natural_light": "优先利用自然采光" if nat else "按常规采光设计",
            "artificial_light": "无主灯 + 重点照明（具体由 Layout Agent 落实）",
            "notes": "照明为策略描述，不含灯具几何 / 点位",
        }

    def _build_storage(self, req) -> Dict[str, Any]:
        hints = req.get("storage_hints", []) or []
        if "强收纳" in hints:
            strategy = "全屋系统收纳，玄关 / 客厅 / 卧室定制柜体"
        elif "极简收纳" in hints:
            strategy = "隐藏式极简收纳，减少视觉杂物"
        else:
            strategy = "按需定制收纳，兼顾美观与容量"
        return {"strategy": strategy, "capacity_notes": "具体容量由 Layout Agent 计算"}

    def _assess_quality(self, requirement: str, spec) -> Dict[str, Any]:
        """确定性质量评估（无 LLM）。"""
        has_req = bool((requirement or "").strip())
        score = 70 if has_req else 45
        if spec and isinstance(spec, dict):
            if spec.get("constraints", {}).get("windows"):
                score += 10
            if spec.get("rooms"):
                score += 10
        score = min(score, 95)
        conf = round(score / 100.0, 2)
        return {"confidence": conf, "quality_score": score,
                "validation_passed": True}

    # ---- 输入解析 ----
    def _resolve_original_model(self, context: AgentContext) -> Dict[str, Any]:
        p = context.parameters.get("original_model_path")
        if p:
            return json.loads(Path(p).read_text(encoding="utf-8"))
        for ref in (context.input_refs or []):
            if str(ref).lower().endswith(".json"):
                return json.loads(Path(ref).read_text(encoding="utf-8"))
        # 回退：从同项目 Workspace 读取 Parser 产出
        proj = self._project_dir(context.project_id) / "original_model.json"
        if proj.exists():
            return json.loads(proj.read_text(encoding="utf-8"))
        raise ValidationError(
            "Design Agent 缺少 OriginalModel：请在 parameters.original_model_path / "
            "input_refs 提供，或先运行 Parser 产出 original_model.json")

    def _resolve_requirement(self, context: AgentContext) -> str:
        r = context.parameters.get("requirement")
        if isinstance(r, str) and r.strip():
            return r
        rp = context.parameters.get("requirement_path")
        if rp:
            return Path(rp).read_text(encoding="utf-8")
        for ref in (context.input_refs or []):
            s = str(ref).lower()
            if s.endswith(".txt") or s.endswith(".md"):
                return Path(ref).read_text(encoding="utf-8")
        return ""

    # ---- 路径 / 落盘 ----
    def _project_dir(self, project_id: str) -> Path:
        if self._workspace_root:
            d = self._workspace_root / "projects" / project_id
        else:
            d = PROJECTS_DIR / project_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_workspace(self, project_id: str, spec: Dict[str, Any]) -> None:
        ensure_workspace()
        out = self._project_dir(project_id) / "design_spec.json"
        out.write_text(json.dumps(spec, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        self._log.runtime("workspace_saved", project_id=project_id, agent="design",
                          path=str(out), version="v1")

    def _save_checkpoint(self, project_id: str, task_id: str,
                         spec: Dict[str, Any]) -> None:
        cp = self._project_dir(project_id) / "checkpoint_design_v1.json"
        payload = {
            "version": "v1",
            "agent": "design",
            "project_id": project_id,
            "task_id": task_id,
            "stage": "DESIGN_SPEC",
            "design_spec": spec,
            "task_status": {"design": "COMPLETED"},
            "project_status": {"stage": "DESIGN_SPEC", "state": "COMPLETED"},
        }
        cp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        self._log.runtime("checkpoint_saved", project_id=project_id, agent="design",
                          path=str(cp), checkpoint="checkpoint_design_v1.json")

    # ---- 类方法 / 便捷 ----
    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "DesignAgent":
        return cls(workspace_root=cfg.get("workspace_root"),
                   log_dir=cfg.get("log_dir"))

    def process(self, original_model_path, requirement: str = "",
                project_id: Optional[str] = None,
                task_id: Optional[str] = None) -> Result:
        """便捷独立运行（异常向上抛出）。"""
        p = Path(original_model_path)
        project_id = project_id or p.stem or "design_cli"
        task_id = task_id or f"design-{project_id}"
        with p.open(encoding="utf-8") as f:
            original_model = json.load(f)
        result = self.generate(original_model, requirement, project_id, task_id)
        return result


def run_design(original_model_path, requirement: str = "",
              project_id: Optional[str] = None, task_id: Optional[str] = None,
              workspace_root: Optional[Path] = None,
              log_dir: Optional[Path] = None) -> Result:
    """便捷函数：独立运行 Design Agent（Phase 4「Design Agent 可独立运行」）。"""
    agent = DesignAgent(workspace_root=workspace_root, log_dir=log_dir)
    return agent.process(original_model_path, requirement=requirement,
                         project_id=project_id, task_id=task_id)


__all__ = ["DesignAgent", "run_design"]
