"""
runtime.approval.approval · Human Approval 节点（Phase 10 §6）。

当出现需要人工裁决的情形（如专业冲突）时，编排层创建 ApprovalRequest，
任务进入 WAITING_USER 状态，等待用户 approve / reject，得到 ApprovalResult。

本模块只负责“审批状态机”，不做任何设计决策。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


class ApprovalStatus(str, Enum):
    WAITING_USER = "WAITING_USER"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class ApprovalResult:
    """审批结果。"""
    request_id: str
    decision: str                 # APPROVED / REJECTED
    comment: str = ""
    decided_by: str = "user"
    decided_at: str = field(default_factory=_now_iso)

    @property
    def approved(self) -> bool:
        return self.decision == ApprovalStatus.APPROVED.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "decision": self.decision,
            "comment": self.comment,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
        }


@dataclass
class ApprovalRequest:
    """审批请求：创建即处于 WAITING_USER 状态。"""
    subject: str
    project_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: f"appr-{uuid.uuid4().hex[:8]}")
    status: str = ApprovalStatus.WAITING_USER.value
    created_at: str = field(default_factory=_now_iso)
    result: Optional[ApprovalResult] = None

    def is_waiting(self) -> bool:
        return self.status == ApprovalStatus.WAITING_USER.value

    def approve(self, comment: str = "", decided_by: str = "user") -> ApprovalResult:
        return self._decide(ApprovalStatus.APPROVED.value, comment, decided_by)

    def reject(self, comment: str = "", decided_by: str = "user") -> ApprovalResult:
        return self._decide(ApprovalStatus.REJECTED.value, comment, decided_by)

    def _decide(self, decision: str, comment: str, decided_by: str) -> ApprovalResult:
        if not self.is_waiting():
            raise ValueError(
                f"审批请求 {self.request_id} 非等待态（当前 {self.status}），不可重复裁决")
        self.status = decision
        self.result = ApprovalResult(
            request_id=self.request_id, decision=decision,
            comment=comment, decided_by=decided_by)
        return self.result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "subject": self.subject,
            "project_id": self.project_id,
            "status": self.status,
            "created_at": self.created_at,
            "payload": self.payload,
            "result": self.result.to_dict() if self.result else None,
        }


class ApprovalManager:
    """审批请求的登记与裁决管理。"""

    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}

    def create(self, subject: str, project_id: str = "",
               payload: Optional[Dict[str, Any]] = None) -> ApprovalRequest:
        req = ApprovalRequest(subject=subject, project_id=project_id,
                              payload=payload or {})
        self._requests[req.request_id] = req
        return req

    def get(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def approve(self, request_id: str, comment: str = "",
                decided_by: str = "user") -> ApprovalResult:
        return self._require(request_id).approve(comment, decided_by)

    def reject(self, request_id: str, comment: str = "",
               decided_by: str = "user") -> ApprovalResult:
        return self._require(request_id).reject(comment, decided_by)

    def pending(self) -> List[ApprovalRequest]:
        return [r for r in self._requests.values() if r.is_waiting()]

    def all(self) -> List[ApprovalRequest]:
        return list(self._requests.values())

    def _require(self, request_id: str) -> ApprovalRequest:
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"审批请求不存在: {request_id}")
        return req


__all__ = ["ApprovalStatus", "ApprovalRequest", "ApprovalResult", "ApprovalManager"]
