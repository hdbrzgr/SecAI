"use client";

import { Alert, Button, Card, EmptyState } from "@secai/ui";
import { ButtonLink } from "@/components/ButtonLink";
import { useUser } from "@/lib/user";

export default function DashboardPage() {
  const { user } = useUser();

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

      <Card title="Websites" flush>
        <EmptyState
          icon="globe"
          title="No websites yet"
          action={
            <Button variant="primary" icon="plus" disabled title="Available in the next release">
              Add website
            </Button>
          }
        >
          Add a website you own, prove it&apos;s yours, and run your first scan. Adding websites
          arrives in the next release.
        </EmptyState>
      </Card>
    </div>
  );
}
