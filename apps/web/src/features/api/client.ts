/**
 * Typed client for the Scotch backend API.
 * All frontend↔backend traffic goes through this module.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers: {
        Accept: "application/json",
        ...(body !== undefined && { "Content-Type": "application/json" }),
      },
      ...(body !== undefined && { body: JSON.stringify(body) }),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(`Backend unreachable at ${API_BASE_URL}`);
  }
  if (!response.ok) {
    throw new ApiError(
      `${method} ${path} failed with ${response.status}`,
      response.status,
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function apiGet<T>(path: string, init?: { signal?: AbortSignal }): Promise<T> {
  return apiRequest<T>("GET", path, undefined, init?.signal);
}

export interface HealthResponse {
  app: string;
  status: string;
  version: string;
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health", { signal });
}

/** A single host-app detection result from GET /system/integrations. */
export interface IntegrationStatus {
  installed: boolean;
  version: string | null;
  detail: string | null;
}

export type IntegrationKey = "sketchup" | "revit" | "rhino" | "blender";

export interface SystemIntegrations {
  platform: string;
  integrations: Record<IntegrationKey, IntegrationStatus>;
}

/**
 * Detect which desktop host apps are installed on this machine. Only the local
 * backend can see local installs, so this is meaningful only while the backend
 * is running; callers should treat a thrown ApiError as "detection unavailable".
 */
export function getSystemIntegrations(
  signal?: AbortSignal,
): Promise<SystemIntegrations> {
  return apiGet<SystemIntegrations>("/system/integrations", { signal });
}

export function getSampleProject(
  signal?: AbortSignal,
): Promise<import("@/features/project/types").ArchitectureProject> {
  return apiGet("/projects/sample", { signal });
}

// ── Generation (Phase 5 / 10) ─────────────────────────────────────

type ArchitectureProject = import("@/features/project/types").ArchitectureProject;
type ProjectWarning = import("@/features/project/types").ProjectWarning;
type DesignOption = import("@/features/project/types").DesignOption;

export interface GenerateResponse {
  project: ArchitectureProject;
  summary: string;
  warnings: ProjectWarning[];
}

export function generateFromPrompt(
  prompt: string,
  mode?: "deterministic" | "ai" | "hybrid",
): Promise<GenerateResponse> {
  return apiRequest("POST", "/generate/from-prompt", {
    prompt,
    ...(mode ? { mode } : {}),
  });
}

// ── Design Options (Phase 10) ─────────────────────────────────────

export interface OptionsResponse {
  options: DesignOption[];
  prompt: string;
}

export function generateOptions(
  prompt: string,
  mode?: "deterministic" | "ai" | "hybrid",
): Promise<OptionsResponse> {
  return apiRequest("POST", "/generate/options", {
    prompt,
    ...(mode ? { mode } : {}),
  });
}

// ── Generation settings (Phase 9) ─────────────────────────────────

export interface GenerationSettings {
  mode: string;
  provider: string;
  anthropic_configured: boolean;
  openai_configured: boolean;
}

export function getGenerationSettings(
  signal?: AbortSignal,
): Promise<GenerationSettings> {
  return apiGet<GenerationSettings>("/settings/generation", { signal });
}

/** A single parameter edit applied via /generate/regenerate. */
export interface ParameterChange {
  key:
    | "site_width"
    | "site_depth"
    | "orientation"
    | "floors"
    | "floor_height"
    | "style"
    | "room_width"
    | "room_depth"
    | "room_name"
    | "room_level"
    | "add_room"
    | "remove_room"
    | "show_furniture"
    | "show_dimensions"
    | "show_mep";
  value: string | number | boolean;
  target_id?: string;
}

// ── MEP (Phase 29) ────────────────────────────────────────────────────────────

export type MEPSystem = import("@/features/project/types").MEPSystem;

export interface MepGenerateResponse {
  mep_plan: import("@/features/project/types").MEPPlan;
  id: string;
  [key: string]: unknown;
}

export function generateMep(
  projectId: string,
  systems?: MEPSystem[],
): Promise<MepGenerateResponse> {
  return apiRequest<MepGenerateResponse>("POST", `/projects/${projectId}/mep`, { systems });
}

