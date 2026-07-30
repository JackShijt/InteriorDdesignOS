"""Phase 3.5 Pipeline 全流程测试（含生命周期、阶段、事件）。"""
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime import REPO_ROOT as R
from runtime.pipeline import Pipeline, SUPPORTED_STAGES


def test_pipeline_runs_to_completion():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        logs = ws / "logs"
        sample = R / "examples" / "input" / "sample_json" / "sample.json"
        p = Pipeline("pl1", workspace_root=ws, log_dir=logs)
        p.create()
        summary = p.run(input_path=str(sample),
                        requirement="三口之家，北欧风，预算中等，强收纳，居家办公")
        assert summary["status"] == "COMPLETED"
        assert summary["current_stage"] == "DESIGN_SPEC"
        assert summary["tasks"]["original_model-pl1"] == "COMPLETED"
        assert summary["tasks"]["design-pl1"] == "COMPLETED"


def test_pipeline_emits_required_events():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        logs = ws / "logs"
        sample = R / "examples" / "input" / "sample_json" / "sample.json"
        p = Pipeline("pl2", workspace_root=ws, log_dir=logs)
        p.create()
        summary = p.run(input_path=str(sample),
                        requirement="北欧风，预算中等")
        types = set(summary["events"])
        for req in ("ProjectCreated", "ProjectStarted", "StageStarted",
                    "StageCompleted", "TaskStarted", "TaskCompleted",
                    "CheckpointSaved", "WorkspaceUpdated", "ProjectCompleted"):
            assert req in types, f"缺少事件: {req}"


def test_stages_supported_four():
    assert SUPPORTED_STAGES == ["INITIALIZATION", "INPUT_ANALYSIS",
                                "ORIGINAL_MODEL", "DESIGN_SPEC"]
