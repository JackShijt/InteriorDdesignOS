"""CADSession（Phase 6 §3）— CAD 生命周期管理：Document + Transaction + Command Queue。

职责：
- 管理 Adapter 连接与 Document 打开/关闭
- 提供 begin / commit / rollback 事务边界
- 提供 run(queue) 以事务方式批量执行命令队列

依赖规则：禁止 import runtime / orchestrator / agents / professional；
仅依赖 cad.base / cad.command（同包内）与 core。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..command.drawing_command import DrawingCommand, DrawingCommandQueue
from .cad_adapter import CADAdapter
from .cad_document import CADDocument
from .cad_transaction import (CADTransaction, CADTransactionError,
                              TransactionState)


class CADSession:
    """CAD 会话：把 Adapter（后端）+ Document + Transaction + Queue 串起来。"""

    def __init__(self, adapter: CADAdapter, document_name: str = "drawing"):
        self.adapter = adapter
        self.document_name = document_name
        self.document: Optional[CADDocument] = None
        self.current_txn: Optional[CADTransaction] = None
        self.committed_records: List[Dict[str, Any]] = []
        self._txn_counter = 0

    # ------------------------------------------------------------------ #
    # 文档生命周期
    # ------------------------------------------------------------------ #
    def open(self, name: Optional[str] = None) -> CADDocument:
        if name:
            self.document_name = name
        self.adapter.connect()
        self.document = self.adapter.open_document(self.document_name)
        self.document.is_open = True
        return self.document

    def close(self) -> None:
        if self.current_txn and self.current_txn.state == TransactionState.ACTIVE:
            self.rollback()
        self.adapter.close()
        if self.document:
            self.document.is_open = False
        self.adapter.disconnect()

    # ------------------------------------------------------------------ #
    # 事务
    # ------------------------------------------------------------------ #
    def begin(self) -> CADTransaction:
        if self.current_txn and self.current_txn.state == TransactionState.ACTIVE:
            raise CADTransactionError(
                "已存在 ACTIVE 事务，禁止嵌套 begin（Phase 6 单事务模型）")
        self._txn_counter += 1
        self.current_txn = CADTransaction(f"txn-{self._txn_counter}")
        self.current_txn.begin()
        return self.current_txn

    def execute(self, command: DrawingCommand) -> Dict[str, Any]:
        if (not self.current_txn
                or self.current_txn.state != TransactionState.ACTIVE):
            raise CADTransactionError(
                "execute 必须在 begin/commit 之间调用")
        self.current_txn.add_command(command)
        record = command.execute(self.adapter)
        self.current_txn.records.append(record)
        if self.document:
            self.document.add_entity(record)
        return record

    def commit(self) -> CADTransaction:
        if not self.current_txn:
            raise CADTransactionError("无活动事务可 commit")
        self.current_txn.commit()
        self.committed_records.extend(self.current_txn.records)
        txn = self.current_txn
        self.current_txn = None
        return txn

    def rollback(self) -> CADTransaction:
        if not self.current_txn:
            raise CADTransactionError("无活动事务可 rollback")
        self.current_txn.rollback()
        txn = self.current_txn
        self.current_txn = None  # 丢弃 provisional 记录（未并入 committed）
        return txn

    # ------------------------------------------------------------------ #
    # 队列执行（Command Queue）
    # ------------------------------------------------------------------ #
    def run(self, queue: DrawingCommandQueue,
            transactional: bool = True) -> Optional[CADTransaction]:
        """执行整个命令队列。

        transactional=True（默认）：内部 begin → execute* → commit；
        任一命令抛错则自动 rollback 并向上抛出。
        transactional=False：逐条 execute（需调用方自行管理事务）。
        """
        if transactional:
            if self.current_txn and \
                    self.current_txn.state == TransactionState.ACTIVE:
                raise CADTransactionError(
                    "已有 ACTIVE 事务，run(transactional=True) 不可嵌套")
            self.begin()
            try:
                for command in queue:
                    self.execute(command)
                return self.commit()
            except Exception:
                self.rollback()
                raise
        else:
            for command in queue:
                self.execute(command)
            return None


__all__ = ["CADSession"]
