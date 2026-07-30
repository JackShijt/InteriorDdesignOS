"""
Phase 5.1 §11 · artifact_test

约束：
- Agent 所有输出必须经 ArtifactManager（禁止在 professional/ 内直接
  json.dump / open(..., "w") 写工作区文件）
- ArtifactManager 提供 save / load / exists / archive / delete 与版本归档
"""
from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from core.artifact import ArtifactManager
from core.context import AgentContext
from professional import build_professional_agents

LAYOUT_EXAMPLE = REPO_ROOT / "schemas" / "examples" / "LayoutModel.example.json"


# --------------------------------------------------------------------------- #
# 静态检查：professional/ 内不得出现直接写文件
# --------------------------------------------------------------------------- #
def _write_call_violations() -> list[str]:
    violations: list[str] = []
    for pyfile in sorted((REPO_ROOT / "professional").rglob("*.py")):
        tree = ast.parse(pyfile.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name in ("dump",):  # json.dump 直接落盘
                violations.append(f"{pyfile.name}:{node.lineno} json.dump")
            if name == "open":
                for arg in node.args[1:2]:
                    if isinstance(arg, ast.Constant) and \
                            any(m in str(arg.value) for m in ("w", "a", "x")):
                        violations.append(
                            f"{pyfile.name}:{node.lineno} open(mode={arg.value})")
            if name == "write_text":
                violations.append(f"{pyfile.name}:{node.lineno} write_text")
    return violations


def test_professional_has_no_direct_file_writes():
    violations = _write_call_violations()
    assert not violations, (
        "professional/ 禁止直接写文件（必须经 ArtifactManager）：\n"
        + "\n".join(violations))


# --------------------------------------------------------------------------- #
# 行为检查：Agent 输出确实经 ArtifactManager 落盘
# --------------------------------------------------------------------------- #
def test_agent_output_goes_through_artifact_manager(monkeypatch=None):
    import pytest  # noqa: F401
    ws = Path(tempfile.mkdtemp()) / "workspace"
    calls: list[str] = []
    original_save = ArtifactManager.save

    def spy_save(self, name, data, archive_previous=True):
        calls.append(name)
        return original_save(self, name, data, archive_previous)

    ArtifactManager.save = spy_save
    try:
        agent = build_professional_agents(workspace_root=ws,
                                          disciplines=["electrical"])[0]
        ctx = AgentContext(project_id="art1", task_id="t-art1",
                           stage="PROFESSIONAL_DEEPENING",
                           parameters={"layout_path": str(LAYOUT_EXAMPLE)})
        result = agent.run(ctx)
    finally:
        ArtifactManager.save = original_save
    assert result.success, result.messages
    assert "professional/electrical_model.json" in calls, \
        "Agent 输出未经过 ArtifactManager.save"
    assert ctx.outputs.get("electrical_model"), "context.outputs 未回填输出路径"


def test_artifact_manager_lifecycle():
    root = Path(tempfile.mkdtemp()) / "proj"
    mgr = ArtifactManager(root)
    name = "professional/demo_model.json"

    assert mgr.exists(name) is False
    mgr.save(name, {"v": 1})
    assert mgr.exists(name) is True
    assert mgr.load(name) == {"v": 1}

    # save 自动归档旧版本
    mgr.save(name, {"v": 2})
    assert mgr.load(name) == {"v": 2}
    assert len(mgr.versions(name)) == 1

    # 手动归档 + 删除
    mgr.archive(name)
    assert len(mgr.versions(name)) == 2
    assert mgr.delete(name) is True
    assert mgr.exists(name) is False
    assert len(mgr.versions(name)) == 3  # 删除前再归档一次
