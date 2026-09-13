"""Phase 8.1 — Load Test + Performance Gate — TDD RED"""
import importlib.util
import pathlib
import statistics

import pytest

REPO_ROOT = pathlib.Path(__file__).parents[4]
BENCH_FILE = REPO_ROOT / "bench" / "load_test.py"


def test_bench_file_exists():
    assert BENCH_FILE.exists(), "bench/load_test.py must exist (8.1)"


def test_bench_defines_locust_user():
    """Locust TaxonomyUser must exist with required tasks."""
    spec = importlib.util.spec_from_file_location("bench.load_test", str(BENCH_FILE))
    assert spec and spec.loader, "cannot load bench/load_test.py"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    # Must have user class (Locust HttpUser fallback allowed)
    has_user = any(
        "User" in name for name in dir(mod) if "User" in name or "Task" in name
    )
    # Also check for at least expected attributes: tasks or task_set or methods for public endpoints
    assert has_user or hasattr(mod, "TaxonomyUser") or hasattr(mod, "PublicApiUser"), "bench must define a User class"
    # Check required endpoints referenced in file content
    text = BENCH_FILE.read_text(encoding="utf-8")
    for endpoint in ["/api/v1/models", "/api/v1/categories", "/api/v1/providers", "/api/v1/locales"]:
        assert endpoint in text, f"bench must reference {endpoint}"
    assert "100" in text or "concurrent" in text.lower(), "bench must mention 100 concurrent users"
    assert "300" in text or "5 min" in text.lower() or "5min" in text.lower() or "t 300" in text, "bench must mention 5 min duration"


def test_bench_defines_seed_10k():
    text = BENCH_FILE.read_text(encoding="utf-8")
    assert "10" in text and ("seed" in text.lower() or "10k" in text.lower() or "10000" in text), "bench must support seeding 10k models"
    assert "p95" in text.lower() or "p_95" in text.lower() or "percentile" in text.lower(), "bench must check p95 gate"


def test_p95_helper_logic():
    """Verify p95 calculation helper meets spec p95 < 200ms."""
    spec = importlib.util.spec_from_file_location("bench.load_test", str(BENCH_FILE))
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    # Find p95 helper
    p95_fn = None
    for name in ["calculate_p95", "calc_p95", "p95", "percentile", "compute_p95"]:
        if hasattr(mod, name):
            p95_fn = getattr(mod, name)
            break
    if p95_fn is None:
        # Fallback: check that bench exposes a function that computes percentile
        # Search any callable containing percentile logic
        candidates = [getattr(mod, n) for n in dir(mod) if callable(getattr(mod, n))]
        for c in candidates:
            try:
                src = getattr(c, "__code__", None)
                if src and "quantile" in str(src.co_consts).lower() or "percentile" in str(src.co_consts).lower():
                    p95_fn = c
                    break
            except Exception:
                pass
    assert p95_fn is not None, "bench must expose a p95 calculation helper"
    # Verify correct calculation: 100 values 0..99 => p95 ~ 95
    latencies = list(range(100))
    result = p95_fn(latencies)  # type: ignore
    # Allow small variance for different percentile methods
    assert 94 <= result <= 96, f"p95 of 0..99 should be ~95, got {result}"
    # p95 < 200ms gate check helper
    if hasattr(mod, "is_within_slo"):
        assert mod.is_within_slo([50] * 100) is True
        assert mod.is_within_slo([300] * 100) is False


def test_bench_has_ci_gate():
    text = BENCH_FILE.read_text(encoding="utf-8")
    # Must have CI gate logic: exit non-zero or assert on p95 >200
    assert "200" in text, "bench must gate on 200ms"
    assert ("assert" in text or "exit" in text or "sys.exit" in text or "gate" in text.lower()), "bench must have gate enforcement"


def test_performance_gate_runs_fast():
    """Simulated performance gate with TestClient should pass with small dataset (<200ms p95)."""
    import time
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import event as sa_event, text as sa_text
    from sqlalchemy.orm import sessionmaker
    from app.db.session import Base, get_session
    from app.taxonomy.api.public import router as public_router
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.taxonomy.models.entities import AIModel, Provider, TaxonomyVersion

    async def setup():
        eng = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return eng

    import asyncio

    eng = asyncio.run(setup())

    async def seed_small():
        async_session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            prov = Provider(id=str(uuid.uuid4()), slug="bench-prov", name="Bench", status="active")
            s.add(prov)
            await s.flush()
            tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
            s.add(tv)
            await s.flush()
            for i in range(20):
                m = AIModel(
                    id=str(uuid.uuid4()),
                    provider_id=prov.id,
                    slug=f"bench-model-{i}",
                    display_name=f"Bench Model {i}",
                    modality=["text"],
                    status="approved",
                    source="manual",
                    source_payload_hash=str(uuid.uuid4()),
                    input_price_per_mtok=Decimal("1.00"),
                )
                s.add(m)
            await s.commit()

    asyncio.run(seed_small())

    app = FastAPI()
    app.include_router(public_router, prefix="/api/v1")

    async def override():
        async_session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            yield s

    app.dependency_overrides[get_session] = override
    client = TestClient(app)

    latencies = []
    for _ in range(20):
        start = time.perf_counter()
        r = client.get("/api/v1/models?limit=20")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert r.status_code == 200
        latencies.append(elapsed_ms)

    latencies.sort()
    idx = int(0.95 * len(latencies))
    p95 = latencies[idx] if latencies else 0
    # With in-memory sqlite and 20 models, p95 should be well under 200ms
    assert p95 < 200, f"p95 {p95:.2f}ms exceeds 200ms gate"
