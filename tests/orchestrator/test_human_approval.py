"""Phase 10 §8 · Human Approval 测试。"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.approval import (ApprovalManager, ApprovalRequest,  # noqa: E402
                              ApprovalStatus)


def test_new_request_is_waiting_user():
    req = ApprovalRequest(subject="专业冲突", project_id="p1")
    assert req.status == ApprovalStatus.WAITING_USER.value
    assert req.is_waiting()


def test_approve_transitions_and_result():
    req = ApprovalRequest(subject="专业冲突")
    result = req.approve(comment="ok")
    assert req.status == ApprovalStatus.APPROVED.value
    assert result.approved is True
    assert result.decision == "APPROVED"


def test_reject_transitions():
    req = ApprovalRequest(subject="专业冲突")
    result = req.reject(comment="需修改")
    assert req.status == ApprovalStatus.REJECTED.value
    assert result.approved is False


def test_cannot_decide_twice():
    req = ApprovalRequest(subject="x")
    req.approve()
    with pytest.raises(ValueError):
        req.reject()


def test_manager_lifecycle():
    mgr = ApprovalManager()
    req = mgr.create(subject="冲突", project_id="p1",
                     payload={"conflict_count": 3})
    assert req in mgr.pending()
    result = mgr.approve(req.request_id, comment="批准")
    assert result.approved
    assert mgr.pending() == []
    assert mgr.get(req.request_id).status == ApprovalStatus.APPROVED.value
