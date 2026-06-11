/**
 * Placeholder recent projects shown on the dashboard until local project
 * storage lands (Phase 4). Centralized so components never hardcode data.
 */

export interface MockProjectSummary {
  id: string;
  name: string;
  promptSummary: string;
  siteSize: string;
  roomCount: number;
  updatedLabel: string;
}

export const MOCK_RECENT_PROJECTS: MockProjectSummary[] = [
  {
    id: "mock-2bhk-east",
    name: "2BHK Apartment Concept",
    promptSummary: "2BHK on a 30×50 ft east-facing site with balcony and parking",
    siteSize: "30 × 50 ft",
    roomCount: 8,
    updatedLabel: "Edited 2 hours ago",
  },
  {
    id: "mock-studio-loft",
    name: "Studio Loft",
    promptSummary: "Open-plan studio on a 20×30 ft site with kitchenette",
    siteSize: "20 × 30 ft",
    roomCount: 3,
    updatedLabel: "Edited yesterday",
  },
  {
    id: "mock-corner-cafe",
    name: "Corner Cafe",
    promptSummary: "Small cafe on a 25×40 ft site with counter and seating",
    siteSize: "25 × 40 ft",
    roomCount: 5,
    updatedLabel: "Edited 3 days ago",
  },
];