export function moveMepPoint(
  projectId: string,
  pointId: string,
  x: number,
  y: number,
): Promise<MepGenerateResponse> {
  return apiRequest<MepGenerateResponse>(
    "PATCH",
    `/projects/${projectId}/mep/points/${pointId}`,
    { x, y },
  );
}

// ── Detail Drawings (Phase 30) ────────────────────────────────────────────────

export type DetailType = import("@/features/project/types").DetailType;
export type DetailDrawing = import("@/features/project/types").DetailDrawing;

export interface DetailListResponse {
  detail_drawings: Array<{
    id: string; name: string; detail_type: DetailType;
    scale: string; view: string; stale: boolean;
    confidence: number; needs_review: boolean;
    source_object_ids: string[];
  }>;
  count: number;
}

export function generateDetail(
  projectId: string,
  detail_type: DetailType,
  source_id: string,
): Promise<DetailDrawing> {
  return apiRequest<DetailDrawing>("POST", `/projects/${projectId}/details`, { detail_type, source_id });
}

export function listDetails(projectId: string, signal?: AbortSignal): Promise<DetailListResponse> {
  return apiGet<DetailListResponse>(`/projects/${projectId}/details`, { signal });
}

export function getDetail(projectId: string, detailId: string): Promise<DetailDrawing> {
  return apiGet<DetailDrawing>(`/projects/${projectId}/details/${detailId}`);
}

export function deleteDetail(projectId: string, detailId: string): Promise<void> {
  return apiRequest<void>("DELETE", `/projects/${projectId}/details/${detailId}`);
}

export function getDetailSvgUrl(projectId: string, detailId: string): string {
  return `${API_BASE_URL}/projects/${projectId}/details/${detailId}/svg`;
}

// ── BOQ / Cost (Phase 31) ─────────────────────────────────────────────────────

export type TileSpec = import("@/features/project/types").TileSpec;
export type RoomFinish = import("@/features/project/types").RoomFinish;
export type RateEntry = import("@/features/project/types").RateEntry;
export type MaterialPlan = import("@/features/project/types").MaterialPlan;
export type BOQItem = import("@/features/project/types").BOQItem;
export type CategoryTotal = import("@/features/project/types").CategoryTotal;
export type CostPlan = import("@/features/project/types").CostPlan;

export interface BOQSummary {
  generated: boolean;
  grand_total: number;
  category_totals: CategoryTotal[];
  missing_rates: string[];
  assumptions: string[];
  confidence: number;
  needs_review: boolean;
  boq_items: BOQItem[];
}

export function calculateBOQ(projectId: string): Promise<ArchitectureProject> {
  return apiRequest<ArchitectureProject>(
    "POST",
    `/projects/${projectId}/chat`,
    { message: "calculate BOQ" },
  ).then((r: unknown) => (r as { project?: ArchitectureProject }).project ?? (r as ArchitectureProject));
}

export function getBOQSummary(projectId: string): Promise<BOQSummary> {
  return apiGet<BOQSummary>(`/projects/${projectId}/boq`);
}

export function editRate(
  projectId: string,
  category: string,
  item: string,
  rate: number,
): Promise<ArchitectureProject> {
  return apiRequest<ArchitectureProject>(
    "POST",
    `/projects/${projectId}/boq/rates`,
    { category, item, rate },
  );
}

export function exportBOQ(
  projectId: string,
  format: "csv" | "json",
): Promise<Blob> {
  return fetch(
    `${API_BASE_URL}/projects/${projectId}/boq/export?format=${format}`,
  ).then((r) => r.blob());
}

// ── Program grid (Phase 21) ───────────────────────────────────────────────────

export interface ProgramSiteRow {
  width: number;
  depth: number;
  orientation: string;
  floors: number;
  floor_height: number;
}

export interface ProgramRoomRow {
  id: string;
  name: string;
  type: string;
  width: number;
  depth: number;
  area: number;
  level: number;
}

export interface ProgramTotals {
  built_up_area: number;
  site_area: number;
  coverage_pct: number;
  room_count: number;
}

export interface ProgramTable {
  site: ProgramSiteRow;
  rooms: ProgramRoomRow[];
  totals: ProgramTotals;
}

