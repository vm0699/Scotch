import { TopBar } from "@/components/layout/top-bar";

/**
 * Top-level chrome for all authenticated screens: TopBar, optional sidebar,
 * and a scrollable content region. Pages own their inner layout.
 */
export function AppShell({
  active,
  sidebar,
  children,
}: {
  active?: "/dashboard" | "/workspace";
  sidebar?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen flex-col bg-muted/40">
      <TopBar active={active} />
      <div className="flex min-h-0 flex-1">
        {sidebar}
        <main className="min-w-0 flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
