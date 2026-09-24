import type { Metadata } from "next";
import Link from "next/link";
import { Attribution } from "@/components/Attribution";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecAI",
  description: "Open-source, AI-powered security scanning for your websites and code.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col font-sans">
        <header className="border-b border-border">
          <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              Sec<span className="text-accent">AI</span>
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link href="/dashboard" className="hover:underline">
                Dashboard
              </Link>
              <Link href="/login" className="hover:underline">
                Sign in
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">{children}</main>
        <Attribution />
      </body>
    </html>
  );
}
