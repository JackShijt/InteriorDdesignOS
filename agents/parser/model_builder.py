"""
InteriorDesignOS · Parser · OriginalModel Builder（Phase 3 §5）

根据输入建立 OriginalModel，遵守 schemas/cad/original_model.schema.json。
必须生成：metadata / units / coordinates / walls / doors / windows / rooms。
当前阶段为占位解析（无真实 CAD 几何提取）：
- 无法解析时几何数组允许为空（禁止返回 null）
- 若输入为 JSON 且包含合法几何列表，可作为提示填充（仍经 Schema 校验把关）

禁止返回 null；所有数组字段始终存在。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.orchestrator.agent import make_metadata
from agents.parser.input_detector import InputType


def _default_units() -> Dict[str, str]:
    return {"length": "mm", "area": "m2", "angle": "degree"}


def _default_coordinates() -> Dict[str, Any]:
    return {"origin": [0, 0], "system": "world"}


def _geometry_from_hints(hints: Optional[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """从 JSON 提示中提取几何列表（仅当为合法 list 时采用，否则回退空数组）。"""
    out: Dict[str, List[Any]] = {"walls": [], "doors": [], "windows": [], "rooms": []}
    if not isinstance(hints, dict):
        return out
    for key in ("walls", "doors", "windows", "rooms"):
        val = hints.get(key)
        if isinstance(val, list):
            out[key] = val
    return out


def build_original_model(
    project_id: str,
    task_id: str,
    input_type: InputType,
    quality: Dict[str, Any],
    hints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构建符合 Schema 的 OriginalModel。

    始终包含全部 6 个必填顶层字段；几何在无法解析时为空数组。
    """
    geo = _geometry_from_hints(hints)
    metadata = make_metadata(
        project_id=project_id,
        agent="parser",
        task_id=task_id,
        status="COMPLETED",
        quality=quality,
    )
    return {
        "metadata": metadata,
        "units": _default_units(),
        "coordinates": _default_coordinates(),
        "walls": geo["walls"],
        "doors": geo["doors"],
        "windows": geo["windows"],
        "rooms": geo["rooms"],
    }


__all__ = ["build_original_model"]
