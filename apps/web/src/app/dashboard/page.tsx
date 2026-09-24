"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import { useUser } from "@/lib/useUser";

export default function DashboardPage() {
  const router = useRouter();
  const [user] = useUser();

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    router.push("/login");
  }

  if (!user) return <p className="text-muted">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Welcome{user.name ? `, ${user.name}` : ""}</h1>
          <p className="text-sm text-muted">{user.email}</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/settings/security"
            className="inline-flex h-10 items-center rounded-md border border-border px-4 text-sm font-medium"
          >
            Security settings
          </Link>
          <Button onClick={logout}>Sign out</Button>
        </div>
      </div>

      {!user.mfa_enabled && (
        <Card className="border-accent/40">
          <p className="text-sm">
            Protect your account: turn on{" "}
            <Link href="/settings/security" className="font-medium underline">
              two-factor authentication
            </Link>
            .
          </p>
        </Card>
      )}

      <Card>
        <h2 className="font-semibold">Your websites</h2>
        <p className="mt-2 text-sm text-muted">
          No websites yet. Adding a website, verifying ownership and running scans arrives in the
          next release.
        </p>
      </Card>
    </div>
  );
}