export function getProgramTable(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProgramTable> {
  return apiGet<ProgramTable>(`/projects/${projectId}/program`, { signal });
}

export function regenerateProject(
  project: ArchitectureProject,
  changes: ParameterChange[],
): Promise<GenerateResponse> {
  return apiRequest("POST", "/generate/regenerate", { project, changes });
}

// ── Project storage (Phase 4) ──────────────────────────────────────

/** Persistence envelope around the universal model (mirrors backend StoredProject). */
export interface StoredProject {
  id: string;
  name: string;
  prompt?: string | null;
  created_at: string;
  updated_at: string;
  project?: ArchitectureProject | null;
  options?: DesignOption[];
}

/** Listing row for dashboards (mirrors backend ProjectSummary). */
export interface ProjectSummary {
  id: string;
  name: string;
  prompt?: string | null;
  created_at: string;
  updated_at: string;
  room_count: number;
  site_label?: string | null;
}

export function listProjects(signal?: AbortSignal): Promise<ProjectSummary[]> {
  return apiGet("/projects", { signal });
}

export function createProject(body: {
  name: string;
  prompt?: string;
}): Promise<StoredProject> {
  return apiRequest("POST", "/projects", body);
}

export function getProject(
  projectId: string,
  signal?: AbortSignal,
): Promise<StoredProject> {
  return apiGet(`/projects/${projectId}`, { signal });
}

export function updateProject(
  projectId: string,
  body: {
    name?: string;
    prompt?: string;
    project?: ArchitectureProject;
    options?: DesignOption[];
    change_type?: "generate" | "regenerate" | "edit" | "option";
    version_summary?: string;
  },
): Promise<StoredProject> {
  return apiRequest("PATCH", `/projects/${projectId}`, body);
}

export function deleteProject(projectId: string): Promise<void> {
  return apiRequest("DELETE", `/projects/${projectId}`);
}

// ── Intelligence (Phase 13) ───────────────────────────────────────

export type { IntelligenceReport, AreaSummary, SpatialCheck, VastuSuggestion } from "@/features/intelligence/types";

export function getIntelligence(
  projectId: string,
  vastu = false,
  signal?: AbortSignal,
): Promise<import("@/features/intelligence/types").IntelligenceReport> {
  return apiGet(`/projects/${projectId}/intelligence?vastu=${vastu}`, { signal });
}

// ── Cameras (Phase 17) ────────────────────────────────────────────

export function getCameras(
  projectId: string,
  signal?: AbortSignal,
): Promise<import("@/features/project/types").CameraSuggestion[]> {
  return apiGet(`/projects/${projectId}/cameras`, { signal });
}

// ── Interior furniture catalog (Phase 43) ─────────────────────────────────────

export type CatalogItem = import("@/features/project/types").CatalogItem;

/** mesh_url / thumbnail_url from CatalogItem are API-relative — resolve before fetching/loading. */
export function resolveCatalogAssetUrl(relativeUrl: string): string {
  return `${API_BASE_URL}${relativeUrl}`;
}

export function getCatalog(
  filters?: { category?: string; style?: string },
  signal?: AbortSignal,
): Promise<CatalogItem[]> {
  const params = new URLSearchParams();
  if (filters?.category) params.set("category", filters.category);
  if (filters?.style) params.set("style", filters.style);
  const qs = params.toString();
  return apiGet<CatalogItem[]>(`/catalog${qs ? `?${qs}` : ""}`, { signal });
}

export function getCatalogItem(catalogId: string, signal?: AbortSignal): Promise<CatalogItem> {
  return apiGet<CatalogItem>(`/catalog/${catalogId}`, { signal });
}

// ── Interior generation / editing (Phase 43 Stage 43.3–43.4) ──────────────────

export type RoomInterior = import("@/features/project/types").RoomInterior;

export interface InteriorResponse {
  room_id: string;
  furniture: import("@/features/project/types").FurnitureItem[];
  warnings: string[];
  room_interior: RoomInterior;
  project: ArchitectureProject;
}

export function generateInterior(
  projectId: string,
  roomId: string,
  req: { mode?: "deterministic" | "ai" | "hybrid"; style?: string; prompt?: string } = {},
): Promise<InteriorResponse> {
  return apiRequest<InteriorResponse>("POST", `/projects/${projectId}/rooms/${roomId}/interior/generate`, req);
}

export function getInterior(projectId: string, roomId: string, signal?: AbortSignal): Promise<InteriorResponse> {
  return apiGet<InteriorResponse>(`/projects/${projectId}/rooms/${roomId}/interior`, { signal });
}

export type InteriorEditAction =
  | { action: "move"; item_id: string; x: number; y: number }
  | { action: "rotate"; item_id: string; rotation: 0 | 90 | 180 | 270 }
  | { action: "delete"; item_id: string }
  | { action: "swap"; item_id: string; catalog_id: string }
  | { action: "add"; catalog_id: string; x: number; y: number; rotation?: 0 | 90 | 180 | 270 }
  | { action: "recolor"; item_id: string; color: string; slot?: string };

export function editInterior(
  projectId: string,
  roomId: string,
  edit: InteriorEditAction,
): Promise<InteriorResponse> {
  return apiRequest<InteriorResponse>("POST", `/projects/${projectId}/rooms/${roomId}/interior/edit`, edit);
}

export interface RoomInteriorResult {
  room_id: string;
  room_name: string;
  status: "designed" | "skipped" | "empty_template";
  item_count: number;
  warnings: string[];
}

export interface InteriorGenerateAllResponse {
  results: RoomInteriorResult[];
  project: ArchitectureProject;
}

export function generateAllInteriors(
  projectId: string,
  req: { mode?: "deterministic" | "ai" | "hybrid"; style?: string; overwrite?: boolean } = {},
): Promise<InteriorGenerateAllResponse> {
  return apiRequest<InteriorGenerateAllResponse>("POST", `/projects/${projectId}/interior/generate-all`, req);
}

// ── Version history (Phase 19) ────────────────────────────────────────────────

export type { ProjectVersionMeta, ProjectVersion, VersionChangeType } from "@/features/project/types";

export function listVersions(
  projectId: string,
  signal?: AbortSignal,
): Promise<import("@/features/project/types").ProjectVersionMeta[]> {
  return apiGet(`/projects/${projectId}/versions`, { signal });
}

export function restoreVersion(
  projectId: string,
  versionId: string,
): Promise<StoredProject> {
  return apiRequest("POST", `/projects/${projectId}/versions/${versionId}/restore`);
}

// ── Exports (Phase 7 / 11 / 12 / 13) ────────────────────────────

export type ExportFormat =
  | "json"
  | "svg"
  | "png"
  | "dxf"
  | "sketchup"
  | "blender"
  | "rhino"
  | "sheet_svg"
  | "sheet_pdf"
  | "schedule_json"
  | "schedule_csv"
  | "ifc";

export interface ExportManifest {
  filename: string;
  format: string;
  path: string;
  created_at: string;
}

export function triggerExport(
  projectId: string,
  format: ExportFormat,
): Promise<ExportManifest> {
  return apiRequest("POST", `/projects/${projectId}/exports/${format}`);
}

export function listExports(projectId: string): Promise<ExportManifest[]> {
  return apiGet(`/projects/${projectId}/exports`);
}

// ── Chat (Phase 24) ──────────────────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatImage {
  media_type: string;
  data: string; // base64, no "data:" prefix
}

