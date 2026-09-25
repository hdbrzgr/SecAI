"use client";

import { usePathname, useRouter } from "next/navigation";
import { AppHeader, Button } from "@secai/ui";
import { api } from "@/lib/api";
import { UserProvider } from "@/lib/user";

const NAV = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Websites", href: "/websites" },
  { label: "Settings", href: "/settings/security" },
];

export default function AppLayout({ children }: LayoutProps<"/">) {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.push("/login");
  }

  return (
    <>
      <AppHeader
        nav={NAV.map((item) => ({
          ...item,
          active:
            pathname.startsWith(item.href) || (item.href === "/websites" && pathname.startsWith("/scans")),
        }))}
        actions={
          <Button variant="ghost" size="sm" icon="log-out" onClick={signOut}>
            Sign out
          </Button>
        }
      />
      <main className="mx-auto w-full max-w-[1120px] flex-1 px-4 py-8 sm:px-6 sm:py-12">
        <UserProvider fallback={<p className="text-ink-muted">Loading…</p>}>{children}</UserProvider>
      </main>
    </>
  );
}
