"""Design Agent 端到端 Pipeline 测试（Phase 4 §13 / §15）。

验证：Project 创建 → Parser → Design Agent → Schema Validation
→ Workspace(design_spec.json) → Checkpoint(checkpoint_design_v1.json) → Project Finished。
"""
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from runtime.config import load_runtime_config
from runtime.pipeline import Pipeline
from agents.design.validator import assert_valid


def _load_example(name: str):
    data = json.loads((REPO_ROOT / "examples" / "design" / name).read_text(encoding="utf-8"))
    return data["original_model"], data["requirement"]


def test_pipeline_runs_to_design_spec():
    tmp = tempfile.mkdtemp()
    cfg = load_runtime_config()
    cfg["workspace_root"] = str(Path(tmp) / "workspace")
    cfg["workspace_path"] = str(Path(tmp) / "workspace")
    cfg["log_dir"] = str(Path(tmp) / "logs")

    sample = REPO_ROOT / "examples" / "input" / "sample_json" / "sample.json"
    p = Pipeline("pipe_design", config=cfg)
    p.create()
    summary = p.run(input_path=str(sample),
                    requirement="三口之家，北欧风，预算中等，强收纳，居家办公")
    assert summary["status"] == "COMPLETED"
    assert summary["current_stage"] == "DESIGN_SPEC"
    assert summary["tasks"]["original_model-pipe_design"] == "COMPLETED"
    assert summary["tasks"]["design-pipe_design"] == "COMPLETED"

    proj_dir = Path(cfg["workspace_path"]) / "projects" / "pipe_design"
    ds = json.loads((proj_dir / "design_spec.json").read_text(encoding="utf-8"))
    assert_valid(ds)  # 落盘后的 DesignSpec 必须通过校验
    assert (proj_dir / "checkpoint_design_v1.json").exists()
    assert (proj_dir / "original_model.json").exists()


def test_design_direct_run_via_cli_like():
    """直接运行 Design Agent（run_design），验证 §14 `design` 子命令路径。"""
    tmp = tempfile.mkdtemp()
    cfg = load_runtime_config()
    cfg["workspace_root"] = str(Path(tmp) / "workspace")
    cfg["workspace_path"] = str(Path(tmp) / "workspace")
    cfg["log_dir"] = str(Path(tmp) / "logs")

    om, req = _load_example("three_room.json")
    # 先把 original_model 落盘（模拟已解析）
    proj_dir = Path(cfg["workspace_path"]) / "projects" / "direct_design"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "original_model.json").write_text(json.dumps(om, ensure_ascii=False),
                                                  encoding="utf-8")

    p = Pipeline("direct_design", config=cfg)
    summary = p.run_design(requirement=req)
    assert summary["status"] == "COMPLETED"
    assert summary["current_stage"] == "DESIGN_SPEC"
    ds = json.loads((proj_dir / "design_spec.json").read_text(encoding="utf-8"))
    assert_valid(ds)
