"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, FolderOpen, LayoutGrid, Settings, Shapes, XCircle } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Sidebar } from "@/components/layout/sidebar";
import type { GenerationSettings } from "@/features/api/client";
import { getGenerationSettings } from "@/features/api/client";

const SIDEBAR_ITEMS = [
  { label: "Projects", href: "/dashboard", icon: LayoutGrid },
  { label: "Templates", href: "/dashboard#templates", icon: Shapes },
  { label: "Open workspace", href: "/workspace", icon: FolderOpen },
  { label: "Settings", href: "/dashboard/settings", icon: Settings, active: true },
];

function ProviderRow({
  name,
  envVar,
  configured,
}: {
  name: string;
  envVar: string;
  configured: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-3 py-2.5">
      <div>
        <p className="text-xs font-medium">{name}</p>
        <p className="font-mono text-[11px] text-muted-foreground">{envVar}</p>
      </div>
      {configured ? (
        <span className="flex items-center gap-1 text-[11px] text-emerald-600">
          <CheckCircle2 className="size-3.5" /> Configured
        </span>
      ) : (
        <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <XCircle className="size-3.5" /> Not set
        </span>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<GenerationSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getGenerationSettings()
      .then(setSettings)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell
      active="/dashboard"
      sidebar={<Sidebar items={SIDEBAR_ITEMS} footer="Scotch 0.1.0 · local" />}
    >
      <div className="mx-auto w-full max-w-3xl px-6 py-8">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Provider configuration and generation mode.
        </p>

        <div className="mt-8 space-y-5">
          {/* Generation mode */}
          <section className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-medium">Generation Mode</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Set via{" "}
              <code className="rounded bg-muted px-1 py-0.5 text-[11px]">
                SCOTCH_GENERATION_MODE
              </code>{" "}
              environment variable.
            </p>
            <div className="mt-4 flex items-center gap-2.5">
              {loading ? (
                <span className="h-6 w-28 animate-pulse rounded-md bg-muted" />
              ) : (
                <span className="rounded-md border border-border bg-muted px-2.5 py-1 font-mono text-xs font-medium">
                  {settings?.mode ?? "—"}
                </span>
              )}
              <span className="text-xs text-muted-foreground">active</span>
            </div>
          </section>

          {/* AI providers */}
          <section className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-medium">AI Providers</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Add a key to your{" "}
              <code className="rounded bg-muted px-1 py-0.5 text-[11px]">.env</code> file
              to unlock AI and Hybrid generation modes.
            </p>
            <div className="mt-4 space-y-2.5">
              {loading ? (
                <>
                  <div className="h-12 animate-pulse rounded-lg bg-muted" />
                  <div className="h-12 animate-pulse rounded-lg bg-muted" />
                </>
              ) : (
                <>
                  <ProviderRow
                    name="Anthropic (Claude)"
                    envVar="SCOTCH_ANTHROPIC_API_KEY"
                    configured={settings?.anthropic_configured ?? false}
                  />
                  <ProviderRow
                    name="OpenAI-compatible"
                    envVar="SCOTCH_OPENAI_API_KEY"
                    configured={settings?.openai_configured ?? false}
                  />
                </>
              )}
            </div>
          </section>

          {/* How to configure */}
          <section className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-medium">How to configure</h2>
            <div className="mt-3 space-y-2 text-xs leading-5 text-muted-foreground">
              <p>
                Edit{" "}
                <code className="rounded bg-muted px-1 py-0.5">.env</code> in the project
                root, then restart the backend:
              </p>
              <pre className="mt-2 overflow-x-auto rounded-lg bg-muted p-3 text-[11px] leading-5 text-foreground/80">
                {`SCOTCH_ANTHROPIC_API_KEY=sk-ant-...\nSCOTCH_GENERATION_MODE=ai   # or hybrid`}
              </pre>
              <p className="mt-2">
                Keys are read server-side only — they are never sent to the browser.
              </p>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
