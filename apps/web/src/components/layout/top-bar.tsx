import Link from "next/link";

import { BackendStatusIndicator } from "@/components/layout/backend-status";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/workspace", label: "Workspace" },
] as const;

export function TopBar({ active }: { active?: "/dashboard" | "/workspace" }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
      <div className="flex h-14 items-center gap-6 px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-md bg-foreground text-background text-[13px] font-semibold tracking-tight">
            S
          </span>
          <span className="text-[15px] font-semibold tracking-tight">
            Scotch
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm transition-colors",
                active === link.href
                  ? "bg-muted font-medium text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-4">
          <span className="hidden text-xs text-muted-foreground sm:block">
            Local project mode
          </span>
          <BackendStatusIndicator />
        </div>
      </div>
    </header>
  );
}
