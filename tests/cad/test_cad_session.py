"""Phase 6 §3 · CADSession 生命周期测试。

验证：
- open → run(queue)（事务批量）→ close 流程
- run 后 committed_records 收集到记录
- 无活动事务 execute 抛错
- 禁止嵌套 begin（单事务模型）
"""
from __future__ import annotations

import pytest

from cad import CADSession, DrawingCommandQueue, MockAdapter
from cad.command.drawing_command import (CreateLayerCommand, DrawLineCommand)
from cad.base.cad_transaction import CADTransactionError


def _queue():
    q = DrawingCommandQueue()
    q.append(CreateLayerCommand("WALL"))
    q.append(DrawLineCommand([0, 0], [1000, 0], "WALL"))
    return q


def test_session_open_run_close():
    adapter = MockAdapter()
    session = CADSession(adapter)
    session.open("demo.dwg")
    assert session.document is not None
    assert adapter.connected is True

    txn = session.run(_queue())
    assert txn.state.value == "COMMITTED"
    assert len(session.committed_records) == 2

    session.close()
    assert adapter.connected is False


def test_session_execute_requires_active_transaction():
    adapter = MockAdapter()
    session = CADSession(adapter)
    session.open("demo.dwg")
    with pytest.raises(CADTransactionError):
        session.execute(DrawLineCommand([0, 0], [1, 1]))
    session.close()


def test_session_nested_begin_rejected():
    adapter = MockAdapter()
    session = CADSession(adapter)
    session.open("demo.dwg")
    session.begin()
    with pytest.raises(CADTransactionError):
        session.begin()  # 单事务模型：禁止嵌套
    session.close()


def test_session_run_is_transactional_atomic():
    adapter = MockAdapter()
    session = CADSession(adapter)
    session.open("demo.dwg")
    # 队列末尾放一个会抛错的命令
    bad = DrawingCommandQueue()
    bad.append(CreateLayerCommand("WALL"))
    bad.append(_BoomCommand())
    with pytest.raises(RuntimeError):
        session.run(bad)
    # 自动 rollback：无 committed 记录
    assert len(session.committed_records) == 0
    assert session.current_txn is None
    session.close()


class _BoomCommand:
    command_type = "boom"

    def execute(self, adapter):
        raise RuntimeError("boom")

    def to_dict(self):
        return {"command_type": "boom", "params": {}}
