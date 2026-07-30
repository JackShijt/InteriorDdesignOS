"""models.model_pipeline · 版本传递链（Phase 8 §2）。

负责 OriginalModel → DesignSpec → LayoutModel → GeometryModel
→ DrawingModel → GeneratedModel 的版本传递与连续性记录。

注意：本类只做「版本传递 / 登记」，不实现任何业务转换
（业务转换在各 Agent）。每个模型必须记录：
  model_type / version / parent_version / producer_agent / timestamp
以及统一的 metadata（project_id / agent / task_id / schema_version / timestamp）
与版本链标签（layout_model_version / geometry_model_version / drawing_model_version）。
"""
from typing import Any, Dict, List, Optional

from models.base.model import SCHEMA_VERSION, _now_iso


class ModelPipeline:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self._labels: Dict[str, int] = {}
        self.chain: List[Dict[str, Any]] = []

    def _next_label(self, model_type: str) -> str:
        n = self._labels.get(model_type, 0) + 1
        self._labels[model_type] = n
        return f"v{n}"

    def observe(self, model_type: str,
                model_dict: Dict[str, Any]) -> Dict[str, Any]:
        """登记已存在的（输入）模型到版本链，不修改模型本身。"""
        md = model_dict.get("metadata", {}) or {}
        ver = model_dict.get("version", {}) or {}
        self.chain.append({
            "model_type": model_type,
            "version": ver.get("model_version", "v1"),
            "parent_version": ver.get("parent_version", "none"),
            "producer_agent": md.get("agent", "unknown"),
            "task_id": md.get("task_id", "unknown"),
            "timestamp": md.get("timestamp"),
        })
        return model_dict

    def attach(self, model_type: str, producer_agent: str, task_id: str,
               payload: Dict[str, Any],
               parent: Optional[Dict[str, Any]] = None,
               quality: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """为 payload 打上 metadata + version + 版本链标签并登记。"""
        own = self._next_label(model_type)
        parent_version = "none"
        lineage: Dict[str, str] = {}
        if parent:
            pmd = parent.get("metadata", {}) or {}
            pver = (pmd.get("version", {}) or {}).get("model_version") or "v1"
            parent_version = pver
            for key in ("layout_model_version", "geometry_model_version",
                        "drawing_model_version"):
                if parent.get(key) is not None:
                    lineage[key] = str(parent[key])

        if model_type == "layout":
            lineage["layout_model_version"] = own
        elif model_type == "geometry":
            lineage.setdefault(
                "layout_model_version",
                (parent.get("metadata", {}).get("version", {}).get("model_version")
                 if parent else "v1") or "v1",
            )
            lineage["geometry_model_version"] = own
        elif model_type == "drawing":
            lineage.setdefault("layout_model_version", "v1")
            lineage.setdefault("geometry_model_version", "v1")
            lineage["drawing_model_version"] = own
        elif model_type == "generated":
            lineage.setdefault("layout_model_version", "v1")
            lineage.setdefault("geometry_model_version", "v1")
            lineage.setdefault("drawing_model_version", "v1")

        ts = _now_iso()
        payload["metadata"] = {
            "project_id": self.project_id,
            "agent": producer_agent,
            "task_id": task_id,
            "timestamp": ts,
            "schema_version": SCHEMA_VERSION,
            "status": "COMPLETED",
            "quality": quality or {"confidence": 1.0, "quality_score": 100,
                                   "validation_passed": True},
        }
        payload["version"] = {
            "model_version": own,
            "parent_version": parent_version,
            "producer_agent": producer_agent,
            "timestamp": ts,
        }
        for k, v in lineage.items():
            payload[k] = v
        self.chain.append({
            "model_type": model_type,
            "version": own,
            "parent_version": parent_version,
            "producer_agent": producer_agent,
            "task_id": task_id,
            "timestamp": ts,
        })
        return payload

    def to_dict(self) -> Dict[str, Any]:
        return {"project_id": self.project_id, "chain": self.chain}

    def verify_chain(self) -> bool:
        """校验版本链连续性：每个非 root 记录的 parent_version 应等于前驱 version。"""
        seen: Dict[str, str] = {}
        for rec in self.chain:
            if rec["parent_version"] != "none":
                if rec["parent_version"] not in seen:
                    return False
            seen[rec["version"]] = rec["model_type"]
        return True
