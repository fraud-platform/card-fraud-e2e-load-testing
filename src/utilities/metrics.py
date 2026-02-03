"""
Custom metrics collection for load testing.

Provides metrics collection and threshold monitoring for SLO enforcement.
"""

import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class MetricThreshold:
    """Threshold configuration for a metric."""

    metric_name: str
    p95_max_ms: float | None = None
    p99_max_ms: float | None = None
    error_rate_max: float | None = None
    rps_min: float | None = None


@dataclass
class MetricSnapshot:
    """Snapshot of metric statistics."""

    name: str
    count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    errors: int = 0
    timestamps: list[float] = field(default_factory=list)
    response_times: list[float] = field(default_factory=list)


class MetricsCollector:
    """
    Collects and aggregates custom metrics for load testing.

    Usage:
        metrics = MetricsCollector()
        metrics.init(environment)

        with metrics.timer("my_operation"):
            # do work

        metrics.increment("my_counter")
    """

    def __init__(self):
        self._metrics: dict[str, MetricSnapshot] = defaultdict(
            lambda: MetricSnapshot(name="unknown")
        )
        self._lock = threading.Lock()
        self._environment = None
        self._thresholds: list[MetricThreshold] = []
        self._violation_handlers: list[Callable] = []

    def init(self, environment):
        """Initialize the collector with the Locust environment."""
        self._environment = environment

    def add_threshold(self, threshold: MetricThreshold):
        """Add a threshold to monitor."""
        self._thresholds.append(threshold)

    def on_violation(self, handler: Callable):
        """Register a handler to be called when thresholds are violated."""
        self._violation_handlers.append(handler)

    def timer(self, metric_name: str):
        """Context manager for timing operations."""
        return TimerContext(self, metric_name)

    def record_time(self, metric_name: str, elapsed_ms: float, success: bool = True):
        """Record a timing measurement."""
        with self._lock:
            snapshot = self._metrics[metric_name]
            snapshot.name = metric_name
            snapshot.count += 1
            snapshot.total_time_ms += elapsed_ms
            snapshot.min_time_ms = min(snapshot.min_time_ms, elapsed_ms)
            snapshot.max_time_ms = max(snapshot.max_time_ms, elapsed_ms)
            snapshot.response_times.append(elapsed_ms)

            if not success:
                snapshot.errors += 1

    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter metric."""
        with self._lock:
            snapshot = self._metrics[metric_name]
            snapshot.name = metric_name
            snapshot.count += value

    def record_error(self, metric_name: str):
        """Record an error for a metric."""
        with self._lock:
            snapshot = self._metrics[metric_name]
            snapshot.name = metric_name
            snapshot.errors += 1

    def get_stats(self, metric_name: str) -> MetricSnapshot | None:
        """Get statistics for a metric."""
        with self._lock:
            return self._metrics.get(metric_name)

    def get_all_stats(self) -> dict[str, MetricSnapshot]:
        """Get all metric statistics."""
        with self._lock:
            return dict(self._metrics)

    def check_thresholds(self) -> list[dict]:
        """Check all thresholds and return violations."""
        violations = []

        for threshold in self._thresholds:
            stats = self.get_stats(threshold.metric_name)
            if not stats or stats.count == 0:
                continue

            # Calculate percentiles
            sorted_times = sorted(stats.response_times)
            n = len(sorted_times)

            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)

            p95 = sorted_times[p95_idx] if n > 0 else 0
            p99 = sorted_times[p99_idx] if n > 0 else 0
            error_rate = stats.errors / stats.count if stats.count > 0 else 0

            # Check thresholds
            if threshold.p95_max_ms and p95 > threshold.p95_max_ms:
                violations.append(
                    {
                        "metric": threshold.metric_name,
                        "threshold": "p95",
                        "limit_ms": threshold.p95_max_ms,
                        "actual_ms": p95,
                    }
                )

            if threshold.p99_max_ms and p99 > threshold.p99_max_ms:
                violations.append(
                    {
                        "metric": threshold.metric_name,
                        "threshold": "p99",
                        "limit_ms": threshold.p99_max_ms,
                        "actual_ms": p99,
                    }
                )

            if threshold.error_rate_max and error_rate > threshold.error_rate_max:
                violations.append(
                    {
                        "metric": threshold.metric_name,
                        "threshold": "error_rate",
                        "limit": threshold.error_rate_max,
                        "actual": error_rate,
                    }
                )

        # Notify handlers
        for handler in self._violation_handlers:
            handler(violations)

        return violations

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, metric_name: str):
        self.collector = collector
        self.metric_name = metric_name
        self.start_time = None
        self.success = True

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.perf_counter() - self.start_time) * 1000
        if exc_type is not None:
            self.success = False
        self.collector.record_time(self.metric_name, elapsed_ms, self.success)
        return False  # Don't suppress exceptions


# Global singleton instance
metrics_collector = MetricsCollector()
