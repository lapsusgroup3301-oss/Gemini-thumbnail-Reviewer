import logging
import time
from contextlib import contextmanager
from typing import Dict, Union

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

log = logging.getLogger("thumbnail-agent")

MetricValue = Union[int, float]
_metrics: Dict[str, MetricValue] = {}


def inc_metric(name: str, amount: int = 1) -> None:
    _metrics[name] = int(_metrics.get(name, 0)) + amount


def set_metric(name: str, value: MetricValue) -> None:
    _metrics[name] = value


def get_metrics_snapshot() -> Dict[str, MetricValue]:
    return dict(_metrics)


@contextmanager
def measure(name: str):
    start = time.time()
    try:
        yield
    finally:
        elapsed_ms = (time.time() - start) * 1000
        log.info(f"{name} took {elapsed_ms:.1f}ms")
        _metrics[f"time_ms_last_{name}"] = round(elapsed_ms, 1)
