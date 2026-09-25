"use client";

import Link from "next/link";
import { Badge, Icon, StatusPill } from "@secai/ui";
import type { Target } from "@/lib/api";

function GradeChip({ target }: { target: Target }) {
  const scan = target.last_scan;
  if (!scan) return <span className="text-[13px] text-ink-muted">Not scanned yet</span>;
  if (scan.status !== "succeeded") return <StatusPill status={scan.status} />;
  return (
    <span className="font-display text-[20px] leading-6 font-bold" aria-label={`Grade ${scan.summary.grade}`}>
      {scan.summary.grade}
      <span className="ml-1 font-sans text-[13px] font-normal text-ink-muted">{scan.summary.score}/100</span>
    </span>
  );
}

/** One row per website: domain, verification state and the latest result. */
export function WebsiteList({ targets }: { targets: Target[] }) {
  return (
    <ul className="m-0 list-none p-0">
      {targets.map((t) => (
        <li key={t.id} className="border-b border-line last:border-b-0">
          <Link
            href={`/websites/${t.id}`}
            className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-4 text-ink no-underline hover:bg-[var(--surface-hover)]"
          >
            <span className="flex min-w-0 flex-1 items-center gap-2 font-mono text-[15px] font-medium">
              <Icon name="globe" />
              <span className="truncate">{t.hostname}</span>
            </span>
            {t.verified_at && !t.verification_expired ? (
              <Badge tone="signal" icon="shield-check">
                Verified
              </Badge>
            ) : t.verification_expired ? (
              <Badge tone="warning" icon="triangle-alert">
                Verify again
              </Badge>
            ) : (
              <Badge icon="clock">Not verified</Badge>
            )}
            <span className="w-32 text-right">
              <GradeChip target={t} />
            </span>
            <Icon name="chevron-right" className="text-ink-muted" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
