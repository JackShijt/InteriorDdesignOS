"""Phase 3.5 §9 EventBus 事件测试。"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime.message import Event, EventType
from runtime.event_bus import EventBus
from runtime.logger import UnifiedLogger

EXPECTED_VALUES = {
    "PROJECT_CREATED": "ProjectCreated",
    "PROJECT_STARTED": "ProjectStarted",
    "STAGE_STARTED": "StageStarted",
    "STAGE_COMPLETED": "StageCompleted",
    "TASK_COMPLETED": "TaskCompleted",
    "CHECKPOINT_SAVED": "CheckpointSaved",
    "WORKSPACE_UPDATED": "WorkspaceUpdated",
    "PROJECT_COMPLETED": "ProjectCompleted",
    "PROJECT_FAILED": "ProjectFailed",
}


def test_new_event_types_exist():
    for name, value in EXPECTED_VALUES.items():
        assert hasattr(EventType, name)
        assert EventType[name].value == value


def test_publish_subscribe():
    bus = EventBus(UnifiedLogger())
    got = []
    bus.subscribe(EventType.STAGE_STARTED, lambda ev: got.append(ev))
    bus.publish(Event(EventType.STAGE_STARTED, {"project_id": "p"}))
    assert len(got) == 1
    assert got[0].payload["project_id"] == "p"
