import { TopBar } from "@/components/layout/top-bar";

function PanelPlaceholder({
  title,
  note,
}: {
  title: string;
  note: string;
}) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-border bg-card">
      <div className="border-b border-border px-4 py-3 text-sm font-medium">
        {title}
      </div>
      <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
        {note}
      </div>
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <div className="flex h-screen flex-col bg-muted/40">
      <TopBar active="/workspace" />

      <main className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-[280px_minmax(0,1fr)_320px]">
        <PanelPlaceholder
          title="Prompt"
          note="Prompt input, templates, and the Generate button land in Phase 2."
        />
        <PanelPlaceholder
          title="Preview"
          note="2D floor plan canvas and 3D massing tab land in Phase 2."
        />
        <PanelPlaceholder
          title="Parameters"
          note="Parameter editor, room schedule, exports, and warnings land in Phase 2."
        />
      </main>
    </div>
  );
}
