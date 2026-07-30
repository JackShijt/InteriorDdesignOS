"""
InteriorDesignOS · State Manager

本模块遵守 PROJECT_RULES.md 的最高约束。

Project 阶段生命周期（Phase 2 §5 / PROJECT_RULES §11、§13）：
状态必须严格遵守顺序：
  INITIALIZATION → INPUT_ANALYSIS → ORIGINAL_MODEL → DESIGN_SPEC → LAYOUT
  → PROFESSIONAL_DEEPENING → GEOMETRY → DRAWING → DWG_GENERATION
  → VALIDATION → REPAIR → EXPORT

- 主流程只能沿顺序前进到下一阶段
- REPAIR 为特殊回退阶段（VALIDATION / DWG_GENERATION 可进入，修复后回到 VALIDATION）
- 禁止跳变 / 逆序（除非显式 regress，用于设计回退）
- 阶段切换通过 EventBus 发布 StageChanged
"""

from typing import Optional

from runtime.event_bus import EventBus
from runtime.logger import UnifiedLogger
from runtime.message import Event, EventType
from runtime.project_runtime import STAGES, ProjectRuntime
from agents.orchestrator.error_handler import ValidationError

# 合法阶段转移：严格按 12 阶段顺序前进（PROJECT_RULES §11、Phase 2 §5）
#   INITIALIZATION → INPUT_ANALYSIS → ... → VALIDATION → REPAIR → EXPORT
STAGE_TRANSITIONS: dict = {}
for _i, _s in enumerate(STAGES):
    nxt = [STAGES[_i + 1]] if _i + 1 < len(STAGES) else []
    STAGE_TRANSITIONS[_s] = nxt
# 修复分支（校验/出图失败后进入 REPAIR；REPAIR 后继保持 EXPORT，不回环）
STAGE_TRANSITIONS["DWG_GENERATION"].append("REPAIR")


class StateManager:
    """Project 阶段状态机。"""

    def __init__(self, project_runtime: ProjectRuntime,
                 event_bus: EventBus, logger: UnifiedLogger):
        self._pr = project_runtime
        self._bus = event_bus
        self._logger = logger

    @staticmethod
    def can_transition(frm: str, to: str) -> bool:
        if frm == to:
            return True
        return to in STAGE_TRANSITIONS.get(frm, [])

    def validate_transition(self, frm: str, to: str) -> None:
        if not self.can_transition(frm, to):
            raise ValidationError(f"非法阶段转移: {frm} -> {to}")

    def current_stage(self, project_id: str) -> str:
        p = self._pr.load(project_id)
        if p is None:
            raise FileNotFoundError(f"Project 不存在: {project_id}")
        return p["current_stage"]

    def advance(self, project_id: str) -> str:
        """推进到下一阶段（严格顺序），发布 StageChanged。"""
        cur = self.current_stage(project_id)
        nxt_list = STAGE_TRANSITIONS.get(cur, [])
        if not nxt_list:
            raise ValidationError(f"阶段 {cur} 无后继阶段，无法推进")
        # 主流程推进取顺序后继（非 REPAIR）
        nxt = nxt_list[0]
        self.validate_transition(cur, nxt)
        self._pr.set_stage(project_id, nxt)
        self._logger.runtime("stage_advanced", project_id=project_id,
                             from_stage=cur, to_stage=nxt)
        self._bus.publish(Event(
            EventType.STAGE_CHANGED,
            {"project_id": project_id, "from_stage": cur, "to_stage": nxt},
        ))
        return nxt

    def enter_repair(self, project_id: str) -> str:
        """进入 REPAIR 阶段（校验/出图失败后）。"""
        cur = self.current_stage(project_id)
        self.validate_transition(cur, "REPAIR")
        self._pr.set_stage(project_id, "REPAIR")
        self._bus.publish(Event(
            EventType.STAGE_CHANGED,
            {"project_id": project_id, "from_stage": cur, "to_stage": "REPAIR"},
        ))
        return "REPAIR"

    def set_stage(self, project_id: str, stage: str) -> None:
        cur = self.current_stage(project_id)
        self.validate_transition(cur, stage)
        self._pr.set_stage(project_id, stage)


__all__ = ["STAGE_TRANSITIONS", "StateManager", "STAGES"]
