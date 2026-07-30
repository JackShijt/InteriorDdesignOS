"""
InteriorDesignOS · Professional Deepening Framework（Phase 5）

统一的专业深化框架：8 个 Professional Agent（Mock Logic）
只读 LayoutModel（SSOT）+ 可选 DesignSpec，输出 ProfessionalModel，
由 ProfessionalValidator 聚合校验。

禁止：AutoCAD MCP / 生成 DWG / 调用外部 AI / 修改 LayoutModel 或 DesignSpec。
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

# 小写专业名（agent_name）→ 与 runtime.agent_registry.PROFESSIONAL_AGENTS 对齐
PROFESSIONAL_DISCIPLINES: tuple[str, ...] = (
    "electrical", "plumbing", "lighting", "ceiling",
    "flooring", "hvac", "construction", "furniture",
)


def build_professional_agents(workspace_root: Optional[Path] = None,
                              log_dir: Optional[Path] = None,
                              disciplines: Optional[Sequence[str]] = None,
                              logger=None,
                              ) -> List["BaseProfessionalAgent"]:
    """构建全部（或指定）Professional Agent 实例。

    延迟导入各专业模块，避免包加载期的循环依赖。
    """
    from professional.base.professional_agent import BaseProfessionalAgent  # noqa: F401
    from professional.electrical.electrical_agent import ElectricalAgent
    from professional.plumbing.plumbing_agent import PlumbingAgent
    from professional.lighting.lighting_agent import LightingAgent
    from professional.ceiling.ceiling_agent import CeilingAgent
    from professional.flooring.flooring_agent import FlooringAgent
    from professional.hvac.hvac_agent import HVACAgent
    from professional.construction.construction_agent import ConstructionAgent
    from professional.furniture.furniture_agent import FurnitureAgent

    factory = {
        "electrical": ElectricalAgent,
        "plumbing": PlumbingAgent,
        "lighting": LightingAgent,
        "ceiling": CeilingAgent,
        "flooring": FlooringAgent,
        "hvac": HVACAgent,
        "construction": ConstructionAgent,
        "furniture": FurnitureAgent,
    }
    wanted = list(disciplines) if disciplines else list(PROFESSIONAL_DISCIPLINES)
    unknown = [d for d in wanted if d not in factory]
    if unknown:
        raise ValueError(f"未知专业: {unknown}，可选: {sorted(factory)}")
    return [factory[d](workspace_root=workspace_root, log_dir=log_dir,
                       logger=logger)
            for d in wanted]


__all__ = ["PROFESSIONAL_DISCIPLINES", "build_professional_agents"]
