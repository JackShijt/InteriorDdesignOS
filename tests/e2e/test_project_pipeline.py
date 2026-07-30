"""Phase 4 端到端 Pipeline 验收（§15）。

创建 Project → Parser → Workspace → Checkpoint → Design Agent → DesignSpec → Project 完成。
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime.config import load_runtime_config
from runtime.pipeline import Pipeline
from agents.design.validator import assert_valid


def test_project_pipeline_end_to_end():
    import tempfile
    tmp = tempfile.mkdtemp()
    cfg = load_runtime_config()
    cfg["workspace_root"] = str(Path(tmp) / "workspace")
    cfg["workspace_path"] = str(Path(tmp) / "workspace")
    cfg["log_dir"] = str(Path(tmp) / "logs")

    sample = REPO_ROOT / "examples" / "input" / "sample_json" / "sample.json"
    p = Pipeline("e2e_design", config=cfg)
    p.create()
    summary = p.run(input_path=str(sample),
                    requirement="三口之家，北欧风，预算中等，强收纳，居家办公")

    # 完成标准
    assert summary["status"] == "COMPLETED"
    assert summary["current_stage"] == "DESIGN_SPEC"
    assert summary["tasks"]["original_model-e2e_design"] == "COMPLETED"
    assert summary["tasks"]["design-e2e_design"] == "COMPLETED"

    proj_dir = Path(cfg["workspace_path"]) / "projects" / "e2e_design"
    assert (proj_dir / "original_model.json").exists()
    assert (proj_dir / "design_spec.json").exists()
    assert (proj_dir / "checkpoint_design_v1.json").exists()
    assert (proj_dir / "checkpoint_pipeline_v1.json").exists()

    ds = json.loads((proj_dir / "design_spec.json").read_text(encoding="utf-8"))
    assert_valid(ds)
    assert ds["version"] == "v1"
    assert ds["style"]["labels"]  # 至少 1 个风格标签
