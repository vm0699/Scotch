"""Phase 13 — Architecture Intelligence tests.

Covers: spatial checks, area calculator, vastu engine,
        schedule exporters (JSON + CSV), and the intelligence API endpoint.
"""

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.sample_factory import create_sample_project
from app.core.intelligence import (
    compute_areas,
    run_spatial_checks,
    run_vastu_checks,
)
from app.core.exports import export_schedule_csv, export_schedule_json
from app.core.storage.factory import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app


@pytest.fixture
def sample():
    return create_sample_project()


@pytest.fixture
def client(tmp_path):
    app.dependency_overrides[get_project_store] = lambda: LocalProjectStore(tmp_path)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def project_with_design(client: TestClient):
    sample = client.get("/projects/sample").json()
    proj = client.post("/projects", json={"name": "Intel House"}).json()
    client.patch(f"/projects/{proj['id']}", json={"project": sample})
    return proj["id"]


# ── 13.2 Area calculator ──────────────────────────────────────────────────────


def test_area_site_area(sample):
    areas = compute_areas(sample)
    expected = round(sample.site.width * sample.site.depth, 2)
    assert areas.site_area == expected


def test_area_built_up_matches_room_sum(sample):
    areas = compute_areas(sample)
    expected = round(sum(r.width * r.depth for r in sample.rooms), 2)
    assert abs(areas.built_up_area - expected) < 0.01


def test_area_carpet_is_85_percent(sample):
    areas = compute_areas(sample)
    assert abs(areas.carpet_area - round(areas.built_up_area * 0.85, 2)) < 0.1


def test_area_coverage_ratio_range(sample):
    areas = compute_areas(sample)
    assert 0 < areas.coverage_ratio <= 100


def test_area_floor_efficiency_is_85(sample):
    areas = compute_areas(sample)
    assert abs(areas.floor_efficiency - 85.0) < 0.5


def test_area_circulation_nonnegative(sample):
    areas = compute_areas(sample)
    assert areas.circulation_area >= 0


def test_area_room_entries_count(sample):
    areas = compute_areas(sample)
    assert len(areas.rooms) == len(sample.rooms)


def test_area_room_entry_fields(sample):
    areas = compute_areas(sample)
    for entry in areas.rooms:
        assert entry.gross_area > 0
        assert entry.carpet_area < entry.gross_area
        assert entry.room_name
        assert entry.room_id


# ── 13.1 Spatial checks ───────────────────────────────────────────────────────


def test_spatial_checks_returns_list(sample):
    checks = run_spatial_checks(sample)
    assert isinstance(checks, list)


def test_spatial_checks_have_valid_severity(sample):
    for check in run_spatial_checks(sample):
        assert check.severity in ("info", "warning", "error")


def test_spatial_check_parking_missing(sample):
    bedrooms = [r for r in sample.rooms if "bedroom" in r.type.lower()]
    if len(bedrooms) >= 2:
        parking = [r for r in sample.rooms if "parking" in r.type.lower()]
        if not parking:
            rules = {c.rule_id for c in run_spatial_checks(sample)}
            assert "parking_missing" in rules


def test_spatial_check_no_false_coverage_error(sample):
    checks = run_spatial_checks(sample)
    # sample project has reasonable coverage — should not flag overcoverage
    error_rules = {c.rule_id for c in checks if c.severity == "error"}
    assert "overcoverage" not in error_rules


def test_spatial_check_room_with_no_door_flagged():
    from app.core.architecture.sample_factory import create_sample_project
    proj = create_sample_project()
    # Remove all doors from first room
    first_room = proj.rooms[0]
    proj.doors = [d for d in proj.doors if d.room_id != first_room.id]
    checks = run_spatial_checks(proj)
    rules = {c.rule_id for c in checks}
    assert "no_door_access" in rules
    flagged_rooms = {c.room_id for c in checks if c.rule_id == "no_door_access"}
    assert first_room.id in flagged_rooms


def test_spatial_check_rule_ids_are_strings(sample):
    for check in run_spatial_checks(sample):
        assert isinstance(check.rule_id, str)
        assert len(check.rule_id) > 0


# ── 13.3 Vastu checks ────────────────────────────────────────────────────────


def test_vastu_returns_list(sample):
    suggestions = run_vastu_checks(sample)
    assert isinstance(suggestions, list)


def test_vastu_severity_valid(sample):
    for s in run_vastu_checks(sample):
        assert s.severity in ("info", "warning", "error")


def test_vastu_includes_entrance_check(sample):
    suggestions = run_vastu_checks(sample)
    entrance_rules = {s.rule_id for s in suggestions}
    assert any("entrance" in r for r in entrance_rules)


def test_vastu_messages_nonempty(sample):
    for s in run_vastu_checks(sample):
        assert len(s.message) > 10


