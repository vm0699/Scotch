"""Phase 43 — Catalog manifest loading.

Reads the static, versioned catalog.json (built by tools/catalog-pipeline/,
vendored under app/assets/catalog/) into typed CatalogItem records. This is
project-independent reference data, not per-project storage — no ProjectStore
involved.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.core.models.catalog import CatalogItem, CatalogManifest


class CatalogNotFoundError(Exception):
    pass


@lru_cache
def _load_manifest_cached(catalog_json_path: str) -> CatalogManifest:
    path = Path(catalog_json_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Catalog manifest not found at {path}. "
            "Run `npm run build` in tools/catalog-pipeline/ to generate it."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return CatalogManifest.model_validate(data)


def load_catalog() -> CatalogManifest:
    settings = get_settings()
    catalog_json = settings.catalog_dir / "catalog.json"
    return _load_manifest_cached(str(catalog_json))


def list_catalog_items(
    category: str | None = None,
    style: str | None = None,
) -> list[CatalogItem]:
    items = load_catalog().items
    if category:
        items = [i for i in items if i.category == category]
    if style:
        items = [i for i in items if style in i.style_tags]
    return items


def get_catalog_item(catalog_id: str) -> CatalogItem:
    for item in load_catalog().items:
        if item.id == catalog_id:
            return item
    raise CatalogNotFoundError(f"Catalog item '{catalog_id}' not found")
