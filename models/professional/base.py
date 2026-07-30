"""models.professional.base · 专业深化模型基类与校验报告（Phase 9 §1 / §5）。

所有专业深化模型（电气 / 给排水 / 照明 / 吊顶 / 施工 / 立面）统一继承
``ProfessionalModel``，从而自动携带 ``Model`` 基类提供的：
- metadata  : project_id / agent / task_id / schema_version / timestamp
- version   : model_version / parent_version / producer_agent / timestamp
- 版本链标签 : layout_model_version / geometry_model_version / drawing_model_version

基类只负责「契约字段」，不实现任何业务逻辑（业务由各 Agent 填充 content 字段）。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.base.model import Model


@dataclass
class ProfessionalModel(Model):
    """专业深化模型统一基类。

    discipline 标识专业领域；summary 记录派生统计（设备数 / 回路数等）。
    """

    discipline: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport(Model):
    """专业深化校验报告（Phase 9 §5）。

    输入：LayoutModel + ProfessionalModels
    输出：ValidationReport（status / issues / rule_results / summary）
    """

    status: str = "PASS"                      # PASS / WARN / FAIL
    checked_count: int = 0
    issues: List[Dict[str, Any]] = field(default_factory=list)
    rule_results: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
