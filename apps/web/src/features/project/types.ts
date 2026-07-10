/**
 * ArchitectureProject — the universal architecture model and single source
 * of truth for previews, parameters, schedules, and exports.
 *
 * Field names are snake_case to match the backend Pydantic JSON one-to-one
 * (formalized in Phase 3); the mock data and all UI components use these
 * types so the backend swap is a data-source change, not a refactor.
 */

export type Units = "feet" | "meters";
export type Orientation = "north" | "south" | "east" | "west";
export type WallSide = "north" | "south" | "east" | "west";
export type WarningSeverity = "info" | "warning" | "error";
export type DimensionType = "linear" | "room" | "external" | "opening" | "stair";
export type DimensionLayer = "dim-external" | "dim-room" | "dim-opening" | "dim-stair";
export type MEPSystem = "plumbing" | "electrical" | "lighting" | "ac";
export type DetailType = "toilet" | "kitchen" | "door_window" | "wall_section" | "tile_layout" | "stair" | "custom";

export interface Site {
  width: number;
  depth: number;
  orientation: Orientation;
}

export interface Building {
  type: string;
  style: string;
  floors: number;
  floor_height: number;
}

export interface Level {
  index: number;
  name: string;
  elevation: number;
}

export interface Room {
  id: string;
  name: string;
  type: string;
  /** Position of the room's top-left corner on the site plan, in project units. */
  x: number;
  y: number;
  width: number;
  depth: number;
  level: number;
}

/** Explicit wall segment; optional while rooms imply their own walls. */
export interface Wall {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  thickness: number;
  room_id?: string | null;
}

export interface Door {
  id: string;
  room_id: string;
  wall: WallSide;
  /** Distance from the wall's start (left/top end) to the opening start. */
  offset: number;
  width: number;
}

export interface WindowOpening {
  id: string;
  room_id: string;
  wall: WallSide;
  offset: number;
  width: number;
}

export interface Material {
  id: string;
  name: string;
  /** What the material applies to, e.g. wall, floor, roof, glass. */
  target: string;
  finish?: string | null;
  /** Hex color hint for render engines, e.g. "#F5F4F2". */
  base_color: string;
  /** Principled BSDF roughness hint (0–1). */
  roughness: number;
  /** Principled BSDF metallic hint (0–1). */
  metallic: number;
}

/** A camera preset derived from site/room geometry for render workflows. */
export interface CameraSuggestion {
  name: string;
  type: "perspective" | "orthographic";
  /** [plan_x, height, plan_y] in project units — maps to three.js [x, y, z] */
  position: [number, number, number];
  /** [plan_x, height, plan_y] in project units */
  target: [number, number, number];
  /** Horizontal FOV in degrees; 0 for orthographic. */
  fov: number;
  description: string;
}

export interface Parameter {
  key: string;
  label: string;
  value: string | number;
  unit?: string | null;
  category: "site" | "building" | "room";
  editable: boolean;
  target_id?: string | null;
  min?: number | null;
  max?: number | null;
}

export interface ProjectWarning {
  id: string;
  severity: WarningSeverity;
  message: string;
}

/**
 * One piece of furniture placed in a room.
 * x/y = top-left corner of the placed footprint (plan space, feet).
 * width/depth = placed footprint dimensions AFTER rotation — always axis-aligned.
 * rotation = display angle (0|90|180|270) for SVG symbol rendering only.
 * height = 3D block height for massing / export.
 */
export interface FurnitureItem {
  id: string;
  type: string;
  label: string;
  room_id: string;
  x: number;
  y: number;
  width: number;
  depth: number;
  rotation: 0 | 90 | 180 | 270;
  height: number;
}

// ── Phase 29: Dimension entities ─────────────────────────────────────────────

/** One working-drawing dimension annotation derived by AutoDimensionEngine. */
export interface DimensionEntity {
  id: string;
  dim_type: DimensionType;
  /** [x, y] start point in plan-space project units */
  p1: [number, number];
  /** [x, y] end point in plan-space project units */
  p2: [number, number];
  /** Numeric span in project units */
  value: number;
  label: string;
  layer: DimensionLayer;
}