/** Read an image File into a base64 ChatImage payload for the chat vision endpoint. */
export function fileToChatImage(file: File): Promise<ChatImage> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.slice(result.indexOf(",") + 1);
      resolve({ media_type: file.type || "image/png", data: base64 });
    };
    reader.onerror = () => reject(reader.error ?? new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}

export interface ChatResponse {
  reply: string;
  project: ArchitectureProject | null;
  tool_calls: string[];
}

export function sendChatMessage(
  projectId: string,
  message: string,
  history: ChatMessage[] = [],
  images: ChatImage[] = [],
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("POST", `/projects/${projectId}/chat`, {
    message,
    history,
    images,
  });
}

// ── Render (Phase 23) ────────────────────────────────────────────────────────

export interface RenderStyleInfo {
  id: string;
  name: string;
  description: string;
  swatch_color: string;
}

export interface RenderResponse {
  render_b64: string;
  style: string;
  camera_id: string;
}

export function getRenderStyles(signal?: AbortSignal): Promise<RenderStyleInfo[]> {
  return apiGet<RenderStyleInfo[]>("/render/styles", { signal });
}

export function createRender(
  projectId: string,
  body: {
    camera_id: string;
    style: string;
    conditioning_image_b64?: string | null;
  },
): Promise<RenderResponse> {
  return apiRequest<RenderResponse>("POST", `/projects/${projectId}/render`, body);
}

