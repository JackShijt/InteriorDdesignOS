"""models.base.model · 模型基类、元数据与版本（Phase 8 §2、§7）。

所有设计模型（LayoutModel / GeometryModel / DrawingModel / ...）统一携带：
- metadata         : project_id / agent / task_id / schema_version / timestamp
- version          : model_version / parent_version / producer_agent / timestamp
- 版本链标签        : layout_model_version / geometry_model_version / drawing_model_version

版本链（父→子）由 ModelPipeline 负责维护（见 models.model_pipeline）。
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.base.model_converter import ModelConverter

SCHEMA_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


@dataclass
class ModelMetadata:
    project_id: str = ""
    agent: str = "unknown"
    task_id: str = "unknown"
    timestamp: str = field(default_factory=_now_iso)
    schema_version: str = SCHEMA_VERSION
    status: str = "COMPLETED"
    quality: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelVersion:
    model_version: str = "v1"
    parent_version: str = "none"
    producer_agent: str = "unknown"
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Model:
    """所有设计模型的基类。"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    version: Dict[str, Any] = field(default_factory=dict)
    layout_model_version: Optional[str] = None
    geometry_model_version: Optional[str] = None
    drawing_model_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return ModelConverter.to_dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Model":
        return ModelConverter.from_dict(cls, data)

    def stamp(self, context, model_version: str = "v1",
              parent_version: str = "none",
              producer_agent: Optional[str] = None) -> "Model":
        """用运行上下文填写 metadata / version（agent 自描述；流水线亦会再打标）。"""
        agent = producer_agent or getattr(self, "discipline", None) or "unknown"
        self.metadata = make_metadata(
            project_id=context.project_id, agent=agent, task_id=context.task_id)
        self.version = make_version(
            model_version=model_version, parent_version=parent_version,
            producer_agent=agent)
        return self


def make_metadata(project_id: str, agent: str, task_id: str,
                  schema_version: str = SCHEMA_VERSION,
                  status: str = "COMPLETED",
                  quality: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "project_id": project_id,
        "agent": agent,
        "task_id": task_id,
        "timestamp": _now_iso(),
        "schema_version": schema_version,
        "status": status,
        "quality": quality or {},
    }


def make_version(model_version: str = "v1", parent_version: str = "none",
                 producer_agent: str = "unknown") -> Dict[str, Any]:
    return {
        "model_version": model_version,
        "parent_version": parent_version,
        "producer_agent": producer_agent,
        "timestamp": _now_iso(),
    }
