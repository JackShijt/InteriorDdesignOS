"""cad/base — CAD 抽象层（Adapter / Document / Transaction / Session）。"""
from __future__ import annotations

from .cad_adapter import CADAdapter, CAD_ADAPTER_METHODS
from .cad_document import CADDocument
from .cad_transaction import CADTransaction, CADTransactionError, TransactionState
from .cad_session import CADSession

__all__ = ["CADAdapter", "CAD_ADAPTER_METHODS", "CADDocument",
           "CADTransaction", "CADTransactionError", "TransactionState",
           "CADSession"]
