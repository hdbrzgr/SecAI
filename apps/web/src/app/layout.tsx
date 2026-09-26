// SecAI — Copyright (C) 2026 hdbrzgr. AGPL-3.0 with an attribution term; see NOTICE.
import type { Metadata } from "next";
import { Attribution } from "@secai/ui";
import "@secai/ui/tokens.css";
import "@secai/ui/styles.css";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "SecAI", template: "%s · SecAI" },
  description: "Open-source security scanning for the websites and code you own.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full">
      <body className="sx-root flex min-h-full flex-col">
        <div className="flex flex-1 flex-col">{children}</div>
        {/* Required by the license: keep this footer visible on every page. */}
        <Attribution />
      </body>
    </html>
  );
}
