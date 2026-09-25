"use client";

import { useEffect, useState } from "react";
import { Alert, Card, EmptyState } from "@secai/ui";
import { ButtonLink } from "@/components/ButtonLink";
import { WebsiteList } from "@/components/WebsiteList";
import { api, type Target } from "@/lib/api";
import { useUser } from "@/lib/user";

export default function DashboardPage() {
  const { user } = useUser();
  const [targets, setTargets] = useState<Target[] | null>(null);

  useEffect(() => {
    api<Target[]>("/targets").then(setTargets, () => setTargets([]));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="page-title">{user.name ? `Welcome, ${user.name}` : "Dashboard"}</h1>
        <p className="m-0 font-mono text-[13px] text-ink-muted">{user.email}</p>
      </div>

      {!user.mfa_enabled && (
        <Alert
          tone="warning"
          title="Two-factor authentication is off"
          action={
            <ButtonLink href="/settings/security" size="sm">
              Turn it on
            </ButtonLink>
          }
        >
          Anyone with your password can sign in. Add an authenticator app to protect your
          account and the scan results it holds.
        </Alert>
      )}

      <Card
        title="Websites"
        flush
        actions={
          targets && targets.length > 0 ? (
            <ButtonLink href="/websites/new" size="sm">
              Add website
            </ButtonLink>
          ) : undefined
        }
      >
        {targets === null ? (
          <p className="m-0 px-5 py-4 text-ink-muted">Loading…</p>
        ) : targets.length === 0 ? (
          <EmptyState
            icon="globe"
            title="No websites yet"
            action={
              <ButtonLink href="/websites/new" variant="primary">
                Add website
              </ButtonLink>
            }
          >
            Add a website you own, prove it&apos;s yours, and run your first scan.
          </EmptyState>
        ) : (
          <WebsiteList targets={targets} />
        )}
      </Card>
    </div>
  );
}
