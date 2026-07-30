"""Phase 3.5 §8 Checkpoint 自动恢复测试。"""
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime import REPO_ROOT as R
from runtime.pipeline import Pipeline


def test_resume_continues_from_input_analysis():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        logs = ws / "logs"
        sample = R / "examples" / "input" / "sample_json" / "sample.json"
        p = Pipeline("rs1", workspace_root=ws, log_dir=logs)
        p.create()                       # CREATED / INITIALIZATION
        # 模拟中途崩溃：项目停留在 RUNNING / INPUT_ANALYSIS
        p.pr.set_state("rs1", "RUNNING")
        p.pr.set_stage("rs1", "INPUT_ANALYSIS")
        p._ensure_parser_task(str(sample))
        p.pr.update("rs1")

        summary = p.resume()
        assert summary["status"] == "COMPLETED"
        assert summary["current_stage"] == "DESIGN_SPEC"


def test_resume_of_completed_returns_completed():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        logs = ws / "logs"
        sample = R / "examples" / "input" / "sample_json" / "sample.json"
        p = Pipeline("rs2", workspace_root=ws, log_dir=logs)
        p.run(input_path=str(sample))
        summary = p.resume()
        assert summary["status"] == "COMPLETED"
