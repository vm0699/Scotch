"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FolderPlus, Plus, RefreshCw } from "lucide-react";

import { ProjectCard } from "@/components/dashboard/project-card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  createProject,
  deleteProject,
  listProjects,
  type ProjectSummary,
} from "@/features/api/client";

type ListState =
  | { state: "loading" }
  | { state: "ready"; projects: ProjectSummary[] }
  | { state: "offline" };

export function NewProjectButton() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      const stored = await createProject({
        name: name.trim() || "Untitled Project",
      });
      router.push(`/workspace?project=${stored.id}`);
    } catch {
      setError("Engine offline — start it with npm run dev:api and retry.");
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus data-icon="inline-start" />
          New Project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>
            Name it now, describe it in the workspace.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <Label htmlFor="project-name">Project name</Label>
          <Input
            id="project-name"
            value={name}
            autoFocus
            placeholder="Untitled Project"
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleCreate();
            }}
          />
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => void handleCreate()} disabled={busy}>
            {busy ? "Creating…" : "Create project"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ProjectsSection() {
  const [list, setList] = useState<ListState>({ state: "loading" });
  const [pendingDelete, setPendingDelete] = useState<ProjectSummary | null>(
    null,
  );
  const [deleting, setDeleting] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const projects = await listProjects();
      setList({ state: "ready", projects });
    } catch {
      setList({ state: "offline" });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteProject(pendingDelete.id);
      await refresh();
    } catch {
      // Listing refresh below surfaces the offline state.
      await refresh();
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  }

  return (
    <section className="mt-8">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-muted-foreground">
          Recent projects
        </h2>
        {list.state === "offline" && (
          <Button variant="ghost" size="xs" onClick={() => void refresh()}>
            <RefreshCw data-icon="inline-start" />
            Retry
          </Button>
        )}
      </div>

      <div className="mt-3">
        {list.state === "loading" && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="flex items-start gap-3.5 rounded-xl border border-border bg-card p-4"
              >
                <Skeleton className="size-9 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-2/5" />
                  <Skeleton className="h-3 w-4/5" />
                  <Skeleton className="h-3 w-3/5" />
                </div>
              </div>
            ))}
          </div>
        )}

        {list.state === "offline" && (
          <div className="flex h-32 flex-col items-center justify-center gap-1.5 rounded-xl border border-dashed border-border bg-card text-center">
            <p className="text-sm text-muted-foreground">
              Engine offline — projects live on your machine.
            </p>
            <p className="font-mono text-xs text-muted-foreground/70">
              npm run dev:api
            </p>
          </div>
        )}

        {list.state === "ready" && list.projects.length === 0 && (
          <div className="flex h-32 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-card text-center">
            <FolderPlus className="size-5 text-muted-foreground/60" />
            <p className="text-sm text-muted-foreground">
              No projects yet — create one or start from a template below.
            </p>
          </div>
        )}

        {list.state === "ready" && list.projects.length > 0 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {list.projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onDelete={setPendingDelete}
              />
            ))}
          </div>
        )}
      </div>

      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete “{pendingDelete?.name}”?</DialogTitle>
            <DialogDescription>
              This removes the project and its exports from your machine.
              There is no undo until version history lands (Phase 19).
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => void confirmDelete()}
              disabled={deleting}
            >
              {deleting ? "Deleting…" : "Delete project"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
