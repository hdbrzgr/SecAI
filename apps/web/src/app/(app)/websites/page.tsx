"use client";

import { useEffect, useState } from "react";
import { Card, EmptyState } from "@secai/ui";
import { ButtonLink } from "@/components/ButtonLink";
import { WebsiteList } from "@/components/WebsiteList";
import { api, type Target } from "@/lib/api";

export default function WebsitesPage() {
  const [targets, setTargets] = useState<Target[] | null>(null);

  useEffect(() => {
    api<Target[]>("/targets").then(setTargets, () => setTargets([]));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="page-title">Websites</h1>
        <ButtonLink href="/websites/new" variant="primary">
          Add website
        </ButtonLink>
      </div>
      <Card flush>
        {targets === null ? (
          <p className="m-0 px-5 py-4 text-ink-muted">Loading…</p>
        ) : targets.length === 0 ? (
          <EmptyState icon="globe" title="No websites yet">
            Add a website you own, prove it&apos;s yours, and run your first scan.
          </EmptyState>
        ) : (
          <WebsiteList targets={targets} />
        )}
      </Card>
    </div>
  );
}
