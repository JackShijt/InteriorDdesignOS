"""models.generated · 生成产物模型（CAD 执行结果摘要）。

Phase 12.5 完善：GeneratedModel 现在同时承载 DWG 回读结果
（layers / entities / dimensions / counts），支撑 Round-Trip 验证：
    生成 DWG → 重新读取 DWG → GeneratedModel → ValidationReport
    → Compare LayoutModel
新增字段全部有默认值，向后兼容 Phase 11 及之前的用法。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.base.model import Model


@dataclass
class GeneratedModel(Model):
    source_project_id: str = ""
    drawing_model_ref: str = ""
    cad_backend: str = "mock"
    command_count: int = 0
    drawing_command_log: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)

    # ---- Phase 12.5：DWG 回读（Round-Trip）----
    dwg_path: str = ""
    layers: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    dimensions: List[Dict[str, Any]] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
