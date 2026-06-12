import type {
  ArchitectureProject,
  Door,
  Room,
  WallSide,
  WindowOpening,
} from "@/features/project/types";
import { roomArea } from "@/features/project/types";

/**
 * Architectural 2D floor plan renderer. Pure SVG from an ArchitectureProject:
 * site boundary, poché walls, door swings, window symbols, room labels with
 * sizes/areas, site dimension lines, and a north arrow.
 *
 * Plan space: x across site width, y along site depth, y = 0 at the entrance
 * edge (drawn at the top). All coordinates are in project units (feet),
 * scaled by SCALE into px.
 */

export const SCALE = 12; // px per ft
const WALL_T = 0.5; // wall thickness in ft
const MARGIN = 64; // px around the site for dimensions + north arrow

export function planPixelSize(project: ArchitectureProject): {
  width: number;
  height: number;
} {
  return {
    width: project.site.width * SCALE + MARGIN * 2,
    height: project.site.depth * SCALE + MARGIN * 2,
  };
}

/** Start corner, along-wall axis and into-room normal for a room wall. */
function wallFrame(room: Room, wall: WallSide) {
  switch (wall) {
    case "north":
      return { sx: room.x, sy: room.y, ax: 1, ay: 0, nx: 0, ny: 1 };
    case "south":
      return { sx: room.x, sy: room.y + room.depth, ax: 1, ay: 0, nx: 0, ny: -1 };
    case "west":
      return { sx: room.x, sy: room.y, ax: 0, ay: 1, nx: 1, ny: 0 };
    case "east":
      return { sx: room.x + room.width, sy: room.y, ax: 0, ay: 1, nx: -1, ny: 0 };
  }
}

function DoorSymbol({ door, room }: { door: Door; room: Room }) {
  const f = wallFrame(room, door.wall);
  const w = door.width;
  // Hinge at the offset start of the opening.
  const hx = (f.sx + f.ax * door.offset) * SCALE;
  const hy = (f.sy + f.ay * door.offset) * SCALE;
  const jx = hx + f.ax * w * SCALE; // far jamb
  const jy = hy + f.ay * w * SCALE;
  const lx = hx + f.nx * w * SCALE; // leaf end (door open into the room)
  const ly = hy + f.ny * w * SCALE;
  const gap = WALL_T * SCALE + 1;
  // Sweep direction so the arc bows from leaf end to far jamb.
  const sweep = f.nx * f.ay - f.ny * f.ax > 0 ? 0 : 1;

  return (
    <g>
      <line
        x1={hx}
        y1={hy}
        x2={jx}
        y2={jy}
        className="stroke-card"
        strokeWidth={gap}
      />
      <line
        x1={hx}
        y1={hy}
        x2={lx}
        y2={ly}
        className="stroke-foreground"
        strokeWidth={1.2}
      />
      <path
        d={`M ${lx} ${ly} A ${w * SCALE} ${w * SCALE} 0 0 ${sweep} ${jx} ${jy}`}
        fill="none"
        className="stroke-muted-foreground"
        strokeWidth={0.8}
        strokeDasharray="2.5 2.5"
      />
    </g>
  );
}

function WindowSymbol({
  window: win,
  room,
}: {
  window: WindowOpening;
  room: Room;
}) {
  const f = wallFrame(room, win.wall);
  const sx = (f.sx + f.ax * win.offset) * SCALE;
  const sy = (f.sy + f.ay * win.offset) * SCALE;
  const ex = sx + f.ax * win.width * SCALE;
  const ey = sy + f.ay * win.width * SCALE;
  const half = (WALL_T / 2) * SCALE;
  const gap = WALL_T * SCALE + 1;

  return (
    <g>
      <line
        x1={sx}
        y1={sy}
        x2={ex}
        y2={ey}
        className="stroke-card"
        strokeWidth={gap}
      />
      {/* sill, glazing and outer lines */}
      {[-half, 0, half].map((d, i) => (
        <line
          key={i}
          x1={sx + f.nx * d}
          y1={sy + f.ny * d}
          x2={ex + f.nx * d}
          y2={ey + f.ny * d}
          className="stroke-foreground"
          strokeWidth={i === 1 ? 1 : 0.7}
        />
      ))}
    </g>
  );
}

function RoomShape({
  room,
  selected,
  interactive,
}: {
  room: Room;
  selected: boolean;
  interactive: boolean;
}) {
  return (
    <g>
      <rect
        data-room-id={room.id}
        x={room.x * SCALE}
        y={room.y * SCALE}
        width={room.width * SCALE}
        height={room.depth * SCALE}
        className={
          (selected ? "fill-sky-50 " : "fill-card ") +
          "stroke-foreground transition-colors" +
          (interactive ? " cursor-pointer hover:fill-muted/70" : "")
        }
        strokeWidth={WALL_T * SCALE}
      />
      {selected && (
        <rect
          x={room.x * SCALE + 2}
          y={room.y * SCALE + 2}
          width={room.width * SCALE - 4}
          height={room.depth * SCALE - 4}
          className="pointer-events-none fill-none stroke-sky-500"
          strokeWidth={1.5}
        />
      )}
    </g>
  );
}

