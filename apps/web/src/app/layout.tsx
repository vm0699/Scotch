import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "sonner";

import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/components/marketing/auth/auth-context";
import { ThemeProvider, themeInitScript } from "@/components/marketing/theme-provider";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://scotch.studio"),
  title: {
    default: "Scotch — Text-to-design for architecture",
    template: "%s · Scotch",
  },
  description:
    "AI-native architecture design platform. Type a brief, get an editable floor plan, 3D massing, and exports for professional tools — AutoCAD, SketchUp, Revit, Rhino and Blender.",
  keywords: [
    "architecture",
    "AI design",
    "floor plan generator",
    "text to design",
    "CAD",
    "Revit",
    "SketchUp",
    "Rhino",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    title: "Scotch — Text-to-design for architecture",
    description:
      "Describe a building in plain language and get an editable floor plan, 3D massing, and exports for the tools architects already use.",
    siteName: "Scotch",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "Scotch — Text-to-design for architecture",
    description:
      "Describe a building in plain language and get an editable floor plan, 3D massing, and professional exports.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Apply the saved/system theme before paint to avoid a flash. */}
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <ThemeProvider>
          <AuthProvider>
            <TooltipProvider>{children}</TooltipProvider>
          </AuthProvider>
        </ThemeProvider>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              fontFamily: "var(--font-sans)",
              fontSize: "13px",
              borderRadius: "10px",
              border: "1px solid hsl(var(--border, 220 13% 91%))",
            },
          }}
        />
      </body>
    </html>
  );
}
