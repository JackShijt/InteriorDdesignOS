"""Phase 3.5 §8 Checkpoint 自动保存测试。"""
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime import REPO_ROOT as R
from runtime.pipeline import Pipeline


def test_checkpoint_saved():
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        logs = ws / "logs"
        sample = R / "examples" / "input" / "sample_json" / "sample.json"
        p = Pipeline("ck1", workspace_root=ws, log_dir=logs)
        p.run(input_path=str(sample))
        d = ws / "projects" / "ck1"
        # Pipeline 检查点 + Parser 检查点
        assert (d / "checkpoint_pipeline_v1.json").exists()
        assert (d / "checkpoint_parser_v1.json").exists()
