"""Phase 3.5 §7 Workspace 自动更新测试。"""
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime import REPO_ROOT as R
from runtime.pipeline import Pipeline


def test_workspace_auto_updated():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        logs = ws / "logs"
        sample = R / "examples" / "input" / "sample_json" / "sample.json"
        p = Pipeline("ws1", workspace_root=ws, log_dir=logs)
        p.create()
        p.run(input_path=str(sample))
        d = ws / "projects" / "ws1"
        assert (d / "project.json").exists()
        assert (d / "task_graph.json").exists()
        assert (d / "original_model.json").exists()
