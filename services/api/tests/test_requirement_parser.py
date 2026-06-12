from app.core.architecture.requirement_parser import parse_prompt


def test_full_2bhk_prompt() -> None:
    req = parse_prompt(
        "Design a 2BHK apartment on a 30x50 ft east-facing site with living room, "
        "kitchen, 2 bedrooms, 2 bathrooms, balcony, and parking."
    )
    assert (req.site_width, req.site_depth) == (30, 50)
    assert req.orientation == "east"
    assert req.building_kind == "apartment"
    assert req.bedrooms == 2
    assert req.bathrooms == 2
    assert req.parking and req.balcony
    assert req.floors == 1


def test_villa_with_dining_north_facing() -> None:
    req = parse_prompt("3BHK villa on a 40x60 north-facing site with dining and 3 bathrooms")
    assert req.building_kind == "villa"
    assert req.bedrooms == 3
    assert req.bathrooms == 3
    assert req.dining
    assert req.orientation == "north"


def test_studio_has_no_bedrooms() -> None:
    req = parse_prompt("studio apartment 20x30")
    assert req.building_kind == "studio"
    assert req.bedrooms == 0
    assert req.bathrooms == 1


def test_cafe_detection() -> None:
    req = parse_prompt("small cafe 25x40 with seating and counter")
    assert req.building_kind == "cafe"


def test_office_detection() -> None:
    req = parse_prompt("office layout 50x80 with workstations")
    assert req.building_kind == "office"


def test_duplex_defaults_two_floors() -> None:
    req = parse_prompt("duplex house 30x50")
    assert req.building_kind == "duplex"
    assert req.floors == 2


def test_defaults_recorded_as_assumptions() -> None:
    req = parse_prompt("design me a house")
    assert (req.site_width, req.site_depth) == (30, 50)
    assert req.orientation == "east"
    assert req.bedrooms == 2
    joined = " ".join(req.assumptions)
    assert "Site size not specified" in joined
    assert "Orientation not specified" in joined
    assert "Bedroom count not specified" in joined


def test_explicit_values_create_no_assumptions() -> None:
    req = parse_prompt(
        "modern 2bhk apartment, 30x50 ft, west-facing, 2 bathrooms"
    )
    joined = " ".join(req.assumptions)
    assert "Site size" not in joined
    assert "Orientation" not in joined
    assert "Bedroom" not in joined
    assert "Bathroom" not in joined