// ── Sync protocol (Phase 25) ─────────────────────────────────────────────────

export interface SyncRoom {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  width: number;
  depth: number;
  level: number;
}

export interface SyncContract {
  project_id: string;
  rooms: SyncRoom[];
  source_version: string | null;
}

export interface SyncConflict {
  room_id: string;
  room_name: string;
  field: string;
  scotch_value: number;
  incoming_value: number;
  delta: number;
}

export interface SyncPushResponse {
  added: string[];
  updated: string[];
  flagged: string[];
  conflicts: SyncConflict[];
  project: ArchitectureProject;
}

export function pullSync(
  projectId: string,
  signal?: AbortSignal,
): Promise<SyncContract> {
  return apiGet<SyncContract>(`/projects/${projectId}/sync`, { signal });
}

export function pushSync(
  projectId: string,
  body: { rooms: SyncRoom[]; source?: string },
): Promise<SyncPushResponse> {
  return apiRequest<SyncPushResponse>("POST", `/projects/${projectId}/sync`, body);
}

// ── Compliance (Phase 27) ────────────────────────────────────────────────────

export type RuleStatus = "pass" | "fail" | "warn" | "skip";

export interface RuleResult {
  rule_id: string;
  category: string;
  description: string;
  status: RuleStatus;
  value: number | null;
  limit: number | null;
  unit: string | null;
  message: string;
}

export interface ComplianceReport {
  project_id: string;
  zone: string;
  passes_review: boolean;
  summary: string;
  rules: RuleResult[];
  front_setback_ft: number;
  side_setback_ft: number;
  rear_setback_ft: number;
  max_fsi: number;
}

export function getCompliance(
  projectId: string,
  signal?: AbortSignal,
): Promise<ComplianceReport> {
  return apiGet<ComplianceReport>(`/projects/${projectId}/compliance`, { signal });
}

// ── Tamil Nadu Advisory (Phase 32) ───────────────────────────────────────────

export type TNStatus = "pass" | "fail" | "warn" | "skip" | "advisory" | "missing_input";

export interface TNRuleResult {
  rule_id: string;
  category: string;
  title: string;
  status: TNStatus;
  source_name: string;
  source_section: string;
  source_url_or_path: string;
  confidence: number;
  needs_professional_verification: boolean;
  is_placeholder: boolean;
  value: number | null;
  limit: number | null;
  unit: string | null;
  message: string;
  missing_inputs: string[];
  advisory_items: string[];
}

export interface TNAdvisoryReport {
  project_id: string;
  jurisdiction: string;
  passes_advisory: boolean;
  summary: string;
  results: TNRuleResult[];
  missing_inputs: string[];
  disclaimer: string;
}

export function getTNAdvisory(
  projectId: string,
  roadWidthFt = 0,
  signal?: AbortSignal,
): Promise<TNAdvisoryReport> {
  return apiGet<TNAdvisoryReport>(
    `/projects/${projectId}/compliance/tn?road_width=${roadWidthFt}`,
    { signal },
  );
}

// ── Phase 33 — Profile + client brief ────────────────────────────────────────

export interface UserProfile {
  role: "owner" | "architect" | "student" | "other";
  preferred_units: "feet" | "meters";
  default_location: string;
  default_style: string;
  default_orientation: "north" | "south" | "east" | "west";
  preferred_room_sizes: Record<string, number>;
  material_preferences: string[];
  output_preferences: string[];
  explanation_style: "brief" | "detailed";
  common_project_types: string[];
  // Phase 37 — cloud/auth readiness
  account_mode: "local" | "cloud";
  display_name: string;
  cloud_email: string | null;
  cloud_user_id: string | null;
}

export interface ClientBrief {
  family_name: string;
  family_size: number;
  lifestyle: string;
  budget_level: "economy" | "standard" | "premium";
  budget_inr: number;
  style_preference: string;
  vastu_preference: boolean;
  parking_preference: "none" | "two_wheeler" | "car" | "both";
  future_expansion: boolean;
  special_needs: string[];
  material_preference: string;
  notes: string;
}

