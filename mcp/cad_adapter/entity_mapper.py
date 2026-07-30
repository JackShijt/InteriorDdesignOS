"""mcp.cad_adapter.entity_mapper · entity_id ↔ autocad_handle 映射（Phase 13 §7）。

用途：回读 / 修改 / 验证时，将 InteriorDesignOS 侧 ``entity_id`` 与 AutoCAD 侧
``autocad_handle`` 双向追踪。

约束：
- 仅做 ID 映射，不含任何 CAD 业务。
- 同一 entity_id 的 handle 一旦注册不可静默覆盖（防止回读错位）。
"""

from __future__ import annotations

from typing import Dict, Optional

from mcp.cad_adapter.exceptions import EntityMappingError


class EntityMapper:
    """维护 DrawingModel entity 与 AutoCAD Entity handle 的映射。"""

    def __init__(self) -> None:
        self._forward: Dict[str, str] = {}   # entity_id -> handle
        self._reverse: Dict[str, str] = {}   # handle -> entity_id

    # ---- 注册 / 查询 -----------------------------------------------------
    def register(self, entity_id: str, handle: str) -> None:
        """注册一个 entity_id → handle 映射。"""
        if not entity_id:
            raise EntityMappingError("entity_id 不能为空")
        if not handle:
            raise EntityMappingError("autocad_handle 不能为空")
        if entity_id in self._forward and self._forward[entity_id] != handle:
            raise EntityMappingError(
                f"entity_id 已映射到其他 handle: {entity_id} "
                f"({self._forward[entity_id]} != {handle})")
        self._forward[entity_id] = handle
        self._reverse[handle] = entity_id

    def lookup(self, entity_id: str) -> Optional[str]:
        """entity_id → handle。"""
        return self._forward.get(entity_id)

    def reverse_lookup(self, handle: str) -> Optional[str]:
        """handle → entity_id。"""
        return self._reverse.get(handle)

    def has(self, entity_id: str) -> bool:
        return entity_id in self._forward

    # ---- 序列化 ----------------------------------------------------------
    def to_dict(self) -> Dict[str, str]:
        """正向映射快照（entity_id -> handle）。"""
        return dict(self._forward)

    def entries(self) -> Dict[str, Dict[str, str]]:
        """带方向信息的完整快照（供 GeneratedModel / 回读使用）。"""
        return {
            eid: {"handle": h, "entity_id": eid}
            for eid, h in self._forward.items()
        }

    def size(self) -> int:
        return len(self._forward)

    @classmethod
    def from_dict(cls, mapping: Dict[str, str]) -> "EntityMapper":
        inst = cls()
        for eid, handle in (mapping or {}).items():
            inst.register(eid, handle)
        return inst


__all__ = ["EntityMapper"]
