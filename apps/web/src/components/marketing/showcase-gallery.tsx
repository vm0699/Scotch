import type { ArchitectureProject } from "@/features/project/types";
import { FloorPlanSvg } from "@/features/plan/floor-plan-svg";
import { MOCK_ARCHITECTURE_PROJECT } from "@/features/project/mock-architecture-project";
import { Reveal } from "@/components/marketing/reveal";

// Lightweight, valid variants rendered with the real SVG engine — honest
// "this is the actual output" samples, no image pipeline required. Openings are
// left empty so each sample stays self-contained.
const STUDIO: ArchitectureProject = {
  ...MOCK_ARCHITECTURE_PROJECT,
  id: "showcase-studio",
  name: "Studio · 24 × 32 ft",
  site: { width: 24, depth: 32, orientation: "east" },
  doors: [],
  windows: [],
  rooms: [
    { id: "living", name: "Living", type: "living", x: 0, y: 0, width: 14, depth: 16, level: 0 },
    { id: "kitchen", name: "Kitchen", type: "kitchen", x: 14, y: 0, width: 10, depth: 10, level: 0 },
    { id: "bath", name: "Bath", type: "bathroom", x: 14, y: 10, width: 10, depth: 8, level: 0 },
    { id: "bed", name: "Bedroom", type: "bedroom", x: 0, y: 16, width: 14, depth: 16, level: 0 },
  ],
};

const VILLA: ArchitectureProject = {
  ...MOCK_ARCHITECTURE_PROJECT,
  id: "showcase-villa",
  name: "Villa · 40 × 55 ft",
  site: { width: 40, depth: 55, orientation: "north" },
  doors: [],
  windows: [],
  rooms: [
    { id: "parking", name: "Parking", type: "parking", x: 0, y: 0, width: 14, depth: 18, level: 0 },
    { id: "living", name: "Living", type: "living", x: 14, y: 0, width: 26, depth: 18, level: 0 },
    { id: "kitchen", name: "Kitchen", type: "kitchen", x: 0, y: 18, width: 13, depth: 14, level: 0 },
    { id: "dining", name: "Dining", type: "dining", x: 13, y: 18, width: 13, depth: 14, level: 0 },
    { id: "bath-1", name: "Bath", type: "bathroom", x: 26, y: 18, width: 14, depth: 8, level: 0 },
    { id: "bed-1", name: "Master Bed", type: "bedroom", x: 0, y: 32, width: 16, depth: 16, level: 0 },
    { id: "bed-2", name: "Bedroom 2", type: "bedroom", x: 16, y: 32, width: 12, depth: 16, level: 0 },
    { id: "bath-2", name: "Bath", type: "bathroom", x: 28, y: 32, width: 12, depth: 10, level: 0 },
  ],
};

const SAMPLES: { project: ArchitectureProject; tag: string }[] = [
  { project: MOCK_ARCHITECTURE_PROJECT, tag: "2BHK · 30 × 50 ft" },
  { project: STUDIO, tag: "Compact studio" },
  { project: VILLA, tag: "Family villa" },
];

export function ShowcaseGallery() {
  return (
    <section id="showcase" className="border-t border-border px-6 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Drawing-standard output
          </h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground">
            Every plan is rendered to architectural convention — these samples
            come straight out of the Scotch engine.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {SAMPLES.map(({ project, tag }, i) => (
            <Reveal
              key={project.id}
              delay={(i % 3) * 80}
              className="group overflow-hidden rounded-2xl border border-border bg-card transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
            >
              <div className="flex h-64 items-center justify-center bg-[#fafafa] p-5 transition-colors duration-300 dark:bg-muted/30">
                <FloorPlanSvg
                  project={project}
                  className="h-full w-auto max-w-full transition-transform duration-300 group-hover:scale-105"
                />
              </div>
              <div className="flex items-center justify-between border-t border-border px-4 py-3">
                <span className="text-sm font-medium">{project.name}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${i % 2 === 0 ? "tint-red" : "tint-ink"}`}
                >
                  {tag}
                </span>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