function RoomLabel({ room, unit }: { room: Room; unit: string }) {
  const cx = (room.x + room.width / 2) * SCALE;
  const cy = (room.y + room.depth / 2) * SCALE;
  const compact = Math.min(room.width, room.depth) < 6;
  const showArea = roomArea(room) >= 60 && !compact;

  return (
    <text
      x={cx}
      y={cy}
      textAnchor="middle"
      className="select-none fill-foreground"
      style={{ fontSize: compact ? 8.5 : 11 }}
    >
      <tspan x={cx} dy={showArea ? "-0.7em" : "-0.1em"} fontWeight={500}>
        {room.name}
      </tspan>
      <tspan
        x={cx}
        dy="1.25em"
        className="fill-muted-foreground"
        style={{ fontSize: compact ? 7.5 : 9 }}
      >
        {room.width}′ × {room.depth}′
      </tspan>
      {showArea && (
        <tspan
          x={cx}
          dy="1.25em"
          className="fill-muted-foreground"
          style={{ fontSize: 9 }}
        >
          {roomArea(room)} {unit}²
        </tspan>
      )}
    </text>
  );
}

/** Dimension line with architectural slash ticks. */
function DimensionLine({
  x1,
  y1,
  x2,
  y2,
  label,
  vertical = false,
}: {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  label: string;
  vertical?: boolean;
}) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const tick = 4;

  return (
    <g className="stroke-muted-foreground" strokeWidth={0.8}>
      <line x1={x1} y1={y1} x2={x2} y2={y2} />
      {[{ x: x1, y: y1 }, { x: x2, y: y2 }].map((p, i) => (
        <line
          key={i}
          x1={p.x - tick}
          y1={p.y + tick}
          x2={p.x + tick}
          y2={p.y - tick}
          strokeWidth={1}
        />
      ))}
      <text
        x={mx}
        y={my}
        dy={vertical ? "-0.5em" : "-0.55em"}
        textAnchor="middle"
        className="fill-muted-foreground"
        stroke="none"
        style={{ fontSize: 9.5 }}
        transform={vertical ? `rotate(-90 ${mx} ${my})` : undefined}
      >
        {label}
      </text>
    </g>
  );
}

function NorthArrow({
  cx,
  cy,
  topDirection,
}: {
  cx: number;
  cy: number;
  topDirection: string;
}) {
  const rotation =
    { north: 0, east: -90, west: 90, south: 180 }[topDirection] ?? 0;
  return (
    <g transform={`translate(${cx} ${cy})`}>
      <circle
        r={15}
        className="fill-card stroke-muted-foreground"
        strokeWidth={0.8}
      />
      <g transform={`rotate(${rotation})`}>
        <path d="M 0 -10 L 4 6 L 0 3.5 L -4 6 Z" className="fill-foreground" />
      </g>
      <text
        y={28}
        textAnchor="middle"
        className="fill-muted-foreground"
        style={{ fontSize: 8.5, letterSpacing: "0.08em" }}
      >
        N
      </text>
    </g>
  );
}

export function FloorPlanSvg({
  project,
  style,
  className,
  selectedRoomId = null,
  interactive = false,
}: {
  project: ArchitectureProject;
  style?: React.CSSProperties;
  className?: string;
  /** Highlighted room (Phase 6 selection). */
  selectedRoomId?: string | null;
  /** Enables pointer affordances on rooms; click handling is delegated to the parent. */
  interactive?: boolean;
}) {
  const { site } = project;
  const { width: vw, height: vh } = planPixelSize(project);
  const sw = site.width * SCALE;
  const sd = site.depth * SCALE;
  const unit = project.units === "feet" ? "ft" : "m";
  const roomsById = new Map(project.rooms.map((r) => [r.id, r]));
  const dimOffset = 26;

  return (
    <svg
      viewBox={`0 0 ${vw} ${vh}`}
      style={style}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label={`Floor plan of ${project.name}`}
    >
      <g transform={`translate(${MARGIN} ${MARGIN})`}>
        {/* site */}
        <rect
          x={0}
          y={0}
          width={sw}
          height={sd}
          className="fill-muted/40 stroke-muted-foreground"
          strokeWidth={1}
          strokeDasharray="6 3"
        />

        {/* rooms: fills + walls, then openings, then labels */}
        <g>
          {project.rooms.map((room) => (
            <RoomShape
              key={room.id}
              room={room}
              selected={room.id === selectedRoomId}
              interactive={interactive}
            />
          ))}
        </g>
        <g>
          {project.doors.map((door) => {
            const room = roomsById.get(door.room_id);
            return room ? (
              <DoorSymbol key={door.id} door={door} room={room} />
            ) : null;
          })}
          {project.windows.map((win) => {
            const room = roomsById.get(win.room_id);
            return room ? (
              <WindowSymbol key={win.id} window={win} room={room} />
            ) : null;
          })}
        </g>
        <g>
          {project.rooms.map((room) => (
            <RoomLabel key={room.id} room={room} unit={unit} />
          ))}
        </g>

        {/* site dimensions */}
        <DimensionLine
          x1={0}
          y1={sd + dimOffset}
          x2={sw}
          y2={sd + dimOffset}
          label={`${site.width}′-0″`}
        />
        <DimensionLine
          x1={-dimOffset}
          y1={sd}
          x2={-dimOffset}
          y2={0}
          label={`${site.depth}′-0″`}
          vertical
        />

        {/* north arrow, top-right of the site */}
        <NorthArrow cx={sw + 34} cy={4} topDirection={site.orientation} />
      </g>
    </svg>
  );
}
