"""
InteriorDesignOS · Parallel Stage Runner（Phase 5 §8）

通用并行阶段执行器：
  Parallel Fan-out（并发提交全部作业）
    ↓
  Parallel Fan-in（等待全部完成）

特性：
- 支持部分失败：单个作业失败不影响其它作业
- 支持只重跑失败作业（retry_failed），无需重新执行成功者
- 作业内异常一律捕获并转为失败 Result（框架安全）

本模块与具体 Agent 解耦（SRP）：作业是 () -> Result 的可调用对象。
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from agents.orchestrator.agent import Result

logger = logging.getLogger(__name__)

Job = Callable[[], Result]


@dataclass
class ParallelOutcome:
    """一次并行阶段执行的聚合结果（Fan-in 产物）。"""
    results: Dict[str, Result] = field(default_factory=dict)
    attempts: Dict[str, int] = field(default_factory=dict)

    @property
    def failed(self) -> List[str]:
        return sorted(k for k, r in self.results.items() if not r.success)

    @property
    def succeeded(self) -> List[str]:
        return sorted(k for k, r in self.results.items() if r.success)

    @property
    def all_success(self) -> bool:
        return bool(self.results) and not self.failed


class ParallelStageRunner:
    """并行阶段执行器（Fan-out / Fan-in + 失败重跑）。"""

    def __init__(self, max_workers: Optional[int] = None,
                 max_retry: int = 1):
        """max_retry：失败作业的额外重跑次数（只重跑失败者）。"""
        self._max_workers = max_workers
        self._max_retry = max(0, max_retry)

    # ---- Fan-out / Fan-in ----
    def run_once(self, jobs: Dict[str, Job]) -> Dict[str, Result]:
        """并发执行全部作业，等待全部完成（不重试）。"""
        if not jobs:
            return {}
        results: Dict[str, Result] = {}
        workers = self._max_workers or len(jobs)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(self._safe_call, job): name
                          for name, job in jobs.items()}
            for future in as_completed(future_map):
                name = future_map[future]
                results[name] = future.result()
                logger.info("parallel job finished: %s success=%s",
                            name, results[name].success)
        return results

    def run(self, jobs: Dict[str, Job]) -> ParallelOutcome:
        """执行全部作业；失败者按 max_retry 只重跑失败部分。"""
        outcome = ParallelOutcome()
        outcome.results = self.run_once(jobs)
        for name in jobs:
            outcome.attempts[name] = 1
        retries = 0
        while retries < self._max_retry and outcome.failed:
            retries += 1
            failed = outcome.failed
            logger.info("retrying failed parallel jobs (round %d): %s",
                        retries, failed)
            retried = self.retry_failed(jobs, outcome)
            for name in retried:
                outcome.attempts[name] = outcome.attempts.get(name, 0) + 1
        return outcome

    def retry_failed(self, jobs: Dict[str, Job],
                     outcome: ParallelOutcome) -> List[str]:
        """只重跑失败作业，成功作业保持原结果不动。返回重跑的作业名。"""
        failed = outcome.failed
        subset = {name: jobs[name] for name in failed if name in jobs}
        if not subset:
            return []
        new_results = self.run_once(subset)
        outcome.results.update(new_results)
        return sorted(subset)

    # ---- 内部 ----
    @staticmethod
    def _safe_call(job: Job) -> Result:
        """作业异常转失败 Result（框架内不向上抛）。"""
        try:
            result = job()
            if not isinstance(result, Result):
                return Result(success=False,
                              messages=["作业未返回统一 Result 对象"])
            return result
        except Exception as exc:  # noqa: BLE001 框架安全兜底
            logger.exception("parallel job raised")
            return Result(success=False, messages=[str(exc) or "作业异常"])


__all__ = ["ParallelStageRunner", "ParallelOutcome", "Job"]
