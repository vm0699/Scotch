/**
 * Starter templates shown on the dashboard and in the workspace template
 * selector. `thumbnail` holds abstract room rectangles (in a 100x70 viewBox)
 * for the schematic preview drawn on each card.
 */

export interface TemplateThumbnailRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ProjectTemplate {
  id: string;
  name: string;
  description: string;
  prompt: string;
  siteSize: string;
  tags: string[];
  thumbnail: TemplateThumbnailRect[];
}

export const PROJECT_TEMPLATES: ProjectTemplate[] = [
  {
    id: "2bhk-apartment",
    name: "2BHK Apartment",
    description: "Living, kitchen, 2 bedrooms, 2 baths, balcony, parking.",
    prompt:
      "Design a 2BHK apartment on a 30x50 ft east-facing site with living room, kitchen, 2 bedrooms, 2 bathrooms, balcony, and parking.",
    siteSize: "30 × 50 ft",
    tags: ["Residential"],
    thumbnail: [
      { x: 4, y: 4, w: 38, h: 34 },
      { x: 4, y: 42, w: 24, h: 24 },
      { x: 32, y: 42, w: 28, h: 24 },
      { x: 46, y: 4, w: 26, h: 34 },
      { x: 76, y: 4, w: 20, h: 26 },
      { x: 64, y: 42, w: 32, h: 24 },
    ],
  },
  {
    id: "3bhk-villa",
    name: "3BHK Villa",
    description: "Spacious villa with dining, 3 bedrooms, and garden front.",
    prompt:
      "Design a 3BHK villa on a 40x60 ft north-facing site with living room, dining, kitchen, 3 bedrooms, 3 bathrooms, balcony, and parking.",
    siteSize: "40 × 60 ft",
    tags: ["Residential"],
    thumbnail: [
      { x: 4, y: 4, w: 30, h: 28 },
      { x: 38, y: 4, w: 26, h: 28 },
      { x: 68, y: 4, w: 28, h: 40 },
      { x: 4, y: 36, w: 30, h: 30 },
      { x: 38, y: 36, w: 26, h: 30 },
      { x: 68, y: 48, w: 28, h: 18 },
    ],
  },
  {
    id: "studio-apartment",
    name: "Studio Apartment",
    description: "Compact open-plan studio with kitchenette and bath.",
    prompt:
      "Design a studio apartment on a 20x30 ft south-facing site with an open living and sleeping area, kitchenette, and bathroom.",
    siteSize: "20 × 30 ft",
    tags: ["Residential", "Compact"],
    thumbnail: [
      { x: 4, y: 4, w: 60, h: 62 },
      { x: 68, y: 4, w: 28, h: 30 },
      { x: 68, y: 38, w: 28, h: 28 },
    ],
  },
  {
    id: "small-cafe",
    name: "Small Cafe",
    description: "Seating area, counter, kitchen, and restroom.",
    prompt:
      "Design a small cafe on a 25x40 ft site with a seating area, service counter, kitchen, storage, and restroom.",
    siteSize: "25 × 40 ft",
    tags: ["Commercial"],
    thumbnail: [
      { x: 4, y: 4, w: 56, h: 62 },
      { x: 64, y: 4, w: 32, h: 20 },
      { x: 64, y: 28, w: 32, h: 22 },
      { x: 64, y: 54, w: 32, h: 12 },
    ],
  },
  {
    id: "office-layout",
    name: "Office Layout",
    description: "Workstations, cabins, meeting room, and pantry.",
    prompt:
      "Design an office layout on a 50x80 ft site with open workstations, 2 cabins, a meeting room, pantry, and restrooms.",
    siteSize: "50 × 80 ft",
    tags: ["Commercial", "Later phase"],
    thumbnail: [
      { x: 4, y: 4, w: 50, h: 40 },
      { x: 58, y: 4, w: 18, h: 18 },
      { x: 78, y: 4, w: 18, h: 18 },
      { x: 58, y: 26, w: 38, h: 18 },
      { x: 4, y: 48, w: 50, h: 18 },
      { x: 58, y: 48, w: 38, h: 18 },
    ],
  },
  {
    id: "duplex-house",
    name: "Duplex House",
    description: "Two-floor family home with stair core and terrace.",
    prompt:
      "Design a duplex house on a 30x50 ft west-facing site with living room, kitchen, dining, 3 bedrooms, 3 bathrooms, staircase, and terrace.",
    siteSize: "30 × 50 ft",
    tags: ["Residential", "2 floors"],
    thumbnail: [
      { x: 4, y: 4, w: 40, h: 30 },
      { x: 48, y: 4, w: 22, h: 30 },
      { x: 74, y: 4, w: 22, h: 30 },
      { x: 4, y: 38, w: 28, h: 28 },
      { x: 36, y: 38, w: 34, h: 28 },
      { x: 74, y: 38, w: 22, h: 28 },
    ],
  },
];
