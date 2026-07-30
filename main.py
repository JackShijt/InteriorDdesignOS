"""
Phase 3.5 §10 / Phase 4 §14 统一 CLI。

仅调用 Runtime（Pipeline / status），不写任何业务逻辑。

用法：
  python main.py create <project_id>
  python main.py run <project_id> [--input <path>] [--requirement "<text>"]
  python main.py design <project_id> [--requirement "<text>"] [--input <original_model.json>]
  python main.py professional <project_id> [--layout <layout_model.json>] [--disciplines a,b,c]
  python main.py resume <project_id>
  python main.py status <project_id>
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from runtime.config import load_runtime_config
from runtime.pipeline import Pipeline
from runtime.status import report_status


def _usage() -> None:
    print("用法:")
    print("  python main.py create <project_id>")
    print("  python main.py run <project_id> [--input <path>] [--requirement \"<text>\"]")
    print("  python main.py design <project_id> [--requirement \"<text>\"] [--input <original_model.json>]")
    print("  python main.py professional <project_id> [--layout <layout_model.json>] [--disciplines a,b,c]")
    print("  python main.py cad <project_id> [--model <drawing_model.json>] [--backend mock]")
    print("  python main.py resume <project_id>")
    print("  python main.py status <project_id>")


def _opt(argv: list, name: str) -> str | None:
    if name in argv:
        idx = argv.index(name)
        return argv[idx + 1] if idx + 1 < len(argv) else None
    return None


def main(argv: list) -> int:
    if len(argv) < 2:
        _usage()
        return 1
    cmd = argv[1]
    if cmd not in ("create", "run", "design", "professional", "cad", "resume", "status"):
        _usage()
        return 1
    if len(argv) < 3:
        print("缺少 project_id")
        return 1
    project_id = argv[2]
    cfg = load_runtime_config()

    if cmd == "create":
        Pipeline(project_id, config=cfg).create()
        print(f"[OK] Project 已创建: {project_id} (state=CREATED)")
    elif cmd == "run":
        input_path = _opt(argv, "--input")
        requirement = _opt(argv, "--requirement")
        summary = Pipeline(project_id, config=cfg).run(
            input_path=input_path, requirement=requirement)
        print(f"[OK] Project 完成: {project_id} "
              f"state={summary['status']} stage={summary['current_stage']} "
              f"tasks={summary['tasks']}")
    elif cmd == "design":
        requirement = _opt(argv, "--requirement")
        input_path = _opt(argv, "--input")
        summary = Pipeline(project_id, config=cfg).run_design(
            requirement=requirement, original_model_path=input_path)
        print(f"[OK] Design Agent 完成: {project_id} "
              f"state={summary['status']} stage={summary['current_stage']} "
              f"tasks={summary['tasks']}")
    elif cmd == "professional":
        layout = _opt(argv, "--layout")
        disciplines_opt = _opt(argv, "--disciplines")
        disciplines = ([d.strip() for d in disciplines_opt.split(",") if d.strip()]
                       if disciplines_opt else None)
        summary = Pipeline(project_id, config=cfg).run_professional(
            layout_path=layout, disciplines=disciplines)
        print(f"[OK] Professional Stage 完成: {project_id} "
              f"state={summary['status']} stage={summary['current_stage']} "
              f"tasks={summary['tasks']}")
    elif cmd == "resume":
        summary = Pipeline(project_id, config=cfg).resume()
        print(f"[OK] Project 恢复: {project_id} "
              f"state={summary['status']} stage={summary['current_stage']}")
    elif cmd == "status":
        rep = report_status(project_id, config=cfg)
        print(rep)
    elif cmd == "cad":
        # Phase 7：经 CAD Framework 驱动（DrawingAgent → CommandQueue →
        # CADSession → CADAdapter）；backend 由 --backend 或 config/runtime.yaml
        # 的 cad.backend 决定，AutoCAD 连接参数从 config 注入（不写死）。
        from core.context import AgentContext
        from agents.drawing import DrawingAgent
        model = _opt(argv, "--model") or str(
            REPO_ROOT / "schemas" / "examples" / "DrawingModel.example.json")
        # --backend 优先；否则交由 DrawingAgent 从 cfg 解析
        cli_backend = _opt(argv, "--backend")
        workspace = REPO_ROOT / "workspace"
        ctx = AgentContext(project_id=project_id, task_id="cli-cad",
                           stage="DRAWING",
                           inputs={"drawing_model_path": model})
        agent = DrawingAgent(workspace_root=workspace, backend=cli_backend,
                             cad_config=cfg)
        backend = agent.backend
        res = agent.run(ctx)
        if res.success:
            print(f"[OK] CAD 命令队列经 {backend} 后端执行完成")
            print(f"     命令数: {ctx.outputs.get('command_count')}")
            print(f"     日志: {ctx.outputs.get('drawing_command_log')}")
        else:
            print(f"[FAIL] {res.messages}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
