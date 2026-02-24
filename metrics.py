#!/usr/bin/env python3
"""
metrics.py — Prometheus Metrics
================================
Exposes application metrics in Prometheus format.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Dict

import config

# In-memory counters (swap for prometheus_client in production)
_counters: Dict[str, int] = {
    "emails_sent_total": 0,
    "emails_received_total": 0,
    "emails_failed_total": 0,
    "auth_login_total": 0,
    "auth_login_failed_total": 0,
    "auth_register_total": 0,
    "crypto_operations_total": 0,
    "tamper_detected_total": 0,
    "replay_detected_total": 0,
    "forge_detected_total": 0,
}

_histograms: Dict[str, list] = {
    "request_duration_seconds": [],
    "crypto_operation_duration_seconds": [],
}


def inc(name: str, value: int = 1) -> None:
    """Increment a counter metric."""
    if name in _counters:
        _counters[name] += value


def observe(name: str, value: float) -> None:
    """Record a histogram observation."""
    if name in _histograms:
        _histograms[name].append(value)
        if len(_histograms[name]) > 10000:
            _histograms[name] = _histograms[name][-5000:]


def track_time(metric_name: str) -> Callable:
    """Decorator to track function execution time."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return f(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                observe(metric_name, duration)
        return wrapper
    return decorator


def get_metrics() -> Dict[str, Any]:
    """Return all metrics as a dict."""
    result: Dict[str, Any] = {}
    for name, value in _counters.items():
        result[name] = value
    for name, values in _histograms.items():
        if values:
            sorted_v = sorted(values)
            count = len(sorted_v)
            result[f"{name}_count"] = count
            result[f"{name}_sum"] = sum(sorted_v)
            result[f"{name}_p50"] = sorted_v[int(count * 0.5)]
            result[f"{name}_p99"] = sorted_v[int(count * 0.99)]
        else:
            result[f"{name}_count"] = 0
    return result


def render_prometheus() -> str:
    """Render metrics in Prometheus text exposition format."""
    lines = []
    for name, value in _counters.items():
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")
    for name, values in _histograms.items():
        if values:
            sorted_v = sorted(values)
            count = len(sorted_v)
            lines.append(f"# TYPE {name} histogram")
            lines.append(f'{name}_count {count}')
            lines.append(f'{name}_sum {sum(sorted_v):.6f}')
            lines.append(f'{name}{{quantile="0.5"}} {sorted_v[int(count * 0.5)]:.6f}')
            lines.append(f'{name}{{quantile="0.99"}} {sorted_v[int(count * 0.99)]:.6f}')
    return "\n".join(lines) + "\n"
