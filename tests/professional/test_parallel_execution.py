"""Parallel Stage Runner 单元测试（Phase 5 §8/§11）。

覆盖：Fan-out / Fan-in、部分失败、只重跑失败作业。
"""
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.orchestrator.agent import Result
from runtime.parallel import ParallelOutcome, ParallelStageRunner


def _ok(name: str):
    def job() -> Result:
        return Result(success=True, messages=[name])
    return job


def _fail(name: str):
    def job() -> Result:
        return Result(success=False, messages=[f"{name} failed"])
    return job


def test_fan_out_fan_in_all_success():
    runner = ParallelStageRunner()
    jobs = {f"agent{i}": _ok(f"agent{i}") for i in range(8)}
    results = runner.run_once(jobs)
    assert len(results) == 8
    assert all(r.success for r in results.values())


def test_jobs_actually_run_in_parallel():
    """8 个作业互相等待屏障：若非并行执行将超时失败。"""
    barrier = threading.Barrier(4, timeout=10)

    def job() -> Result:
        barrier.wait()
        return Result(success=True)

    runner = ParallelStageRunner()
    results = runner.run_once({f"j{i}": job for i in range(4)})
    assert all(r.success for r in results.values())


def test_partial_failure_does_not_affect_others():
    runner = ParallelStageRunner()
    jobs = {"a": _ok("a"), "b": _fail("b"), "c": _ok("c")}
    outcome = ParallelOutcome(results=runner.run_once(jobs))
    assert outcome.failed == ["b"]
    assert outcome.succeeded == ["a", "c"]
    assert outcome.all_success is False


def test_retry_only_failed_jobs():
    """失败作业单独重跑；成功作业不得重新执行（Phase 5 §8）。"""
    calls = {"good": 0, "flaky": 0}
    lock = threading.Lock()

    def good() -> Result:
        with lock:
            calls["good"] += 1
        return Result(success=True)

    def flaky() -> Result:
        with lock:
            calls["flaky"] += 1
        return Result(success=calls["flaky"] >= 2,
                      messages=["first attempt fails"])

    runner = ParallelStageRunner(max_retry=1)
    outcome = runner.run(jobs={"good": good, "flaky": flaky})
    assert outcome.all_success
    assert calls["good"] == 1, "成功作业不应被重跑"
    assert calls["flaky"] == 2, "失败作业应重跑一次"
    assert outcome.attempts["flaky"] == 2


def test_exception_in_job_becomes_failed_result():
    def boom() -> Result:
        raise RuntimeError("模拟作业崩溃")

    runner = ParallelStageRunner()
    results = runner.run_once({"boom": boom, "ok": _ok("ok")})
    assert results["boom"].success is False
    assert "模拟作业崩溃" in results["boom"].messages[0]
    assert results["ok"].success is True


def test_retry_exhausted_keeps_failure():
    runner = ParallelStageRunner(max_retry=2)
    outcome = runner.run(jobs={"always_bad": _fail("always_bad")})
    assert outcome.failed == ["always_bad"]
    assert outcome.attempts["always_bad"] == 3  # 1 + 2 次重跑
