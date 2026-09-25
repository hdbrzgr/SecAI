"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Fragment, useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Card,
  CodeBlock,
  EmptyState,
  FindingRow,
  ProgressBar,
  ScoreGrade,
  SeveritySummary,
  StatusPill,
  Tabs,
} from "@secai/ui";
import { api, ApiError, formatDate, type Finding, type Scan, type ToolRun } from "@/lib/api";

const TOOL_LABEL: Record<string, string> = {
  headers: "Security headers and cookies",
  tls: "TLS certificate and protocols",
  exposure: "Exposed files",
  nuclei: "Nuclei templates",
  zap: "OWASP ZAP",
};

function FindingDetail({ f }: { f: Finding }) {
  return (
    <div className="flex flex-col gap-4 border-b border-line bg-[var(--surface)] px-5 py-5 sm:pl-[148px]">
      {f.description && (
        <section className="flex flex-col gap-1">
          <h3 className="eyebrow m-0">What it means</h3>
          <p className="prose-text m-0 !text-[var(--ink)]">{f.description}</p>
        </section>
      )}
      {f.recommendation && (
        <section className="flex flex-col gap-1">
          <h3 className="eyebrow m-0">How to fix it</h3>
          <p className="prose-text m-0 !text-[var(--ink)]">{f.recommendation}</p>
        </section>
      )}
      {f.evidence && (
        <section className="flex flex-col gap-2">
          <h3 className="eyebrow m-0">Evidence</h3>
          <CodeBlock title={f.location.url} lines={f.evidence.trimEnd().split("\n")} />
        </section>
      )}
      <div className="flex flex-wrap items-center gap-2 text-[13px] text-ink-muted">
        <span className="font-mono">{f.rule_id}</span>
        {f.references.map((r) => (
          <a key={r} href={r} target="_blank" rel="noopener noreferrer" className="text-link break-all">
            {new URL(r).hostname}
          </a>
        ))}
      </div>
      <p className="m-0 text-[13px] text-ink-muted">
        AI explanations tailored to your stack arrive in the next release.
      </p>
    </div>
  );
}

function ToolRow({ t }: { t: ToolRun }) {
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line px-5 py-3 last:border-b-0">
      <span className="flex-1 font-medium">{TOOL_LABEL[t.name] ?? t.name}</span>
      {t.status === "ok" ? (
        <Badge tone="signal" icon="check">
          {t.findings} finding{t.findings === 1 ? "" : "s"}
        </Badge>
      ) : t.status === "skipped" ? (
        <Badge>Skipped</Badge>
      ) : (
        <Badge tone="danger" icon="circle-x">
          {t.status === "blocked" ? "Blocked" : "Failed"}
        </Badge>
      )}
      <span className="w-16 text-right font-mono text-[13px] text-ink-muted">{t.seconds}s</span>
      {t.reason && <span className="basis-full text-[13px] text-ink-muted">{t.reason}</span>}
    </li>
  );
}

export default function ScanPage() {
  const { id } = useParams<{ id: string }>();
  const [scan, setScan] = useState<Scan | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [tab, setTab] = useState("findings");
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false;
    const poll = async () => {
      try {
        const s = await api<Scan>(`/scans/${id}`);
        if (stopped) return;
        setScan(s);
        if (s.status === "queued" || s.status === "running") timer = setTimeout(poll, 2000);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) setNotFound(true);
        else timer = setTimeout(poll, 5000);
      }
    };
    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id]);

  if (notFound) {
    return (
      <Card>
        <EmptyState title="Scan not found">It may have been deleted with its website.</EmptyState>
      </Card>
    );
  }
  if (!scan) return <p className="text-ink-muted">Loading…</p>;

  const host = scan.target_url ? new URL(scan.target_url).host : "Scan";
  const running = scan.status === "queued" || scan.status === "running";
  const tools = scan.summary.tools ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        {scan.target_id && (
          <Link href={`/websites/${scan.target_id}`} className="text-link text-[14px]">
            ← {host}
          </Link>
        )}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <h1 className="page-title">Scan report</h1>
          <StatusPill status={scan.status} />
        </div>
        <p className="m-0 text-[14px] text-ink-muted">
          <span className="font-mono">{scan.target_url}</span> · {formatDate(scan.created_at)}
          {scan.summary.seconds !== undefined &&
            ` · took ${scan.summary.seconds < 1 ? "under 1 s" : `${Math.round(scan.summary.seconds)} s`}`}
        </p>
      </div>

      {running && (
        <Card>
          <ProgressBar
            value={scan.progress}
            label={scan.status === "queued" ? "Waiting to start" : `Scanning ${host}`}
            detail={scan.current_step ?? undefined}
          />
        </Card>
      )}

      {scan.status === "failed" && (
        <Alert tone="danger" title="The scan couldn't finish">
          {scan.error ?? "Every scanner failed to reach the website."} Check that the site is online
          and try again.
        </Alert>
      )}

      {scan.status === "succeeded" && scan.summary.grade && (
        <>
          <Card>
            <div className="grid items-center gap-8 md:grid-cols-[auto_1fr]">
              <ScoreGrade
                grade={scan.summary.grade}
                score={scan.summary.score ?? 0}
                caption={`${scan.findings.length} finding${scan.findings.length === 1 ? "" : "s"}`}
              />
              <SeveritySummary counts={scan.summary.counts ?? {}} />
            </div>
          </Card>

          <Tabs
            label="Report sections"
            value={tab}
            onChange={setTab}
            tabs={[
              { id: "findings", label: "Findings", count: scan.findings.length },
              { id: "details", label: "Scan details" },
            ]}
          />

          {tab === "findings" && (
            <Card flush>
              {scan.findings.length === 0 ? (
                <EmptyState icon="shield-check" title="No issues found">
                  None of the checks found a problem on {host}.
                </EmptyState>
              ) : (
                <div>
                  {scan.findings.map((f) => (
                    <Fragment key={f.id}>
                      <FindingRow
                        severity={f.severity}
                        title={f.title}
                        location={f.location.param ? `${f.location.url} · ${f.location.param}` : (f.location.url ?? "")}
                        tool={f.tool}
                        cwe={f.cwe ?? undefined}
                        expanded={open === f.id}
                        onClick={() => setOpen(open === f.id ? null : f.id)}
                      />
                      {open === f.id && <FindingDetail f={f} />}
                    </Fragment>
                  ))}
                </div>
              )}
            </Card>
          )}

          {tab === "details" && (
            <Card title="Scanners" flush>
              <ul className="m-0 list-none p-0">
                {tools.map((t) => (
                  <ToolRow key={t.name} t={t} />
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
