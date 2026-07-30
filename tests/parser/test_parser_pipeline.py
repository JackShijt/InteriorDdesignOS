"""Parser 端到端管线与集成测试（Phase 3 §9/§10/§12/§13/§16）。

覆盖：正常输入、空输入、错误输入、Schema 不合法、不存在文件、
Dispatcher 集成、Orchestrator 调度、统一 Result 返回。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.parser.exceptions import FatalError
from agents.parser.parser import ParserAgent, run_parser

REPO = Path(__file__).resolve().parent.parent.parent
EXAMPLES = REPO / "examples" / "input"


def test_run_parser_success_saves_files(tmp_path):
    ws = tmp_path / "ws"
    res = run_parser(EXAMPLES / "sample_json" / "sample.json",
                     project_id="t1", workspace_root=ws)
    assert res.success
    assert res.next_tasks == ["design"]
    assert res.output_model["metadata"]["project_id"] == "t1"

    om = ws / "projects" / "t1" / "original_model.json"
    cp = ws / "projects" / "t1" / "checkpoint_parser_v1.json"
    assert om.exists() and cp.exists()

    data = json.loads(om.read_text(encoding="utf-8"))
    assert data["metadata"]["project_id"] == "t1"
    # checkpoint 包含 stage / original_model / task_status / project_status
    cp_data = json.loads(cp.read_text(encoding="utf-8"))
    assert cp_data["stage"] == "ORIGINAL_MODEL"
    assert "original_model" in cp_data
    assert cp_data["task_status"]["parser"] == "COMPLETED"


def test_run_parser_image_empty_geometry(tmp_path):
    res = run_parser(EXAMPLES / "sample_image" / "sample.png",
                     project_id="img1", workspace_root=tmp_path / "ws")
    assert res.success
    assert res.output_model["walls"] == []
    # OriginalModel 顶层只有 6 个必填键
    assert set(res.output_model.keys()) == {
        "metadata", "units", "coordinates", "walls", "doors", "windows", "rooms"}


def test_run_parser_pdf_empty_geometry(tmp_path):
    res = run_parser(EXAMPLES / "sample_pdf" / "sample.pdf",
                     project_id="pdf1", workspace_root=tmp_path / "ws")
    assert res.success
    assert res.output_model["rooms"] == []


def test_run_parser_missing_file_raises():
    try:
        run_parser(EXAMPLES / "does_not_exist.dwg", project_id="x")
        raise AssertionError("应抛出 FatalError")
    except FatalError:
        pass


def test_run_parser_empty_input(tmp_path):
    # 空 txt 文件：可加载、识别为 TEXT、生成空几何 OriginalModel
    res = run_parser(EXAMPLES / "empty_project" / "empty.txt",
                     project_id="empty1", workspace_root=tmp_path / "ws")
    assert res.success
    assert res.output_model["walls"] == []


def test_dispatcher_runs_parser(tmp_path):
    from agents.orchestrator import AgentRegistry
    from agents.orchestrator.dispatcher import Dispatcher
    from agents.orchestrator.task_graph import TaskGraph
    from agents.orchestrator.context_manager import ContextManager
    from agents.orchestrator.checkpoint import Checkpoint
    from runtime.event_bus import EventBus
    from runtime.logger import UnifiedLogger
    from runtime.project_runtime import ProjectRuntime

    ws = tmp_path / "ws"
    logs = tmp_path / "logs"
    pid = "disp1"
    pr = ProjectRuntime(ws)
    pr.create(pid, "dispatch-test")
    g = TaskGraph()
    g.create_task(task_id="parser-1", agent="parser", stage="ORIGINAL_MODEL",
                 dependencies=[], input_refs=[str(EXAMPLES / "sample_json" / "sample.json")])
    g.update_status("parser-1", "READY")

    reg = AgentRegistry()
    reg.register(ParserAgent(workspace_root=ws, log_dir=logs))
    bus = EventBus(UnifiedLogger(log_dir=logs))
    cm = ContextManager(ws)
    cp = Checkpoint(cm, pr, bus, UnifiedLogger(log_dir=logs))
    disp = Dispatcher(pid, g, reg, cm, cp, bus, UnifiedLogger(log_dir=logs))

    res = disp.execute("parser-1")
    assert res is not None and res.success
    assert g.get_task("parser-1").status == "COMPLETED"
    assert (ws / "projects" / pid / "original_model.json").exists()
    assert (ws / "projects" / pid / "checkpoint_parser_v1.json").exists()


def test_orchestrator_schedules_parser(tmp_path):
    from agents.orchestrator import Orchestrator, AgentRegistry, StubAgent
    from runtime.project_runtime import STAGES

    ws = tmp_path / "ws"
    logs = tmp_path / "logs"
    reg = AgentRegistry()
    for s in STAGES:
        if s == "ORIGINAL_MODEL":
            reg.register(ParserAgent(workspace_root=ws, log_dir=logs))
        else:
            reg.register(StubAgent(agent_name=s.lower()))

    orch = Orchestrator("orch1", registry=reg, workspace_root=ws, log_dir=logs)
    orch.create_project()  # 构建默认 Task Graph 并存盘
    t = orch._graph.get_task("original_model-orch1")
    t.agent = "parser"
    t.input_refs = [str(EXAMPLES / "sample_json" / "sample.json")]
    orch._graph.save(orch._graph_path)  # 持久化修改，供 run() 重新加载

    summary = orch.run()
    assert summary["status"] == "COMPLETED"
    assert summary["tasks"]["original_model-orch1"] == "COMPLETED"
    assert (ws / "projects" / "orch1" / "original_model.json").exists()
