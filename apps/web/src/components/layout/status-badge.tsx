import { cn } from "@/lib/utils";

const STATUS_VARIANTS = {
  ok: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  error: "bg-red-50 text-red-700 border-red-200",
  info: "bg-muted text-muted-foreground border-border",
} as const;

export type StatusVariant = keyof typeof STATUS_VARIANTS;

export function StatusBadge({
  variant = "info",
  className,
  children,
}: {
  variant?: StatusVariant;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium",
        STATUS_VARIANTS[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
