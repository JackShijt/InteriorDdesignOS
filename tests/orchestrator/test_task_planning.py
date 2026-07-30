"""Phase 10 §8 · Task 自动生成测试。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.orchestrator.task_planner import ProjectRequirement, TaskPlanner  # noqa: E402


def _requirement():
    return ProjectRequirement(
        project_id="p-plan",
        initial_schemas=["DesignSpec"],
        target_schemas=["DrawingModel", "ValidationReport"],
        disciplines=["electrical", "lighting", "plumbing", "ceiling"],
    )


def test_plan_generates_expected_chain():
    tg = TaskPlanner().plan(_requirement())
    tasks = {t.task_id: t for t in tg.all_tasks()}
    for tid in ("layout_task", "geometry_task", "drawing_task", "validator_task",
                "electrical_task", "lighting_task", "plumbing_task", "ceiling_task"):
        assert tid in tasks, f"缺少任务 {tid}"


def test_dependencies_follow_dataflow():
    tg = TaskPlanner().plan(_requirement())
    tasks = {t.task_id: t for t in tg.all_tasks()}
    # 专业任务依赖 layout
    assert tasks["electrical_task"].dependencies == ["layout_task"]
    # geometry 依赖 layout
    assert tasks["geometry_task"].dependencies == ["layout_task"]
    # drawing 依赖 geometry
    assert "geometry_task" in tasks["drawing_task"].dependencies
    # validator 依赖 drawing + 所有专业任务
    val_deps = set(tasks["validator_task"].dependencies)
    assert "drawing_task" in val_deps
    assert {"electrical_task", "lighting_task", "plumbing_task",
            "ceiling_task"} <= val_deps


def test_professional_tasks_are_parallel():
    """专业任务彼此不互相依赖 -> 可并行。"""
    tg = TaskPlanner().plan(_requirement())
    tasks = {t.task_id: t for t in tg.all_tasks()}
    prof = ["electrical_task", "lighting_task", "plumbing_task", "ceiling_task"]
    for a in prof:
        for b in prof:
            if a != b:
                assert b not in tasks[a].dependencies


def test_disciplines_filter():
    req = _requirement()
    req.disciplines = ["electrical"]
    tg = TaskPlanner().plan(req)
    ids = {t.task_id for t in tg.all_tasks()}
    assert "electrical_task" in ids
    assert "lighting_task" not in ids
    assert "plumbing_task" not in ids


def test_no_cycles_and_topological_order():
    tg = TaskPlanner().plan(_requirement())
    seen = set()
    for t in tg.all_tasks():
        for dep in t.dependencies:
            assert dep in seen, f"{t.task_id} 依赖 {dep} 未在其之前定义（非拓扑序）"
        seen.add(t.task_id)
