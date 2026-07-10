"use client";

import * as React from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/marketing/auth/auth-context";
import { SignInDialog } from "@/components/marketing/auth/sign-in-dialog";
import { ThemeToggle } from "@/components/marketing/theme-toggle";
import { UserMenu } from "@/components/marketing/auth/user-menu";

const NAV_LINKS = [
  { href: "#product", label: "Product" },
  { href: "#integrations", label: "Integrations" },
  { href: "#showcase", label: "Showcase" },
  { href: "#about", label: "About" },
  { href: "#faq", label: "FAQ" },
] as const;

export function MarketingNav() {
  const { user } = useAuth();
  const [scrolled, setScrolled] = React.useState(false);

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 transition-all duration-300",
        scrolled
          ? "border-b border-border bg-background/90 backdrop-blur-md"
          : "border-b border-transparent",
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-8 px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="brand-logo flex size-7 items-center justify-center rounded-md text-[13px] font-semibold tracking-tight">
            S
          </span>
          <span className="text-[15px] font-semibold tracking-tight">Scotch</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          {user ? (
            <UserMenu user={user} />
          ) : (
            <SignInDialog
              trigger={
                <Button variant="ghost" size="sm" className="hidden sm:inline-flex">
                  Sign in
                </Button>
              }
            />
          )}
          <Button asChild size="sm" className="brand-btn">
            <Link href="/workspace">Open Workspace</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
