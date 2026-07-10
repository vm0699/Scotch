import Link from "next/link";

const COLUMNS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Overview",   href: "#product"    },
      { label: "Showcase",   href: "#showcase"   },
      { label: "Workspace",  href: "/workspace"  },
      { label: "Dashboard",  href: "/dashboard"  },
    ],
  },
  {
    title: "Integrations",
    links: [
      { label: "SketchUp",            href: "#integrations" },
      { label: "Revit",               href: "#integrations" },
      { label: "Rhino + Grasshopper", href: "#integrations" },
      { label: "Blender",             href: "#integrations" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "About",      href: "#about"   },
      { label: "FAQ",        href: "#faq"     },
      { label: "Why Scotch", href: "#product" },
    ],
  },
];

export function MarketingFooter() {
  return (
    <footer className="border-t border-border px-6 py-14">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 sm:grid-cols-2 md:grid-cols-4">
          <div>
            <Link href="/" className="flex items-center gap-2.5">
              <span className="brand-logo flex size-7 items-center justify-center rounded-md text-[13px] font-semibold tracking-tight">
                S
              </span>
              <span className="text-[15px] font-semibold tracking-tight">Scotch</span>
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-6 text-muted-foreground">
              Text-to-design for architecture. Local-first, editable, and built
              for the tools you already run.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {col.title}
              </h3>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row">
          <span>
            © {new Date().getFullYear()}{" "}
            <span className="brand-text font-medium">Scotch</span>
            {" "}· Text-to-design for architecture
          </span>
          <span>Local-first · Deterministic generation works without an AI key</span>
        </div>
      </div>
    </footer>
  );
}
