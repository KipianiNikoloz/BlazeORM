"""
Performance tracking utilities and N+1 query detection.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Sequence

SLOW_QUERY_ENV_VAR = "BLAZE_SLOW_QUERY_MS"


def _validate_slow_query_ms(value: int, *, source: str) -> int:
    if value < 0:
        raise ValueError(f"{source} must be >= 0, got {value}.")
    return value


def _parse_slow_query_ms(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid {SLOW_QUERY_ENV_VAR} value {value!r}; must be an integer."
        ) from exc
    return _validate_slow_query_ms(parsed, source=SLOW_QUERY_ENV_VAR)


def resolve_slow_query_ms(*, default: int, override: int | None) -> int:
    if override is not None:
        return _validate_slow_query_ms(override, source="slow_query_ms")
    env_value = os.getenv(SLOW_QUERY_ENV_VAR)
    if env_value is None:
        return _validate_slow_query_ms(default, source="default slow_query_ms")
    return _parse_slow_query_ms(env_value)


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
        return self.export()

    def export(self, *, include_samples: bool = False) -> List[dict[str, object]]:
        payload: List[dict[str, object]] = []
        for stat in self.stats.values():
            row = {
                "sql": stat.sql,
                "count": stat.count,
                "total_ms": stat.total_ms,
                "average_ms": stat.average_ms,
                "distinct_params": len(stat.fingerprints),
            }
            if include_samples:
                row["samples"] = list(stat.samples)
            payload.append(row)
        return payload

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
        normalized: list[object] = []
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
