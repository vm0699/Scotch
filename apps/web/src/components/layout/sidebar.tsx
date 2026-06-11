import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface SidebarItem {
  label: string;
  href: string;
  icon: LucideIcon;
  active?: boolean;
  disabled?: boolean;
  hint?: string;
}

export function Sidebar({
  items,
  footer,
}: {
  items: SidebarItem[];
  footer?: React.ReactNode;
}) {
  return (
    <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-background lg:flex">
      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {items.map((item) =>
          item.disabled ? (
            <span
              key={item.label}
              title={item.hint}
              className="flex cursor-default items-center gap-2.5 rounded-md px-3 py-2 text-sm text-muted-foreground/50"
            >
              <item.icon className="size-4" />
              {item.label}
            </span>
          ) : (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                item.active
                  ? "bg-muted font-medium text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <item.icon className="size-4" />
              {item.label}
            </Link>
          ),
        )}
      </nav>
      {footer && (
        <div className="border-t border-border p-3 text-xs text-muted-foreground">
          {footer}
        </div>
      )}
    </aside>
  );
}