export function getUserProfile(signal?: AbortSignal): Promise<UserProfile> {
  return apiGet<UserProfile>("/profile", { signal });
}

export function updateUserProfile(
  updates: Partial<Omit<UserProfile, "preferred_room_sizes" | "material_preferences" | "output_preferences" | "common_project_types">>,
  signal?: AbortSignal,
): Promise<UserProfile> {
  return apiRequest<UserProfile>("PUT", "/profile", updates, signal);
}

export function getClientBrief(projectId: string, signal?: AbortSignal): Promise<ClientBrief> {
  return apiGet<ClientBrief>(`/profile/projects/${projectId}/brief`, { signal });
}

export function updateClientBrief(
  projectId: string,
  updates: Partial<ClientBrief>,
  signal?: AbortSignal,
): Promise<ClientBrief> {
  return apiRequest<ClientBrief>("PUT", `/profile/projects/${projectId}/brief`, updates, signal);
}

// ── Client Changes (Phase 34) ─────────────────────────────────────────────────

export type {
  ClientChangeRequest,
  AffectedItems,
  AffectedItem,
  ChangeStatus,
  ChangeSource,
  ChangePriority,
  RevisionMeta,
} from "@/features/project/types";

export interface CreateChangeBody {
  request_text: string;
  source?: "client" | "architect" | "chat" | "manual";
  priority?: "low" | "medium" | "high" | "urgent";
  compute_affected?: boolean;
}

export interface UpdateChangeBody {
  status?: import("@/features/project/types").ChangeStatus;
  summary?: string;
  cost_impact?: string;
  before_version?: string;
  after_version?: string;
}

export function createClientChange(
  projectId: string,
  body: CreateChangeBody,
): Promise<import("@/features/project/types").ClientChangeRequest> {
  return apiRequest("POST", `/projects/${projectId}/changes`, body);
}

export function listClientChanges(
  projectId: string,
  signal?: AbortSignal,
): Promise<import("@/features/project/types").ClientChangeRequest[]> {
  return apiGet(`/projects/${projectId}/changes`, { signal });
}

export function getClientChange(
  projectId: string,
  changeId: string,
): Promise<import("@/features/project/types").ClientChangeRequest> {
  return apiGet(`/projects/${projectId}/changes/${changeId}`);
}

export function updateClientChange(
  projectId: string,
  changeId: string,
  body: UpdateChangeBody,
): Promise<import("@/features/project/types").ClientChangeRequest> {
  return apiRequest("PATCH", `/projects/${projectId}/changes/${changeId}`, body);
}

export function getAffectedItems(
  projectId: string,
  changeId: string,
): Promise<import("@/features/project/types").AffectedItems> {
  return apiGet(`/projects/${projectId}/changes/${changeId}/affected`);
}

export function deleteClientChange(projectId: string, changeId: string): Promise<void> {
  return apiRequest<void>("DELETE", `/projects/${projectId}/changes/${changeId}`);
}

// ── References / Scan-to-Plan (Phase 39) ─────────────────────────────────────

export type { ReferenceAsset, ScaleCalibration, ReferenceType, ScaleStatus } from "@/features/project/types";

export interface CalibrateBody {
  p1_x: number;
  p1_y: number;
  p2_x: number;
  p2_y: number;
  known_distance_ft: number;
  origin_x_ft?: number;
  origin_y_ft?: number;
}

export function listReferences(
  projectId: string,
  signal?: AbortSignal,
): Promise<import("@/features/project/types").ReferenceAsset[]> {
  return apiGet(`/projects/${projectId}/references`, { signal });
}

export function uploadReference(
  projectId: string,
  file: File,
  referenceType = "reference_image",
  notes = "",
): Promise<import("@/features/project/types").ReferenceAsset> {
  const form = new FormData();
  form.append("file", file);
  form.append("reference_type", referenceType);
  form.append("notes", notes);
  return fetch(`${API_BASE_URL}/projects/${projectId}/references`, {
    method: "POST",
    body: form,
  }).then(async (r) => {
    if (!r.ok) throw new ApiError(`Upload failed: ${r.status}`, r.status);
    return r.json();
  });
}

export function deleteReference(projectId: string, refId: string): Promise<void> {
  return apiRequest<void>("DELETE", `/projects/${projectId}/references/${refId}`);
}

