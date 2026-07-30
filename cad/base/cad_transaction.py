"""CADTransaction（Phase 6 §3）— 事务抽象 + 状态机。

保证命令的原子性边界：begin → (add_command / execute)* → commit | rollback。
Phase 6 采用「单事务模型」（MAX_NESTING=1），禁止嵌套 begin。
依赖规则：禁止 import runtime / orchestrator / agents / professional。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class TransactionState(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"


class CADTransactionError(Exception):
    """事务状态机非法操作。"""


@dataclass
class CADTransaction:
    """一次事务：持有命令与执行记录，并约束状态转移。"""

    id: str
    state: TransactionState = TransactionState.PENDING
    commands: List[Any] = field(default_factory=list)
    records: List[Dict[str, Any]] = field(default_factory=list)

    def begin(self) -> None:
        if self.state is not TransactionState.PENDING:
            raise CADTransactionError(
                f"无法 begin：事务已处于 {self.state.value}")
        self.state = TransactionState.ACTIVE

    def add_command(self, command: Any) -> None:
        if self.state is not TransactionState.ACTIVE:
            raise CADTransactionError(
                "只能在 ACTIVE 事务中 add_command")
        self.commands.append(command)

    def commit(self) -> None:
        if self.state is not TransactionState.ACTIVE:
            raise CADTransactionError(
                f"无法 commit：事务处于 {self.state.value}")
        self.state = TransactionState.COMMITTED

    def rollback(self) -> None:
        if self.state is not TransactionState.ACTIVE:
            raise CADTransactionError(
                f"无法 rollback：事务处于 {self.state.value}")
        self.state = TransactionState.ROLLED_BACK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state.value,
            "command_count": len(self.commands),
            "record_count": len(self.records),
        }


__all__ = ["CADTransaction", "CADTransactionError", "TransactionState"]
