/**
 * Intelligence report types — mirrors backend app/core/intelligence/models.py.
 * Phase 13.
 */

export type CheckSeverity = "info" | "warning" | "error";

export interface SpatialCheck {
  rule_id: string;
  severity: CheckSeverity;
  message: string;
  room_id?: string | null;
  detail?: string | null;
}

export interface RoomAreaEntry {
  room_id: string;
  room_name: string;
  room_type: string;
  gross_area: number;
  carpet_area: number;
}

export interface AreaSummary {
  site_area: number;
  built_up_area: number;
  carpet_area: number;
  circulation_area: number;
  coverage_ratio: number;   // percentage
  floor_efficiency: number; // percentage
  rooms: RoomAreaEntry[];
}

export interface VastuSuggestion {
  rule_id: string;
  severity: CheckSeverity;
  message: string;
  room_id?: string | null;
  direction?: string | null;
}

export interface IntelligenceReport {
  project_id: string;
  spatial_checks: SpatialCheck[];
  area_summary: AreaSummary;
  vastu_suggestions: VastuSuggestion[] | null;
}
