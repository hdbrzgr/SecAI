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
  Icon,
  ProgressBar,
  ScoreGrade,
  SeverityBadge,
  SeveritySummary,
  StatusPill,
  Tabs,
} from "@secai/ui";
import {
  api,
  ApiError,
  formatDate,
  type Finding,
  type FindingAi,
  type Scan,
  type ToolRun,
} from "@/lib/api";

const TOOL_LABEL: Record<string, string> = {
  headers: "Security headers and cookies",
  tls: "TLS certificate and protocols",
  exposure: "Exposed files",
  nuclei: "Nuclei templates",
  zap: "OWASP ZAP",
  ai: "AI analysis (Claude)",
};

const SEVERITY_LABEL: Record<string, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

function VerdictBadge({ ai }: { ai: FindingAi | null }) {
  if (!ai || ai.verdict === "likely_real") return null;
  return ai.verdict === "needs_review" ? (
    <Badge tone="warning">Needs review</Badge>
  ) : (
    <Badge>Likely false positive</Badge>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-1.5">
      <h3 className="eyebrow m-0">{title}</h3>
      {children}
    </section>
  );
}

function FindingDetail({ f }: { f: Finding }) {
  const ai = f.ai;
  return (
    <div className="flex flex-col gap-5 border-b border-line bg-[var(--surface)] px-5 py-5 sm:pl-[148px]">
      {ai ? (
        <>
          <p className="m-0 flex flex-wrap items-center gap-2 text-[13px] text-ink-muted">
            <Icon name="shield-check" size={14} />
            AI assessment: <strong className="text-ink">{SEVERITY_LABEL[ai.severity]}</strong>
            {ai.severity !== f.severity && <span>(scanner said {SEVERITY_LABEL[f.severity]})</span>}
            <span>·</span>
            {ai.verdict === "likely_real" ? "Likely real" : ai.verdict === "needs_review" ? "Needs review" : "Likely false positive"}
          </p>
          <Section title="What it means">
            <p className="prose-text m-0 !text-[var(--ink)]">{ai.explanation}</p>
            <p className="prose-text m-0">{ai.impact}</p>
          </Section>
          {ai.fix_steps.length > 0 && (
            <Section title="How to fix it">
              <ol className="prose-text m-0 flex list-decimal flex-col gap-1 pl-5 !text-[var(--ink)]">
                {ai.fix_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </Section>
          )}
          {ai.code_example && (
            <CodeBlock title={ai.code_example.language} lines={ai.code_example.code.trimEnd().split("\n")} />
          )}
        </>
      ) : (
        <>
          {f.description && (
            <Section title="What it means">
              <p className="prose-text m-0 !text-[var(--ink)]">{f.description}</p>
            </Section>
          )}
          {f.recommendation && (
            <Section title="How to fix it">
              <p className="prose-text m-0 !text-[var(--ink)]">{f.recommendation}</p>
            </Section>
          )}
        </>
      )}
      {f.evidence && (
        <Section title="Evidence">
          <CodeBlock title={f.location.url} lines={f.evidence.trimEnd().split("\n")} />
        </Section>
      )}
      {ai && f.recommendation && (
        <Section title="Scanner's recommendation">
          <p className="prose-text m-0">{f.recommendation}</p>
        </Section>
      )}
      <div className="flex flex-wrap items-center gap-2 text-[13px] text-ink-muted">
        <span className="font-mono">{f.rule_id}</span>
        {f.references.map((r) => (
          <a key={r} href={r} target="_blank" rel="noopener noreferrer" className="text-link break-all">
            {new URL(r).hostname}
          </a>
        ))}
      </div>
    </div>
  );
}

function AiSummary({ scan, onOpen }: { scan: Scan; onOpen: (id: string) => void }) {
  const ai = scan.summary.ai;
  if (!ai) return null;
  if (ai.status === "skipped") {
    if (scan.findings.length === 0) return null;
    return (
      <Alert tone="info" title="AI analysis is off on this instance">
        Add an Anthropic API key (SECAI_ANTHROPIC_API_KEY) to get plain-language explanations and
        fixes written for your stack.
      </Alert>
    );
  }
  if (ai.status !== "ok") {
    return (
      <Alert tone="warning" title="AI analysis didn't finish">
        {ai.reason ?? "Something went wrong."} The scanner results below are complete.
      </Alert>
    );
  }
  const byFp = new Map(scan.findings.map((f) => [f.fingerprint, f]));
  const priorities = ai.top_priorities.map((fp) => byFp.get(fp)).filter((f): f is Finding => Boolean(f));
  return (
    <Card title="AI summary">
      <div className="flex flex-col gap-5">
        <p className="prose-text m-0 text-[16px] leading-[26px] !text-[var(--ink)]">{ai.executive_summary}</p>
        {priorities.length > 0 && (
          <Section title="Fix first">
            <ol className="m-0 flex list-none flex-col gap-2 p-0">
              {priorities.map((f, i) => (
                <li key={f.id} className="flex items-center gap-3">
                  <span className="w-5 font-mono text-[13px] text-ink-muted">{i + 1}</span>
                  <SeverityBadge severity={f.severity} pips={false} />
                  <button type="button" onClick={() => onOpen(f.id)} className="text-link cursor-pointer border-0 bg-transparent p-0 text-left text-[15px]">
                    {f.title}
                  </button>
                </li>
              ))}
            </ol>
          </Section>
        )}
        <p className="m-0 text-[13px] text-ink-muted">
          Written by Claude ({ai.model}) from redacted scanner output. Check the evidence before you act on it.
        </p>
      </div>
    </Card>
  );
}

function ToolRow({ t }: { t: ToolRun }) {
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line px-5 py-3 last:border-b-0">
      <span className="flex-1 font-medium">{TOOL_LABEL[t.name] ?? t.name}</span>
      {t.status === "ok" ? (
        <Badge tone="signal" icon="check">
          {t.findings === undefined ? "Done" : `${t.findings} finding${t.findings === 1 ? "" : "s"}`}
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

          <AiSummary
            scan={scan}
            onOpen={(fid) => {
              setTab("findings");
              setOpen(fid);
              setTimeout(() => document.getElementById(`finding-${fid}`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
            }}
          />

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
                      <span id={`finding-${f.id}`} />
                      <FindingRow
                        severity={f.severity}
                        title={f.title}
                        location={f.location.param ? `${f.location.url} · ${f.location.param}` : (f.location.url ?? "")}
                        tool={f.tool}
                        cwe={f.cwe ?? undefined}
                        expanded={open === f.id}
                        badge={<VerdictBadge ai={f.ai} />}
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
