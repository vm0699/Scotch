"""Phase 35 — Render prompt generator tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.architecture.floorplan_generator import generate_floorplan
from app.core.architecture.requirement_parser import parse_prompt
from app.core.render.prompt_generator import (
    _classify_view,
    generate_all_render_prompts,
    generate_render_prompt,
)
from app.core.storage import get_project_store
from app.core.storage.local_store import LocalProjectStore
from app.main import app

PROMPT = "3BHK on 30x50 ft east-facing site with master bedroom, 2 bedrooms, living, kitchen, 2 bathrooms"


def _project():
    proj, _ = generate_floorplan(parse_prompt(PROMPT))
    return proj


# ── View classification ───────────────────────────────────────────────────────

def test_classify_exterior():
    assert _classify_view("exterior_front") == "exterior"
    assert _classify_view("facade_view") == "exterior"
    assert _classify_view("street_view") == "exterior"


def test_classify_top():
    assert _classify_view("top_down") == "top"
    assert _classify_view("aerial_view") == "top"


def test_classify_living():
    assert _classify_view("living_room") == "living"
    assert _classify_view("lounge_interior") == "living"


def test_classify_bedroom():
    assert _classify_view("master_bedroom") == "bedroom"
    assert _classify_view("bedroom_view") == "bedroom"


def test_classify_kitchen():
    assert _classify_view("kitchen_view") == "kitchen"
    assert _classify_view("kitchen_interior") == "kitchen"


def test_classify_toilet():
    assert _classify_view("bathroom_view") == "toilet"
    assert _classify_view("wc_interior") == "toilet"


def test_classify_none_defaults_exterior():
    assert _classify_view(None) == "exterior"


# ── generate_render_prompt ────────────────────────────────────────────────────

def test_prompt_is_non_empty_string():
    proj = _project()
    prompt = generate_render_prompt(proj)
    assert isinstance(prompt, str)
    assert len(prompt) > 50


def test_prompt_contains_photorealistic():
    proj = _project()
    prompt = generate_render_prompt(proj)
    assert "photorealistic" in prompt.lower() or "architectural" in prompt.lower()


def test_prompt_contains_camera_view_prefix():
    proj = _project()
    prompt_ext = generate_render_prompt(proj, camera_name="exterior_front")
    assert "exterior" in prompt_ext.lower()
    prompt_liv = generate_render_prompt(proj, camera_name="living_room")
    assert "living room" in prompt_liv.lower()


def test_prompt_mentions_lighting():
    proj = _project()
    prompt = generate_render_prompt(proj, camera_name="exterior_front")
    assert "light" in prompt.lower() or "HDRI" in prompt or "daylight" in prompt.lower()


def test_prompt_mentions_location():
    proj = _project()
    prompt = generate_render_prompt(proj)
    assert "india" in prompt.lower() or "tropical" in prompt.lower()


def test_prompt_mentions_quality_tag():
    proj = _project()
    prompt = generate_render_prompt(proj)
    assert "8K" in prompt or "ultra" in prompt.lower() or "Phase One" in prompt


def test_prompt_with_extra_tags():
    proj = _project()
    prompt = generate_render_prompt(proj, extra_tags=["--ar 16:9", "no people"])
    assert "--ar 16:9" in prompt
    assert "no people" in prompt


def test_prompt_varies_by_view():
    proj = _project()
    ext = generate_render_prompt(proj, camera_name="exterior_front")
    kit = generate_render_prompt(proj, camera_name="kitchen_view")
    assert ext != kit


def test_prompt_includes_style_from_building():
    from app.core.architecture.requirement_parser import parse_prompt as pp
    from app.core.architecture.floorplan_generator import generate_floorplan as gf
    proj, _ = gf(pp("contemporary 3BHK on 30x50 ft site"))
    prompt = generate_render_prompt(proj)
    # contemporary is in building.style → should appear in prompt
    assert "contemporary" in prompt.lower() or "clean" in prompt.lower()


def test_prompt_with_material_plan(tmp_path):
    """When material_plan is generated, floor material adjective appears."""
    from app.core.models.project import MaterialPlan, RoomFinish

    proj = _project()
    room_id = proj.rooms[0].id
    proj = proj.model_copy(update={
        "material_plan": MaterialPlan(
            tile_specs=[],
            room_finishes=[RoomFinish(
                room_id=room_id,
                floor_material="marble",
                wall_material="paint",
                ceiling_material="paint",
            )],
            editable_rates=[],
            assumptions=[],
            generated=True,
            stale=False,
        )
    })
    prompt = generate_render_prompt(proj, camera_name="living_room")
    assert "marble" in prompt.lower() or "reflective" in prompt.lower()


# ── generate_all_render_prompts ───────────────────────────────────────────────

def test_all_prompts_returns_six_views():
    proj = _project()
    all_p = generate_all_render_prompts(proj)
    assert len(all_p) == 6


def test_all_prompts_have_required_fields():
    proj = _project()
    all_p = generate_all_render_prompts(proj)
    for item in all_p:
        assert "name" in item
        assert "label" in item
        assert "view" in item
        assert "prompt" in item
        assert len(item["prompt"]) > 20


def test_all_prompts_cover_all_views():
    proj = _project()
    all_p = generate_all_render_prompts(proj)
    views = {item["view"] for item in all_p}
    assert "exterior" in views
    assert "living" in views or "bedroom" in views  # at least one interior view


# ── REST API endpoint ─────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path: Path):
    store = LocalProjectStore(tmp_path)
    app.dependency_overrides[get_project_store] = lambda: store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _project_with_design(client: TestClient) -> str:
    proj = client.post("/projects", json={"name": "Render Test"}).json()
    pid = proj["id"]
    sample = client.get("/projects/sample").json()
    client.patch(f"/projects/{pid}", json={"project": sample, "change_type": "generate"})
    return pid


def test_render_prompts_endpoint_returns_200(client):
    pid = _project_with_design(client)
    r = client.get(f"/projects/{pid}/render/prompts")
    assert r.status_code == 200


def test_render_prompts_returns_list(client):
    pid = _project_with_design(client)
    r = client.get(f"/projects/{pid}/render/prompts")
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_render_prompts_items_have_prompt_field(client):
    pid = _project_with_design(client)
    r = client.get(f"/projects/{pid}/render/prompts")
    for item in r.json():
        assert "prompt" in item
        assert len(item["prompt"]) > 10


def test_render_prompts_missing_project_returns_404(client):
    r = client.get("/projects/no-such/render/prompts")
    assert r.status_code == 404


def test_render_prompts_no_design_returns_409(client):
    proj = client.post("/projects", json={"name": "Empty"}).json()
    r = client.get(f"/projects/{proj['id']}/render/prompts")
    assert r.status_code == 409
