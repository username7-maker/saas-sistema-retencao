"""Read-only connectivity benchmark for the Supabase session/transaction poolers."""

from __future__ import annotations

import os
from statistics import median
from time import perf_counter

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def benchmark(port: int, iterations: int = 5) -> dict[str, object]:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        return {"port": port, "status": "missing_database_url"}
    url = make_url(database_url).set(port=port)
    timings: list[float] = []
    try:
        for _ in range(iterations):
            engine = create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 8})
            started_at = perf_counter()
            with engine.connect() as connection:
                connection.execute(text("select 1"))
            timings.append((perf_counter() - started_at) * 1000)
            engine.dispose()
    except Exception as exc:
        return {"port": port, "status": "failed", "error_type": type(exc).__name__}
    return {
        "port": port,
        "status": "ok",
        "median_ms": round(median(timings), 2),
        "min_ms": round(min(timings), 2),
        "max_ms": round(max(timings), 2),
        "samples": len(timings),
    }


if __name__ == "__main__":
    for candidate_port in (5432, 6543):
        print(benchmark(candidate_port))
