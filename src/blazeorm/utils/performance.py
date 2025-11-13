"""
Performance tracking utilities and N+1 query detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Sequence


@dataclass
class QueryStat:
    sql: str
    count: int = 0
    total_ms: float = 0.0
    fingerprints: set[str] = field(default_factory=set)
    samples: List[str] = field(default_factory=list)

    def record(self, fingerprint: str, elapsed_ms: float, *, sample_limit: int) -> None:
        self.count += 1
        self.total_ms += elapsed_ms
        if fingerprint:
            if fingerprint not in self.fingerprints:
                self.fingerprints.add(fingerprint)
                if len(self.samples) < sample_limit:
                    self.samples.append(fingerprint)

    @property
    def average_ms(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_ms / self.count


class PerformanceTracker:
    """
    Tracks executed queries and emits warnings for potential N+1 patterns.
    """

    def __init__(
        self,
        logger: logging.Logger,
        *,
        n_plus_one_threshold: int = 5,
        sample_size: int = 5,
    ) -> None:
        self.logger = logger
        self.n_plus_one_threshold = n_plus_one_threshold
        self.sample_size = sample_size
        self.stats: dict[str, QueryStat] = {}
        self._reported: set[str] = set()

    def record(self, sql: str, params: Sequence[object], elapsed_ms: float) -> None:
        normalized_sql = self._normalize_sql(sql)
        fingerprint = self._fingerprint(params)
        stat = self.stats.setdefault(normalized_sql, QueryStat(sql=normalized_sql))
        stat.record(fingerprint, elapsed_ms, sample_limit=self.sample_size)
        if self._should_report(stat):
            self._report(normalized_sql, stat)

    def summary(self) -> List[dict[str, object]]:
        return [
            {
                "sql": stat.sql,
                "count": stat.count,
                "total_ms": stat.total_ms,
                "average_ms": stat.average_ms,
                "distinct_params": len(stat.fingerprints),
            }
            for stat in self.stats.values()
        ]

    def reset(self) -> None:
        self.stats.clear()
        self._reported.clear()

    def _should_report(self, stat: QueryStat) -> bool:
        if stat.count < self.n_plus_one_threshold:
            return False
        if len(stat.fingerprints) < 2:
            return False
        if stat.sql in self._reported:
            return False
        return True

    def _report(self, sql: str, stat: QueryStat) -> None:
        self._reported.add(sql)
        self.logger.warning(
            "Potential N+1 detected for SQL '%s' (%s executions, %s distinct params)",
            self._abbreviate(sql),
            stat.count,
            len(stat.fingerprints),
            extra={"sql": sql, "count": stat.count, "distinct_params": len(stat.fingerprints)},
        )

    @staticmethod
    def _normalize_sql(sql: str) -> str:
        return " ".join(sql.strip().split())

    @staticmethod
    def _fingerprint(params: Sequence[object]) -> str:
        if not params:
            return ""
        normalized = []
        for value in params:
            if isinstance(value, (list, tuple)):
                normalized.append(tuple(value))
            elif isinstance(value, dict):
                normalized.append(tuple(sorted(value.items())))
            else:
                normalized.append(value)
        return repr(tuple(normalized))

    @staticmethod
    def _abbreviate(sql: str, max_length: int = 80) -> str:
        if len(sql) <= max_length:
            return sql
        return sql[: max_length - 3] + "..."
