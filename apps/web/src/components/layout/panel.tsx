import { cn } from "@/lib/utils";

/**
 * Panel system for the CADAM-style workspace: a bordered white surface with
 * a slim header, scrollable body, and labeled sections.
 */

export function Panel({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-[0_1px_2px_rgba(0,0,0,0.04)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PanelHeader({
  title,
  actions,
  className,
}: {
  title: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex h-11 shrink-0 items-center justify-between gap-2 border-b border-border px-4",
        className,
      )}
    >
      <div className="text-[13px] font-medium tracking-tight">{title}</div>
      {actions && <div className="flex items-center gap-1.5">{actions}</div>}
    </div>
  );
}

export function PanelBody({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("min-h-0 flex-1 overflow-auto", className)}>
      {children}
    </div>
  );
}

export function PanelSection({
  title,
  actions,
  className,
  children,
}: {
  title?: string;
  actions?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={cn("border-b border-border px-4 py-3 last:border-b-0", className)}>
      {(title || actions) && (
        <div className="mb-2.5 flex items-center justify-between">
          {title && (
            <h3 className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              {title}
            </h3>
          )}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function PanelEmpty({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground",
        className,
      )}
    >
      {children}
    </div>
  );
}
