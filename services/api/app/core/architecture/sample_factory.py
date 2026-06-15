"""Sample ArchitectureProject factory.

Produces the canonical valid 2BHK used by the frontend until prompt-driven
generation lands (Phase 5). Mirrors the layout the workspace shipped with in
Phase 2: a 30 x 50 ft east-facing site, public zone at the entrance, private
zone at the rear, last 15 ft of the plot unbuilt.
"""

from app.core.architecture.materials import assign_default_materials
from app.core.models import (
    ArchitectureProject,
    Building,
    Door,
    Level,
    Parameter,
    ProjectWarning,
    Room,
    Site,
    Window,
)


def create_sample_project() -> ArchitectureProject:
    project = ArchitectureProject(
        id="sample-2bhk-east",
        name="2BHK Apartment Concept",
        units="feet",
        site=Site(width=30, depth=50, orientation="east"),
        building=Building(type="residential", style="modern minimal", floors=1, floor_height=10),
        levels=[Level(index=0, name="Ground Floor", elevation=0)],
        rooms=[
            Room(id="parking", name="Parking", type="parking", x=0, y=0, width=10, depth=15),
            Room(id="living", name="Living Room", type="living", x=10, y=0, width=14, depth=12),
            Room(id="balcony", name="Balcony", type="balcony", x=24, y=0, width=6, depth=10),
            Room(id="kitchen", name="Kitchen", type="kitchen", x=10, y=12, width=8, depth=10),
            Room(id="bath-1", name="Common Bath", type="bathroom", x=18, y=12, width=5, depth=8),
            Room(id="bed-master", name="Master Bedroom", type="bedroom", x=0, y=22, width=12, depth=13),
            Room(id="bath-2", name="Attached Bath", type="bathroom", x=12, y=22, width=5, depth=8),
            Room(id="bed-2", name="Bedroom 2", type="bedroom", x=17, y=22, width=11, depth=12),
        ],
        doors=[
            Door(id="door-main", room_id="living", wall="north", offset=5, width=3.5),
            Door(id="door-kitchen", room_id="kitchen", wall="north", offset=2.5, width=3),
            Door(id="door-bath-1", room_id="bath-1", wall="north", offset=1, width=2.5),
            Door(id="door-bed-master", room_id="bed-master", wall="north", offset=8.5, width=3),
            Door(id="door-bath-2", room_id="bath-2", wall="north", offset=1.25, width=2.5),
            Door(id="door-bed-2", room_id="bed-2", wall="north", offset=4, width=3),
            Door(id="door-balcony", room_id="balcony", wall="west", offset=3.5, width=3),
        ],
        windows=[
            Window(id="win-living", room_id="living", wall="north", offset=9.5, width=4),
            Window(id="win-kitchen", room_id="kitchen", wall="west", offset=3.5, width=3),
            Window(id="win-bed-master-1", room_id="bed-master", wall="south", offset=4, width=4),
            Window(id="win-bed-master-2", room_id="bed-master", wall="west", offset=4.5, width=4),
            Window(id="win-bed-2", room_id="bed-2", wall="south", offset=3.5, width=4),
            Window(id="win-bath-1", room_id="bath-1", wall="east", offset=3, width=1.5),
        ],
        parameters=[
            Parameter(key="site_width", label="Site width", value=30, unit="ft", category="site"),
            Parameter(key="site_depth", label="Site depth", value=50, unit="ft", category="site"),
            Parameter(key="orientation", label="Orientation", value="east", category="site"),
            Parameter(key="floors", label="Floors", value=1, category="building"),
            Parameter(key="floor_height", label="Floor height", value=10, unit="ft", category="building"),
            Parameter(key="style", label="Style", value="modern minimal", category="building"),
        ],
        notes=[
            "Entrance assumed on the east edge per site orientation.",
            "Rear 15 ft of the plot kept unbuilt for garden or expansion.",
        ],
        warnings=[
            ProjectWarning(
                id="warn-bath-distance",
                severity="warning",
                message="Common bath is 10 ft from Bedroom 2 across the corridor — acceptable, not ideal.",
            ),
        ],
    )
    return assign_default_materials(project)