export function calibrateReference(
  projectId: string,
  refId: string,
  body: CalibrateBody,
): Promise<import("@/features/project/types").ReferenceAsset> {
  return apiRequest(`PATCH`, `/projects/${projectId}/references/${refId}/calibrate`, body);
}

export function getReferenceFileUrl(projectId: string, refId: string): string {
  return `${API_BASE_URL}/projects/${projectId}/references/${refId}/file`;
}

// ── Feasibility / Yield Analysis (Phase 40) ──────────────────────────────────

export type { Feasibility, FeasibilityOption } from "@/features/project/types";

export function runFeasibility(
  projectId: string,
  roadWidthFt = 0,
  signal?: AbortSignal,
): Promise<import("@/features/project/types").Feasibility> {
  return apiGet(
    `/projects/${projectId}/feasibility?road_width_ft=${roadWidthFt}`,
    { signal },
  );
}

// ── Review / QA Workflow (Phase 41) ──────────────────────────────────────────

export type {
  ReviewIssue,
  QAChecklist,
  QACheckItem,
  ReviewCategory,
  ReviewStatus,
  ReviewPriority,
  QAStatus,
} from "@/features/project/types";

export interface CreateReviewIssueBody {
  title: string;
  category?: import("@/features/project/types").ReviewCategory;
  description?: string;
  object_ref?: string | null;
  priority?: import("@/features/project/types").ReviewPriority;
}

export interface UpdateReviewIssueBody {
  title?: string;
  description?: string;
  status?: import("@/features/project/types").ReviewStatus;
  priority?: import("@/features/project/types").ReviewPriority;
  assigned_to?: string | null;
  resolution_note?: string;
}

export function listReviewIssues(
  projectId: string,
  signal?: AbortSignal,
): Promise<import("@/features/project/types").ReviewIssue[]> {
  return apiGet(`/projects/${projectId}/review/issues`, { signal });
}

export function createReviewIssue(
  projectId: string,
  body: CreateReviewIssueBody,
): Promise<import("@/features/project/types").ReviewIssue> {
  return apiRequest("POST", `/projects/${projectId}/review/issues`, body);
}

export function updateReviewIssue(
  projectId: string,
  issueId: string,
  body: UpdateReviewIssueBody,
): Promise<import("@/features/project/types").ReviewIssue> {
  return apiRequest("PATCH", `/projects/${projectId}/review/issues/${issueId}`, body);
}

export function deleteReviewIssue(
  projectId: string,
  issueId: string,
): Promise<{ deleted: string }> {
  return apiRequest("DELETE", `/projects/${projectId}/review/issues/${issueId}`);
}

export function runQAChecklist(
  projectId: string,
  signal?: AbortSignal,
): Promise<import("@/features/project/types").QAChecklist> {
  return apiGet(`/projects/${projectId}/review/qa`, { signal });
}

export function exportReviewReport(
  projectId: string,
  fmt: "json" | "text" = "json",
): Promise<Blob> {
  return fetch(
    `${API_BASE_URL}/projects/${projectId}/review/export?fmt=${fmt}`,
    { cache: "no-store" },
  ).then(async (r) => {
    if (!r.ok) throw new ApiError(`Review export failed: ${r.status}`, r.status);
    return r.blob();
  });
}

// ── Demo Fixtures (Phase 42) ──────────────────────────────────────────────────

export interface FixtureMeta {
  id: string;
  name: string;
  description: string;
}

export function listFixtures(signal?: AbortSignal): Promise<FixtureMeta[]> {
  return apiGet<FixtureMeta[]>("/fixtures", { signal });
}

export function loadFixture(
  fixtureId: string,
  signal?: AbortSignal,
): Promise<import("@/features/project/types").ArchitectureProject> {
  return apiGet(`/fixtures/${fixtureId}`, { signal });
}

/** Fetch an export file as a Blob for browser download. */
export async function fetchExportBlob(
  projectId: string,
  filename: string,
): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/projects/${projectId}/exports/${filename}`,
      { cache: "no-store" },
    );
  } catch {
    throw new ApiError(`Backend unreachable at ${API_BASE_URL}`);
  }
  if (!response.ok) {
    throw new ApiError(`Download failed with ${response.status}`, response.status);
  }
  return response.blob();
}
