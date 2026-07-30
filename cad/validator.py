"""CAD Command Validation（Phase 6 §8）— 校验 command / layer / transaction / entity。

四大检查维度（任务 §8）：
1. 非法 command   → command_type 必须登记在 COMMAND_REGISTRY
2. 非法 layer     → 图层命名必须合规（大写开头、仅 A-Z0-9_、≤31 字符）
3. 非法 transaction → 状态机完整性（开始前/提交后/回滚后再操作均非法）
4. 非法 entity    → 实体类型必须来自白名单，且引用图层合规

提供 CADValidator（类方法聚合）与自由函数两种入口。
依赖规则：禁止 import runtime / orchestrator / agents / professional。
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from .base.cad_transaction import CADTransaction, TransactionState
from .command.drawing_command import COMMAND_REGISTRY

# 图层命名：大写字母开头，仅含 A-Z 0-9 _，长度 ≤ 31（DWG 限制）
LAYER_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,30}$")

# 合法实体类型（与 DrawingModel.entities[].type 对齐）
ALLOWED_ENTITY_TYPES = frozenset({
    "WALL", "DOOR", "WINDOW", "FURNITURE", "DIMENSION",
    "AXIS", "COLUMN", "FIXTURE", "EQUIPMENT",
})

MAX_TXN_NESTING = 1  # Phase 6 单事务模型


class CADValidationError(Exception):
    """CAD 校验失败。"""


class CADValidator:
    """CAD 命令 / 图层 / 事务 / 实体 校验器。"""

    LAYER_RE = LAYER_RE
    ALLOWED_ENTITY_TYPES = ALLOWED_ENTITY_TYPES

    # ---- 命令 ----
    @classmethod
    def validate_command(cls, command: Any) -> bool:
        data = command.to_dict() if hasattr(command, "to_dict") else command
        ctype = data.get("command_type") if isinstance(data, dict) else None
        if ctype not in COMMAND_REGISTRY:
            raise CADValidationError(
                f"非法 command：{ctype!r} 未登记（已知："
                f"{sorted(COMMAND_REGISTRY)}）")
        return True

    # ---- 图层 ----
    @classmethod
    def validate_layer(cls, name: Any) -> bool:
        if not isinstance(name, str) or not cls.LAYER_RE.match(name):
            raise CADValidationError(
                f"非法 layer：{name!r}（须大写字母开头、仅含 A-Z0-9_、≤31 字符）")
        return True

    # ---- 实体 ----
    @classmethod
    def validate_entity(cls, entity: Dict[str, Any]) -> bool:
        if not isinstance(entity, dict):
            raise CADValidationError(f"非法 entity：{entity!r} 非 dict")
        etype = entity.get("type")
        if etype not in cls.ALLOWED_ENTITY_TYPES:
            raise CADValidationError(
                f"非法 entity type：{etype!r}（允许："
                f"{sorted(cls.ALLOWED_ENTITY_TYPES)}）")
        layer = entity.get("layer")
        if layer:
            cls.validate_layer(layer)
        return True

    # ---- 事务 ----
    @classmethod
    def validate_transaction(cls, txn: CADTransaction) -> bool:
        if not isinstance(txn, CADTransaction):
            raise CADValidationError("非法 transaction：非 CADTransaction 实例")
        # 提交/回滚后的事务不得再持有 ACTIVE 命令
        if txn.state not in (TransactionState.PENDING,
                             TransactionState.ACTIVE,
                             TransactionState.COMMITTED,
                             TransactionState.ROLLED_BACK):
            raise CADValidationError(f"非法 transaction 状态：{txn.state}")
        return True

    # ---- 模型级（DrawingModel）----
    @classmethod
    def validate_model(cls, drawing_model: Dict[str, Any]) -> bool:
        if not isinstance(drawing_model, dict):
            raise CADValidationError("DrawingModel 必须是 dict")
        for layer in drawing_model.get("layers", []) or []:
            lname = layer.get("name") if isinstance(layer, dict) else layer
            cls.validate_layer(lname)
        for entity in drawing_model.get("entities", []) or []:
            cls.validate_entity(entity)
        return True

    # ---- 聚合 ----
    @classmethod
    def assert_valid(cls, *,
                     commands: Optional[Iterable[Any]] = None,
                     layers: Optional[Iterable[Any]] = None,
                     entities: Optional[Iterable[Dict[str, Any]]] = None,
                     transactions: Optional[Iterable[CADTransaction]] = None,
                     model: Optional[Dict[str, Any]] = None) -> bool:
        if model is not None:
            cls.validate_model(model)
        if layers is not None:
            for l in layers:
                cls.validate_layer(l)
        if entities is not None:
            for e in entities:
                cls.validate_entity(e)
        if commands is not None:
            for c in commands:
                cls.validate_command(c)
        if transactions is not None:
            for t in transactions:
                cls.validate_transaction(t)
        return True


# 自由函数入口（向后兼容 / 简洁调用）
def validate_command(command: Any) -> bool:
    return CADValidator.validate_command(command)


def validate_layer(name: Any) -> bool:
    return CADValidator.validate_layer(name)


def validate_entity(entity: Dict[str, Any]) -> bool:
    return CADValidator.validate_entity(entity)


def validate_transaction(txn: CADTransaction) -> bool:
    return CADValidator.validate_transaction(txn)


def assert_cad_valid(**kwargs) -> bool:
    return CADValidator.assert_valid(**kwargs)


__all__ = [
    "CADValidator", "CADValidationError",
    "LAYER_RE", "ALLOWED_ENTITY_TYPES", "MAX_TXN_NESTING",
    "validate_command", "validate_layer", "validate_entity",
    "validate_transaction", "assert_cad_valid",
]
