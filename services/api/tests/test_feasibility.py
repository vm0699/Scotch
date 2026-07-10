"""Phase 40 — Feasibility / Yield Analysis tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.feasibility.engine import FeasibilityEngine, _setback
from app.core.feasibility.options import OptionGenerator
from app.core.models.project import ArchitectureProject, Feasibility
from app.core.storage.local_store import LocalProjectStore
import app.core.chat_tools as ct


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def store(tmp_path: Path) -> LocalProjectStore:
    return LocalProjectStore(tmp_path)


@pytest.fixture()
def pid(store: LocalProjectStore) -> str:
    entry = store.create_project("Feasibility Test", prompt="2BHK")
    req = parse_prompt("2BHK east-facing 30x50ft")
    project, _ = generate_floorplan(req)
    store.update_project(entry.id, project=project, change_type="generate")
    return entry.id


def _patch(store: LocalProjectStore):
    ct._store = lambda: store  # type: ignore[attr-defined]


# ── Setback table ─────────────────────────────────────────────────────────────


def test_setback_40ft_road():
    f, s, r = _setback(40.0)
    assert f == 15.0
    assert s == 5.0
    assert r == 10.0


def test_setback_30ft_road():
    f, s, r = _setback(30.0)
    assert f == 12.0


def test_setback_default():
    f, s, r = _setback(0.0)
    assert f == 7.0


def test_setback_exact_threshold():
    # 20 ft road uses 20.0 tier
    f, s, r = _setback(20.0)
    assert f == 9.0


# ── FeasibilityEngine ─────────────────────────────────────────────────────────


def _make_project(w=30, d=50, floors=1) -> ArchitectureProject:
    req = parse_prompt(f"2BHK east-facing {w}x{d}ft")
    project, _ = generate_floorplan(req)
    return project.model_copy(update={"building": project.building.model_copy(update={"floors": floors})})


def test_engine_returns_feasibility():
    proj = _make_project()
    result = FeasibilityEngine().compute(proj)
    assert isinstance(result, Feasibility)
    assert result.generated is True


def test_engine_site_area_correct():
    proj = _make_project(30, 50)
    result = FeasibilityEngine().compute(proj)
    assert result.site_area == pytest.approx(1500.0, abs=1)


def test_engine_usable_footprint_less_than_site():
    proj = _make_project(30, 50)
    result = FeasibilityEngine().compute(proj)
    assert result.usable_footprint < result.site_area


def test_engine_coverage_pct_positive():
    proj = _make_project(30, 50)
    result = FeasibilityEngine().compute(proj)
    assert 0 < result.coverage_pct <= 100


def test_engine_buildable_area_site_times_fsi():
    proj = _make_project(30, 50)
    result = FeasibilityEngine().compute(proj)
    assert result.buildable_area == pytest.approx(result.site_area * result.fsi_far, abs=1)


def test_engine_with_road_width():
    proj = _make_project(30, 50)
    result = FeasibilityEngine().compute(proj, road_width_ft=40.0)
    assert result.road_width_ft == 40.0
    assert not result.missing_inputs  # road_width provided so not in missing


def test_engine_no_road_width_missing_input():
    proj = _make_project(30, 50)
    result = FeasibilityEngine().compute(proj, road_width_ft=0.0)
    assert "road_width_ft" in result.missing_inputs


def test_engine_five_options():
    proj = _make_project(30, 50)
    result = FeasibilityEngine().compute(proj)
    assert len(result.options) == 5


def test_engine_option_names():
    proj = _make_project(30, 50)
    result = FeasibilityEngine().compute(proj)
    names = {opt.name for opt in result.options}
    assert names == {"compact", "balanced", "spacious", "future_expansion", "rental_friendly"}


def test_engine_parking_estimate_at_least_one():
    proj = _make_project(20, 30)
    result = FeasibilityEngine().compute(proj)
    assert result.parking_estimate >= 1


def test_engine_needs_review_true():
    proj = _make_project()
    result = FeasibilityEngine().compute(proj)
    assert result.needs_review is True


def test_engine_confidence_range():
    proj = _make_project()
    result = FeasibilityEngine().compute(proj)
    assert 0.0 < result.confidence <= 1.0


def test_engine_assumptions_not_empty():
    proj = _make_project()
    result = FeasibilityEngine().compute(proj)
    assert len(result.assumptions) >= 1


# ── OptionGenerator ───────────────────────────────────────────────────────────


def test_option_generator_returns_five():
    gen = OptionGenerator()
    opts = gen.generate(site_area=1500, usable_footprint=876, buildable_area=2250, max_floors=2, parking_slots=2)
    assert len(opts) == 5


def test_compact_option_unit_type():
    gen = OptionGenerator()
    opts = gen.generate(1500, 876, 2250, 2, 2)
    compact = next(o for o in opts if o.name == "compact")
    assert compact.unit_type == "1BHK"
    assert compact.unit_count >= 1


def test_balanced_option_unit_type():
    gen = OptionGenerator()
    opts = gen.generate(1500, 876, 2250, 2, 2)
    balanced = next(o for o in opts if o.name == "balanced")
    assert balanced.unit_type == "2BHK"


def test_rental_option_highest_unit_count():
    gen = OptionGenerator()
    opts = gen.generate(1500, 876, 2250, 2, 2)
    rental = next(o for o in opts if o.name == "rental_friendly")
    compact = next(o for o in opts if o.name == "compact")
    # rental-friendly (studios) should have >= compact (1BHK) unit count
    assert rental.unit_count >= compact.unit_count


def test_future_expansion_single_unit():
    gen = OptionGenerator()
    opts = gen.generate(1500, 876, 2250, 2, 2)
    future = next(o for o in opts if o.name == "future_expansion")
    assert future.unit_count == 1


def test_options_have_trade_offs():
    gen = OptionGenerator()
    opts = gen.generate(1500, 876, 2250, 2, 2)
    for opt in opts:
        assert len(opt.trade_offs) >= 1


# ── Model roundtrip ───────────────────────────────────────────────────────────


def test_feasibility_inline_in_project():
    proj = _make_project()
    result = FeasibilityEngine().compute(proj)
    updated = proj.model_copy(update={"feasibility": result})
    dumped = updated.model_dump()
    assert "feasibility" in dumped
    assert dumped["feasibility"]["generated"] is True


def test_empty_project_feasibility_default():
    proj = _make_project()
    assert proj.feasibility.generated is False
    assert proj.feasibility.site_area == 0.0


# ── Chat tools ────────────────────────────────────────────────────────────────


def test_run_feasibility_tool(store, pid):
    _patch(store)
    result = ct.run_feasibility(pid)
    assert isinstance(result, dict)
    assert result["generated"] is True
    assert len(result["options"]) == 5


def test_run_feasibility_with_road_width(store, pid):
    _patch(store)
    result = ct.run_feasibility(pid, road_width_ft=40.0)
    assert result["road_width_ft"] == 40.0
    assert "road_width_ft" not in result["missing_inputs"]


def test_compare_feasibility_options_tool(store, pid):
    _patch(store)
    result = ct.compare_feasibility_options(pid)
    assert "options" in result
    assert len(result["options"]) == 5


# ── API route ─────────────────────────────────────────────────────────────────


def test_feasibility_api_route(store, pid):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.storage.factory import get_project_store

    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    resp = client.get(f"/projects/{pid}/feasibility")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["generated"] is True
    assert len(data["options"]) == 5


def test_feasibility_api_with_road_width(store, pid):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.storage.factory import get_project_store

    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    resp = client.get(f"/projects/{pid}/feasibility?road_width_ft=30")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["road_width_ft"] == 30.0


def test_feasibility_api_404_unknown_project(store):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.storage.factory import get_project_store

    app.dependency_overrides[get_project_store] = lambda: store
    client = TestClient(app)
    resp = client.get("/projects/nonexistent/feasibility")
    app.dependency_overrides.clear()
    assert resp.status_code == 404


# ── Chat routing ──────────────────────────────────────────────────────────────


def _chat(store: LocalProjectStore, pid: str, message: str):
    from app.api.routes.chat import _run_deterministic_fallback, ChatRequest
    _patch(store)
    return _run_deterministic_fallback(pid, ChatRequest(message=message, history=[]))


def test_feasibility_keyword_routes(store, pid):
    resp = _chat(store, pid, "run feasibility analysis")
    assert "run_feasibility" in resp.tool_calls


def test_feasibility_compare_routes(store, pid):
    resp = _chat(store, pid, "compare development options")
    assert "compare_feasibility_options" in resp.tool_calls


def test_feasibility_reply_has_content(store, pid):
    resp = _chat(store, pid, "run feasibility analysis")
    assert "feasib" in resp.reply.lower() or "site" in resp.reply.lower()