/** Detailed stair parameters for working-drawing output. */
export interface StairEntity {
  id: string;
  room_id: string;
  risers: number;
  riser_height: number;
  tread_depth: number;
  width: number;
  flight_direction: WallSide;
  stair_type: "straight" | "l_shaped" | "u_shaped";
  level_from: number;
  level_to: number;
}

// ── Phase 29: MEP models ──────────────────────────────────────────────────────

/** One MEP fixture or control point placed in plan space. */
export interface ServicePoint {
  id: string;
  system: MEPSystem;
  kind: string;
  room_id: string;
  x: number;
  y: number;
  mount_height: number;
  confidence: number;
  needs_review: boolean;
  user_override: boolean;
  label: string;
}

/** Advisory pipe/cable route as a polyline of [x, y] points. */
export interface ServiceRoute {
  id: string;
  system: MEPSystem;
  polyline: [number, number][];
  kind: string;
  confidence: number;
  needs_review: boolean;
}

export interface PlumbingPlan {
  points: ServicePoint[];
  routes: ServiceRoute[];
  warnings: string[];
  confidence: number;
  needs_review: boolean;
}

export interface ElectricalPlan {
  points: ServicePoint[];
  routes: ServiceRoute[];
  warnings: string[];
  confidence: number;
  needs_review: boolean;
}

export interface LightingPlan {
  points: ServicePoint[];
  warnings: string[];
  confidence: number;
  needs_review: boolean;
}

export interface ACPlan {
  points: ServicePoint[];
  warnings: string[];
  confidence: number;
  needs_review: boolean;
}

/**
 * Container for all four MEP systems.
 * generated=false until MEPGenerator runs.
 * stale=true when rooms change after generation.
 * All outputs are advisory — not engineering-certified.
 */
export interface MEPPlan {
  plumbing: PlumbingPlan;
  electrical: ElectricalPlan;
  lighting: LightingPlan;
  ac: ACPlan;
  generated: boolean;
  stale: boolean;
}

// ── Phase 30: Detail Drawing types ───────────────────────────────────────────

export interface LinePrimitive {
  kind: "line";
  p1: [number, number];
  p2: [number, number];
  layer: string;
  style: string;
  weight: number;
}

export interface ArcPrimitive {
  kind: "arc";
  center: [number, number];
  radius: number;
  start_angle: number;
  end_angle: number;
  layer: string;
}

export interface TextPrimitive {
  kind: "text";
  pos: [number, number];
  text: string;
  height: number;
  layer: string;
  anchor: string;
}

export interface DimPrimitive {
  kind: "dim";
  p1: [number, number];
  p2: [number, number];
  value: number;
  label: string;
  layer: string;
}

export interface HatchPrimitive {
  kind: "hatch";
  boundary: [number, number][];
  pattern: string;
  scale: number;
  layer: string;
  angle: number;
}

export type DetailPrimitive = LinePrimitive | ArcPrimitive | TextPrimitive | DimPrimitive | HatchPrimitive;

export interface DetailDrawing {
  id: string;
  name: string;
  detail_type: DetailType;
  source_object_ids: string[];
  primitives: DetailPrimitive[];
  canvas_width: number;
  canvas_height: number;
  scale: string;
  view: string;
  warnings: string[];
  annotations: string[];
  confidence: number;
  needs_review: boolean;
  stale: boolean;
}

// ── Phase 31: Material / BOQ / Cost types ────────────────────────────────────

/** Tile specification for a room or project-wide default. */
export interface TileSpec {
  id: string;
  label: string;
  /** Tile width in inches */
  size_w: number;
  /** Tile height in inches */
  size_h: number;
  /** Supply rate in INR per sqft; 0 = missing/not set */
  rate_per_sqft: number;
  /** Additional wastage percentage, e.g. 10 = 10% */
  wastage_pct: number;
}

export interface RoomFinish {
  room_id: string;
  floor_material: string;
  floor_tile_spec_id?: string | null;
  wall_material: string;
  ceiling_material: string;
  wall_tile_spec_id?: string | null;
}

export interface RateEntry {
  category: string;
  item: string;
  unit: string;
  rate: number;
  source: string;
}

export interface MaterialPlan {
  tile_specs: TileSpec[];
  room_finishes: RoomFinish[];
  editable_rates: RateEntry[];
  assumptions: string[];
  generated: boolean;
  stale: boolean;
}

