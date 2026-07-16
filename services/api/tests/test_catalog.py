"""Phase 43 Stage 43.1 — Interior furniture catalog tests.

Covers:
  - loader: manifest loads, filtering by category/style, unknown id raises
  - CatalogItem model: footprint/height/license fields validate
  - API: GET /catalog, GET /catalog/{id}, 404 for unknown id
  - static assets: every catalog item's mesh_url resolves to bytes that
    parse as a valid glTF-binary (GLB) file (magic header + non-trivial size)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.catalog import CatalogNotFoundError, get_catalog_item, list_catalog_items, load_catalog
from app.main import app

client = TestClient(app)


# ── Loader ──────────────────────────────────────────────────────────────────


def test_load_catalog_has_bedroom_items() -> None:
    manifest = load_catalog()
    assert "bedroom" in manifest.room_type
    assert len(manifest.items) >= 15


def test_list_catalog_items_filters_by_category() -> None:
    beds = list_catalog_items(category="bed")
    assert len(beds) >= 1
    assert all(item.category == "bed" for item in beds)


def test_list_catalog_items_filters_by_style() -> None:
    modern = list_catalog_items(style="modern")
    assert len(modern) >= 1
    assert all("modern" in item.style_tags for item in modern)


def test_get_catalog_item_returns_known_item() -> None:
    item = get_catalog_item("bed_single_frame")
    assert item.category == "bed"
    assert item.footprint_w > 0
    assert item.footprint_d > 0
    assert item.height > 0
    assert item.license.spdx == "CC0-1.0"


def test_get_catalog_item_unknown_raises() -> None:
    with pytest.raises(CatalogNotFoundError):
        get_catalog_item("does_not_exist")


def test_every_item_has_valid_snap_and_symbol() -> None:
    for item in load_catalog().items:
        assert item.snap in {"floor", "wall", "ceiling", "tabletop"}
        assert item.symbol_id
        assert item.material_slots


# ── API ─────────────────────────────────────────────────────────────────────


def test_get_catalog_api_lists_items() -> None:
    response = client.get("/catalog")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 15
    assert {"id", "label", "category", "mesh_url", "thumbnail_url"} <= body[0].keys()


def test_get_catalog_api_filters_by_category() -> None:
    response = client.get("/catalog", params={"category": "nightstand"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert all(item["category"] == "nightstand" for item in body)


def test_get_catalog_item_api_returns_item() -> None:
    response = client.get("/catalog/wardrobe_painted")
    assert response.status_code == 200
    assert response.json()["category"] == "wardrobe"


def test_get_catalog_item_api_404_for_unknown() -> None:
    response = client.get("/catalog/nope")
    assert response.status_code == 404


# ── Static asset serving ────────────────────────────────────────────────────

GLB_MAGIC = b"glTF"


def test_all_catalog_meshes_serve_valid_glb_bytes() -> None:
    # Threshold is 2 KB, not 10 KB — Stage 43.18/43.19 added Meshopt geometry
    # + WebP texture compression, and simple low-poly Kenney fixtures (WC,
    # basin, tub) legitimately compress down to ~7-10 KB now. This still
    # catches genuine corruption (an empty or near-empty response).
    manifest = load_catalog()
    for item in manifest.items:
        response = client.get(item.mesh_url)
        assert response.status_code == 200, f"{item.id}: {item.mesh_url} did not serve"
        assert response.content[:4] == GLB_MAGIC, f"{item.id}: not a valid GLB (bad magic header)"
        assert len(response.content) > 2_000, f"{item.id}: suspiciously small GLB ({len(response.content)} bytes)"


def test_all_catalog_thumbnails_serve() -> None:
    manifest = load_catalog()
    for item in manifest.items:
        response = client.get(item.thumbnail_url)
        assert response.status_code == 200, f"{item.id}: {item.thumbnail_url} did not serve"
        assert len(response.content) > 100


def test_catalog_licenses_file_exists_and_lists_every_item() -> None:
    licenses_path = get_settings().catalog_dir / "CATALOG_LICENSES.md"
    assert licenses_path.exists()
    text = licenses_path.read_text(encoding="utf-8")
    for item in load_catalog().items:
        assert item.id in text, f"{item.id} missing from CATALOG_LICENSES.md"
