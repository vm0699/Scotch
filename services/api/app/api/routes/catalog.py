"""Phase 43 — Interior furniture catalog API.

GET /catalog             -> browse/filter the vendored CC0 furniture catalog
GET /catalog/{id}        -> single item detail

Static mesh/thumbnail bytes are served by the /catalog-assets StaticFiles
mount registered in main.py — this router only returns metadata + URLs.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.catalog import CatalogNotFoundError, get_catalog_item, list_catalog_items
from app.core.models.catalog import CatalogItem

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("", response_model=list[CatalogItem], summary="List/browse the furniture catalog")
def get_catalog(category: str | None = None, style: str | None = None) -> list[CatalogItem]:
    return list_catalog_items(category=category, style=style)


@router.get("/{catalog_id}", response_model=CatalogItem, summary="Get one catalog item")
def get_catalog_item_route(catalog_id: str) -> CatalogItem:
    try:
        return get_catalog_item(catalog_id)
    except CatalogNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