/** One line in the Bill of Quantities. */
export interface BOQItem {
  id: string;
  category: string;
  description: string;
  source_object_ids: string[];
  unit: string;
  quantity: number;
  rate: number;
  amount: number;
  confidence: number;
  needs_review: boolean;
  editable: boolean;
}

export interface CategoryTotal {
  category: string;
  total: number;
}

export interface CostPlan {
  boq_items: BOQItem[];
  category_totals: CategoryTotal[];
  grand_total: number;
  missing_rates: string[];
  assumptions: string[];
  confidence: number;
  needs_review: boolean;
  generated: boolean;
}

// ── Phase 34: Client Change Management ───────────────────────────────────────

export type ChangeStatus = "pending" | "approved" | "applied" | "rejected" | "reverted";
export type ChangeSource = "chat" | "manual" | "client" | "architect";
export type ChangePriority = "low" | "medium" | "high" | "urgent";
export type AffectedSeverity = "info" | "warning" | "action_needed";

export interface AffectedItem {
  module: string;
  object_id?: string | null;
  description: string;
  severity: AffectedSeverity;
  action: string;
}

export interface AffectedItems {
  change_id: string;
  rooms: AffectedItem[];
  mep: AffectedItem[];
  boq: AffectedItem[];
  compliance: AffectedItem[];
  details: AffectedItem[];
  exports: AffectedItem[];
  plugins: AffectedItem[];
  total_count: number;
  summary: string;
  cost_impact: string;
}

export interface ClientChangeRequest {
  id: string;
  request_text: string;
  source: ChangeSource;
  status: ChangeStatus;
  priority: ChangePriority;
  created_at: string;
  updated_at: string;
  affected_modules: string[];
  before_version?: string | null;
  after_version?: string | null;
  summary: string;
  cost_impact: string;
  drawing_impact: string[];
  mep_impact: string[];
  detail_impact: string[];
  export_impact: string[];
  affected_items?: AffectedItems | null;
}

export interface RevisionMeta {
  revision_number: number;
  note: string;
  date: string;
  affected_sheets: string[];
  exports_stale: boolean;
  stale_reason: string;
}

export interface ArchitectureProject {
  id: string;
  name: string;
  units: Units;
  site: Site;
  building: Building;
  levels: Level[];
  rooms: Room[];
  walls: Wall[];
  doors: Door[];
  windows: WindowOpening[];
  furniture: FurnitureItem[];
  materials: Material[];
  parameters: Parameter[];
  notes: string[];
  warnings: ProjectWarning[];
  show_furniture: boolean;
  // Phase 29 additions
  dimensions: DimensionEntity[];
  stairs: StairEntity[];
  mep_plan: MEPPlan;
  show_dimensions: boolean;
  show_mep: boolean;
  detail_drawings: DetailDrawing[];
  // Phase 31 additions
  material_plan: MaterialPlan;
  cost_plan: CostPlan;
  // Phase 33 additions
  client_brief: ClientBrief;
  // Phase 34 additions
  revision_meta: RevisionMeta;
  // Phase 40 additions
  feasibility: Feasibility;
}

export interface ExportManifest {
  filename: string;
  format: string;
  path: string;
  created_at: string;
}

/** One compact / balanced / spacious variant generated from a prompt (Phase 10). */
export interface DesignOption {
  option_id: string;
  variant: "compact" | "balanced" | "spacious";
  score: number;
  summary: string;
  warnings: ProjectWarning[];
  preview: ArchitectureProject;
}

// ── Version history (Phase 19) ────────────────────────────────────────────────

export type VersionChangeType =
  | "generate"
  | "regenerate"
  | "edit"
  | "option"
  | "restore"
  | "sync";

export interface ProjectVersionMeta {
  version_id: string;
  created_at: string;
  change_type: VersionChangeType;
  summary: string;
  room_count: number;
  total_area: number;
  thumbnail: string | null;
}

export interface ProjectVersion {
  version_id: string;
  created_at: string;
  change_type: VersionChangeType;
  summary: string;
  snapshot: ArchitectureProject;
}

// ── Phase 33 — Architect-twin profile + client brief ─────────────────────────

export type BudgetLevel = "economy" | "standard" | "premium";
export type ParkingPreference = "none" | "two_wheeler" | "car" | "both";
export type UserRole = "owner" | "architect" | "student" | "other";
export type ExplanationStyle = "brief" | "detailed";

