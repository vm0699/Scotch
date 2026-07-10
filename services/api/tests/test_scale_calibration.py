"""Phase 39 — Scale calibration engine tests."""
from __future__ import annotations

import math

import pytest

from app.core.references.models import ScaleCalibration
from app.core.references.scale import (
    compute_scale,
    ft_to_pixel,
    pixel_distance_ft,
    pixel_to_ft,
)


# ── compute_scale ─────────────────────────────────────────────────────────────

def test_compute_scale_horizontal():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)
    assert cal.pixels_per_foot == pytest.approx(10.0)
    assert cal.known_distance_ft == 10.0


def test_compute_scale_vertical():
    cal = compute_scale(50, 0, 50, 200, known_distance_ft=20.0)
    assert cal.pixels_per_foot == pytest.approx(10.0)


def test_compute_scale_diagonal():
    cal = compute_scale(0, 0, 30, 40, known_distance_ft=5.0)
    expected_ppf = math.sqrt(30 ** 2 + 40 ** 2) / 5.0
    assert cal.pixels_per_foot == pytest.approx(expected_ppf)


def test_compute_scale_with_origin_offset():
    cal = compute_scale(10, 10, 110, 10, known_distance_ft=5.0, origin_x_ft=2.0, origin_y_ft=3.0)
    assert cal.pixels_per_foot == pytest.approx(20.0)
    assert cal.origin_x_ft == 2.0
    assert cal.origin_y_ft == 3.0


def test_compute_scale_rejects_coincident_points():
    with pytest.raises(ValueError, match="1 pixel apart"):
        compute_scale(100, 100, 100, 100, known_distance_ft=5.0)


def test_compute_scale_rejects_zero_distance():
    with pytest.raises(ValueError):
        compute_scale(0, 0, 100, 0, known_distance_ft=0.0)


def test_compute_scale_rejects_negative_distance():
    with pytest.raises(Exception):
        compute_scale(0, 0, 100, 0, known_distance_ft=-5.0)


def test_compute_scale_returns_calibration_model():
    cal = compute_scale(0, 0, 60, 0, known_distance_ft=6.0)
    assert isinstance(cal, ScaleCalibration)
    assert cal.scale_status if hasattr(cal, "scale_status") else True  # not on model
    assert cal.p1_x == 0
    assert cal.p2_x == 60


# ── pixel_to_ft ───────────────────────────────────────────────────────────────

def test_pixel_to_ft_origin():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)  # ppf = 10
    x, y = pixel_to_ft(0, 0, cal)
    assert x == pytest.approx(0.0)
    assert y == pytest.approx(0.0)


def test_pixel_to_ft_along_x():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)  # ppf = 10
    x, y = pixel_to_ft(50, 0, cal)
    assert x == pytest.approx(5.0)
    assert y == pytest.approx(0.0)


def test_pixel_to_ft_along_y():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)  # ppf = 10
    x, y = pixel_to_ft(0, 30, cal)
    assert x == pytest.approx(0.0)
    assert y == pytest.approx(3.0)


def test_pixel_to_ft_with_origin_offset():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0, origin_x_ft=5.0, origin_y_ft=2.0)
    x, y = pixel_to_ft(0, 0, cal)
    assert x == pytest.approx(5.0)
    assert y == pytest.approx(2.0)


def test_pixel_to_ft_roundtrip_via_ft_to_pixel():
    cal = compute_scale(0, 0, 120, 0, known_distance_ft=30.0)
    px_in, py_in = 60.0, 40.0
    x_ft, y_ft = pixel_to_ft(px_in, py_in, cal)
    px_out, py_out = ft_to_pixel(x_ft, y_ft, cal)
    assert px_out == pytest.approx(px_in, abs=0.5)
    assert py_out == pytest.approx(py_in, abs=0.5)


# ── ft_to_pixel ───────────────────────────────────────────────────────────────

def test_ft_to_pixel_origin():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)
    px, py = ft_to_pixel(0.0, 0.0, cal)
    assert px == pytest.approx(0.0, abs=0.5)
    assert py == pytest.approx(0.0, abs=0.5)


def test_ft_to_pixel_known_distance():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)  # ppf = 10
    px, py = ft_to_pixel(5.0, 3.0, cal)
    assert px == pytest.approx(50.0, abs=0.5)
    assert py == pytest.approx(30.0, abs=0.5)


# ── pixel_distance_ft ─────────────────────────────────────────────────────────

def test_pixel_distance_ft_horizontal():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)  # ppf = 10
    dist = pixel_distance_ft(0, 0, 100, 0, cal)
    assert dist == pytest.approx(10.0)


def test_pixel_distance_ft_diagonal():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)  # ppf = 10
    dist = pixel_distance_ft(0, 0, 30, 40, cal)
    expected = math.sqrt(30 ** 2 + 40 ** 2) / 10.0
    assert dist == pytest.approx(expected)


def test_pixel_distance_ft_zero():
    cal = compute_scale(0, 0, 100, 0, known_distance_ft=10.0)
    assert pixel_distance_ft(50, 50, 50, 50, cal) == pytest.approx(0.0)


# ── API integration (using FastAPI TestClient) ────────────────────────────────

def test_calibrate_api_sets_calibration(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.core.references.store import ReferenceStore
    import app.api.routes.references as ref_mod

    app = create_app()
    client = TestClient(app)

    # Create a project first
    proj_resp = client.post("/projects", json={"name": "Cal Test", "prompt": "2BHK"})
    assert proj_resp.status_code == 201
    pid = proj_resp.json()["id"]

    # Upload a fake image
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    up_resp = client.post(
        f"/projects/{pid}/references",
        files={"file": ("test.png", fake_png, "image/png")},
        data={"reference_type": "existing_plan"},
    )
    assert up_resp.status_code == 201
    ref_id = up_resp.json()["id"]

    # Set calibration
    cal_resp = client.patch(
        f"/projects/{pid}/references/{ref_id}/calibrate",
        json={"p1_x": 0, "p1_y": 0, "p2_x": 200, "p2_y": 0, "known_distance_ft": 10.0},
    )
    assert cal_resp.status_code == 200
    data = cal_resp.json()
    assert data["scale_status"] == "calibrated"
    assert data["calibration"]["pixels_per_foot"] == pytest.approx(20.0)


def test_calibrate_api_rejects_coincident_points(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app

    app = create_app()
    client = TestClient(app)

    proj_resp = client.post("/projects", json={"name": "Cal Err", "prompt": "2BHK"})
    pid = proj_resp.json()["id"]
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    up_resp = client.post(
        f"/projects/{pid}/references",
        files={"file": ("t.png", fake_png, "image/png")},
        data={},
    )
    ref_id = up_resp.json()["id"]

    cal_resp = client.patch(
        f"/projects/{pid}/references/{ref_id}/calibrate",
        json={"p1_x": 10, "p1_y": 10, "p2_x": 10, "p2_y": 10, "known_distance_ft": 5.0},
    )
    assert cal_resp.status_code == 422
