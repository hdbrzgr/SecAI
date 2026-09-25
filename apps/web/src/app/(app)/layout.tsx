"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Alert, AppHeader, Button } from "@secai/ui";
import { api } from "@/lib/api";
import { UserProvider, useUser } from "@/lib/user";

const NAV = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Websites", href: "/websites" },
  { label: "Settings", href: "/settings/security" },
];

function EmailBanner() {
  const { user } = useUser();
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  if (!user.email_verification_required) return null;
  const resend = async () => {
    setState("sending");
    try {
      await api("/auth/email/verify/request", { method: "POST" });
      setState("sent");
    } catch {
      setState("error");
    }
  };
  return (
    <div className="mb-6">
      <Alert
        tone="warning"
        title="Confirm your email address"
        action={
          state === "sent" ? undefined : (
            <Button size="sm" onClick={resend} loading={state === "sending"}>
              Send again
            </Button>
          )
        }
      >
        {state === "sent"
          ? `A new link is on its way to ${user.email}.`
          : state === "error"
            ? "The email couldn't be sent. Try again in a few minutes."
            : `Open the link sent to ${user.email} to start adding websites.`}
      </Alert>
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useUser();
  const nav = user.is_superuser ? [...NAV, { label: "Admin", href: "/admin" }] : NAV;

  async function signOut() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.push("/login");
  }

  return (
    <>
      <AppHeader
        nav={nav.map((item) => ({
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
        <EmailBanner />
        {children}
      </main>
    </>
  );
}

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <UserProvider fallback={<p className="px-4 py-12 text-center text-ink-muted">Loading…</p>}>
      <Shell>{children}</Shell>
    </UserProvider>
  );
}