export interface ClientBrief {
  family_name: string;
  family_size: number;
  lifestyle: string;
  budget_level: BudgetLevel;
  budget_inr: number;
  style_preference: string;
  vastu_preference: boolean;
  parking_preference: ParkingPreference;
  future_expansion: boolean;
  special_needs: string[];
  material_preference: string;
  notes: string;
}

export interface UserProfile {
  role: UserRole;
  preferred_units: Units;
  default_location: string;
  default_style: string;
  default_orientation: Orientation;
  preferred_room_sizes: Record<string, number>;
  material_preferences: string[];
  output_preferences: string[];
  explanation_style: ExplanationStyle;
  common_project_types: string[];
}

// ── Phase 40 — Feasibility / Yield Analysis ──────────────────────────────────

export interface FeasibilityOption {
  name: string;
  label: string;
  unit_count: number;
  unit_type: string;
  unit_sizes_sqft: number[];
  coverage_pct: number;
  built_up_area: number;
  parking_slots: number;
  description: string;
  trade_offs: string[];
}

export interface Feasibility {
  site_area: number;
  usable_footprint: number;
  coverage_pct: number;
  fsi_far: number;
  buildable_area: number;
  floors: number;
  parking_estimate: number;
  options: FeasibilityOption[];
  missing_inputs: string[];
  warnings: string[];
  assumptions: string[];
  confidence: number;
  needs_review: boolean;
  generated: boolean;
  road_width_ft: number;
}

// ── Phase 41 — Collaboration / Review / QA ───────────────────────────────────

export type ReviewCategory = "spatial" | "mep" | "compliance" | "boq" | "detail" | "export" | "general";
export type ReviewStatus = "open" | "in_progress" | "resolved";
export type ReviewPriority = "low" | "medium" | "high";
export type QAStatus = "pass" | "fail" | "warning" | "not_checked";

export interface ReviewIssue {
  id: string;
  object_ref: string | null;
  category: ReviewCategory;
  title: string;
  description: string;
  status: ReviewStatus;
  priority: ReviewPriority;
  assigned_to: string | null;
  created_at: string;
  resolved_at: string | null;
  resolution_note: string;
  created_by: string;
}

export interface QACheckItem {
  id: string;
  category: ReviewCategory;
  title: string;
  description: string;
  status: QAStatus;
  detail: string;
}

export interface QAChecklist {
  project_id: string;
  items: QACheckItem[];
  passed: number;
  failed: number;
  warnings: number;
  not_checked: number;
  completion_pct: number;
  generated_at: string;
  advisory: string;
}

// ── Phase 39 — Reference / scan-to-plan ──────────────────────────────────────

export type ReferenceType =
  | "sketch"
  | "photo"
  | "pdf_page"
  | "site_plan"
  | "existing_plan"
  | "reference_image";

export type ScaleStatus = "uncalibrated" | "calibrated" | "auto_detected";

export interface ScaleCalibration {
  p1_x: number;
  p1_y: number;
  p2_x: number;
  p2_y: number;
  known_distance_ft: number;
  pixels_per_foot: number;
  origin_x_ft: number;
  origin_y_ft: number;
}

export interface ExtractedEntity {
  id: string;
  entity_type: string;
  confidence: number;
  geometry: Record<string, unknown>;
  label: string | null;
  needs_review: boolean;
  linked_project_object_id: string | null;
}

export interface ReferenceAsset {
  id: string;
  project_id: string;
  file_name: string;
  file_path: string;
  mime_type: string;
  file_size_bytes: number;
  reference_type: ReferenceType;
  scale_status: ScaleStatus;
  calibration: ScaleCalibration | null;
  extracted_entities: ExtractedEntity[];
  needs_review: boolean;
  linked_project_objects: string[];
  notes: string;
  created_at: string;
  updated_at: string;
}

export function roomArea(room: Room): number {
  return room.width * room.depth;
}

export function formatRoomSize(room: Room): string {
  return `${room.width} × ${room.depth}`;
}

export function totalBuiltArea(project: ArchitectureProject): number {
  return project.rooms.reduce((sum, room) => sum + roomArea(room), 0);
}

export function unitLabel(units: Units): string {
  return units === "feet" ? "ft" : "m";
}
