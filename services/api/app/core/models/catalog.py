"""Phase 43 — Interior furniture catalog models.

The catalog is static, versioned data (not per-project) describing real,
vendored CC0 glTF furniture assets: services/api/app/assets/catalog/. Each
CatalogItem pairs a real mesh with the metadata FurnitureItem placement needs
(footprint, snap behavior, 2D symbol, material slots, license provenance) —
see docs/product/interior-design-studio-plan.md §5.1.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

SnapType = str  # "floor" | "wall" | "ceiling" | "tabletop"


class MaterialSlot(BaseModel):
    """One recolorable/retexturable region of a catalog mesh.

    v1 ships every slot with editable=False — Poly Haven assets bake diffuse/
    normal/roughness into a single material, so per-slot recolor needs shader
    work that lands in a later stage (Stage 43.4+). The slot is still modeled
    now so FurnitureItem.material_overrides has a stable target to point at.
    """

    slot: str
    editable: bool = False


class CatalogLicense(BaseModel):
    source: str
    spdx: str
    source_url: str
    attribution: str | None = None


class CatalogItem(BaseModel):
    id: str
    slug: str = Field(description="Upstream source identifier (e.g. Poly Haven asset slug)")
    label: str
    category: str = Field(description='e.g. "bed" | "nightstand" | "wardrobe" | "chair"')
    style_tags: list[str] = Field(default_factory=list)
    footprint_w: float = Field(gt=0, description="Canonical width in feet at rotation 0")
    footprint_d: float = Field(gt=0, description="Canonical depth in feet at rotation 0")
    height: float = Field(gt=0, description="3D height in feet")
    mesh_url: str = Field(description="Vendored GLB path, served statically")
    thumbnail_url: str = Field(description="Vendored thumbnail path, served statically")
    symbol_id: str = Field(description="2D plan symbol key (FurnitureSymbol)")
    snap: SnapType = "floor"
    material_slots: list[MaterialSlot] = Field(default_factory=list)
    license: CatalogLicense


class CatalogManifest(BaseModel):
    version: int
    room_type: str
    generated_at: str
    items: list[CatalogItem]