def test_vastu_direction_values(sample):
    valid_dirs = {
        "north", "south", "east", "west",
        "northeast", "northwest", "southeast", "southwest", "center",
    }
    for s in run_vastu_checks(sample):
        if s.direction is not None:
            assert s.direction in valid_dirs


# ── 13.4 Schedule exporters ───────────────────────────────────────────────────


def test_schedule_json_writes_file(tmp_path, sample):
    out = tmp_path / "room_schedule.json"
    export_schedule_json(sample, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_schedule_json_valid_structure(tmp_path, sample):
    out = tmp_path / "room_schedule.json"
    data = export_schedule_json(sample, out)
    payload = json.loads(data)
    assert payload["total_rooms"] == len(sample.rooms)
    assert "rooms" in payload
    assert len(payload["rooms"]) == len(sample.rooms)


def test_schedule_json_room_has_areas(tmp_path, sample):
    out = tmp_path / "room_schedule.json"
    data = export_schedule_json(sample, out)
    payload = json.loads(data)
    for room in payload["rooms"]:
        assert "gross_area" in room and room["gross_area"] > 0
        assert "carpet_area" in room and room["carpet_area"] > 0
        assert room["carpet_area"] < room["gross_area"]


def test_schedule_csv_writes_file(tmp_path, sample):
    out = tmp_path / "room_schedule.csv"
    export_schedule_csv(sample, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_schedule_csv_valid_rows(tmp_path, sample):
    out = tmp_path / "room_schedule.csv"
    data = export_schedule_csv(sample, out)
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    rows = list(reader)
    assert len(rows) == len(sample.rooms)


def test_schedule_csv_has_area_columns(tmp_path, sample):
    out = tmp_path / "room_schedule.csv"
    data = export_schedule_csv(sample, out)
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    headers = reader.fieldnames or []
    assert any("Gross" in h for h in headers)
    assert any("Carpet" in h for h in headers)


def test_api_export_schedule_json(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/schedule_json")
    assert r.status_code == 201
    body = r.json()
    assert body["format"] == "schedule_json"
    assert body["filename"] == "room_schedule.json"


def test_api_export_schedule_csv(client, project_with_design):
    r = client.post(f"/projects/{project_with_design}/exports/schedule_csv")
    assert r.status_code == 201
    body = r.json()
    assert body["format"] == "schedule_csv"
    assert body["filename"] == "room_schedule.csv"


def test_api_download_schedule_json(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/schedule_json")
    r = client.get(f"/projects/{project_with_design}/exports/room_schedule.json")
    assert r.status_code == 200
    payload = r.json()
    assert "rooms" in payload


def test_api_download_schedule_csv(client, project_with_design):
    client.post(f"/projects/{project_with_design}/exports/schedule_csv")
    r = client.get(f"/projects/{project_with_design}/exports/room_schedule.csv")
    assert r.status_code == 200
    assert b"Room Name" in r.content or b"No" in r.content


# ── Intelligence API endpoint ─────────────────────────────────────────────────


def test_api_intelligence_returns_200(client, project_with_design):
    r = client.get(f"/projects/{project_with_design}/intelligence")
    assert r.status_code == 200


def test_api_intelligence_structure(client, project_with_design):
    r = client.get(f"/projects/{project_with_design}/intelligence")
    body = r.json()
    assert "spatial_checks" in body
    assert "area_summary" in body
    assert "vastu_suggestions" in body
    assert body["vastu_suggestions"] is None  # vastu=false by default


def test_api_intelligence_area_summary_fields(client, project_with_design):
    r = client.get(f"/projects/{project_with_design}/intelligence")
    summary = r.json()["area_summary"]
    for key in ("site_area", "built_up_area", "carpet_area", "coverage_ratio", "floor_efficiency"):
        assert key in summary
        assert summary[key] >= 0


def test_api_intelligence_with_vastu(client, project_with_design):
    r = client.get(f"/projects/{project_with_design}/intelligence?vastu=true")
    assert r.status_code == 200
    body = r.json()
    assert body["vastu_suggestions"] is not None
    assert isinstance(body["vastu_suggestions"], list)


def test_api_intelligence_vastu_has_messages(client, project_with_design):
    r = client.get(f"/projects/{project_with_design}/intelligence?vastu=true")
    for suggestion in r.json()["vastu_suggestions"]:
        assert len(suggestion["message"]) > 5
        assert suggestion["severity"] in ("info", "warning", "error")


def test_api_intelligence_404_unknown_project(client):
    r = client.get("/projects/does-not-exist/intelligence")
    assert r.status_code == 404


def test_api_intelligence_409_no_design(client):
    proj = client.post("/projects", json={"name": "Empty"}).json()
    r = client.get(f"/projects/{proj['id']}/intelligence")
    assert r.status_code == 409
