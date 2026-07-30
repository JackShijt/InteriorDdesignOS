"""
InteriorDesignOS · BaseProfessionalModel（Phase 5 §4/§5）

所有专业模型（ElectricalModel / PlumbingModel / ...）的公共 dataclass 基类。
统一提供 ProfessionalModel Schema 所需的公共字段与序列化逻辑，
禁止各专业重复实现（PROJECT_RULES：SOLID / DRY）。

序列化契约（schemas/professional/professional_model.schema.json）：
  metadata / layout_model_version / discipline / objects / constraints / quality

各专业只声明自己的领域集合字段（如 switches / sockets），
由 COLLECTION_FIELDS / SINGLE_FIELDS 汇总为统一 objects 列表。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple, Type, TypeVar

from models.base.model_converter import ModelConverter

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound="BaseProfessionalModel")

# 八大专业（与 Schema discipline 枚举一致）
DISCIPLINES: Tuple[str, ...] = (
    "ELECTRICAL", "PLUMBING", "LIGHTING", "CEILING",
    "FLOORING", "HVAC", "CONSTRUCTION", "FURNITURE",
)


@dataclass
class BaseProfessionalModel:
    """专业模型公共基类（Phase 5 §5）。

    - DISCIPLINE：专业类型（子类以 ClassVar 声明）
    - COLLECTION_FIELDS：领域列表字段名（每项为 dict），汇总进 objects
    - SINGLE_FIELDS：领域单对象字段名（dict），汇总进 objects
    """

    DISCIPLINE: ClassVar[str] = "BASE"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = ()
    SINGLE_FIELDS: ClassVar[Tuple[str, ...]] = ()

    metadata: Dict[str, Any] = field(default_factory=dict)
    layout_model_version: str = ""
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    quality: Dict[str, Any] = field(default_factory=dict)

    # ---- 序列化 ----
    def collect_objects(self) -> List[Dict[str, Any]]:
        """把各领域集合字段汇总为统一 objects 列表（附 category）。"""
        objects: List[Dict[str, Any]] = []
        for name in self.COLLECTION_FIELDS:
            for item in getattr(self, name, []) or []:
                objects.append({"category": name, **item})
        for name in self.SINGLE_FIELDS:
            single = getattr(self, name, None)
            if single:
                objects.append({"category": name, **single})
        return objects

    def to_dict(self) -> Dict[str, Any]:
        """输出符合 professional_model.schema.json 的字典。"""
        return {
            "metadata": self.metadata,
            "layout_model_version": self.layout_model_version,
            "discipline": self.DISCIPLINE,
            "objects": self.collect_objects(),
            "constraints": self.constraints,
            "quality": self.quality,
        }

    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串（Phase 5.1 §7；经 ModelConverter 统一处理）。"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent,
                          default=str)

    # ---- 反序列化（Phase 5.1 §7/§8）----
    @classmethod
    def from_dict(cls: Type[TModel], data: Dict[str, Any]) -> TModel:
        """从 schema 字典重建强类型模型：objects 按 category 拆回领域字段。"""
        model = ModelConverter.from_dict(cls, {
            k: v for k, v in data.items()
            if k in ("metadata", "layout_model_version", "constraints",
                     "quality")
        })
        for obj in data.get("objects", []) or []:
            category = obj.get("category")
            payload = {k: v for k, v in obj.items() if k != "category"}
            if category in cls.COLLECTION_FIELDS:
                getattr(model, category).append(payload)
            elif category in cls.SINGLE_FIELDS:
                setattr(model, category, payload)
        return model

    @classmethod
    def from_json(cls: Type[TModel], text: str) -> TModel:
        import json
        return cls.from_dict(json.loads(text))

    # ---- 便捷 ----
    def object_count(self) -> int:
        return len(self.collect_objects())


__all__ = ["BaseProfessionalModel", "DISCIPLINES"]
