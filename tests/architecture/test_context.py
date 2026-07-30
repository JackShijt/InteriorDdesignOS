"""
Phase 5.1 §11 · context_test

约束：
- Agent 只接受 AgentContext（run(context) 单参数签名）
- Agent 全部输入来自 Context（inputs / parameters），不自行查找文件
- AgentContext 含 Phase 5.1 §3 要求的字段
"""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from core.context import AgentContext
from professional import build_professional_agents

LAYOUT_EXAMPLE = REPO_ROOT / "schemas" / "examples" / "LayoutModel.example.json"


def _tmp_ws() -> Path:
    return Path(tempfile.mkdtemp()) / "workspace"


def test_agent_context_has_required_fields():
    """Phase 5.1 §3：AgentContext 必备字段。"""
    ctx = AgentContext(project_id="p", task_id="t")
    for attr in ("project_id", "task_id", "agent_name", "workspace",
                 "inputs", "outputs", "metadata"):
        assert hasattr(ctx, attr), f"AgentContext 缺少字段 {attr}"


def test_all_agents_run_accepts_only_context():
    """run 签名必须是 (self, context)。"""
    for agent in build_professional_agents(workspace_root=_tmp_ws()):
        params = list(inspect.signature(type(agent).run).parameters)
        assert params == ["self", "context"], (
            f"{agent.discipline}.run 签名必须为 (self, context)，实际 {params}")


def test_agent_reads_inline_layout_from_context():
    """输入通过 context.inputs 内联传递时，Agent 不接触任何输入文件。"""
    layout = json.loads(LAYOUT_EXAMPLE.read_text(encoding="utf-8"))
    ws = _tmp_ws()
    agent = build_professional_agents(workspace_root=ws,
                                      disciplines=["electrical"])[0]
    ctx = AgentContext(project_id="ctx1", task_id="t-ctx1",
                       stage="PROFESSIONAL_DEEPENING",
                       inputs={"layout": layout})
    result = agent.run(ctx)
    assert result.success, result.messages
    assert result.output_model["discipline"] == "ELECTRICAL"


def test_agent_uses_context_workspace():
    """context.workspace（项目工作区目录）优先于构造注入的根目录。"""
    layout = json.loads(LAYOUT_EXAMPLE.read_text(encoding="utf-8"))
    project_dir = Path(tempfile.mkdtemp()) / "proj-ctx"
    agent = build_professional_agents(disciplines=["plumbing"])[0]
    ctx = AgentContext(project_id="ctx2", task_id="t-ctx2",
                       stage="PROFESSIONAL_DEEPENING",
                       workspace=project_dir,
                       inputs={"layout": layout})
    result = agent.run(ctx)
    assert result.success, result.messages
    out = project_dir / "professional" / "plumbing_model.json"
    assert out.exists(), "输出必须写入 context.workspace 指定的项目工作区"
