"""Phase 6 §3 · CADTransaction 状态机测试。

验证 begin/commit/rollback 的合法转移与非法操作。
"""
from __future__ import annotations

import pytest

from cad.base.cad_transaction import (CADTransaction, CADTransactionError,
                                       TransactionState)


def test_transaction_happy_path():
    txn = CADTransaction("t1")
    assert txn.state is TransactionState.PENDING
    txn.begin()
    assert txn.state is TransactionState.ACTIVE
    txn.add_command("cmd")
    assert len(txn.commands) == 1
    txn.commit()
    assert txn.state is TransactionState.COMMITTED


def test_transaction_rollback():
    txn = CADTransaction("t2")
    txn.begin()
    txn.add_command("cmd")
    txn.rollback()
    assert txn.state is TransactionState.ROLLED_BACK


def test_transaction_begin_twice_illegal():
    txn = CADTransaction("t3")
    txn.begin()
    with pytest.raises(CADTransactionError):
        txn.begin()


def test_transaction_commit_without_begin_illegal():
    txn = CADTransaction("t4")
    with pytest.raises(CADTransactionError):
        txn.commit()


def test_transaction_rollback_without_begin_illegal():
    txn = CADTransaction("t5")
    with pytest.raises(CADTransactionError):
        txn.rollback()


def test_transaction_add_command_without_active_illegal():
    txn = CADTransaction("t6")
    with pytest.raises(CADTransactionError):
        txn.add_command("cmd")
