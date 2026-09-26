"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  DomainVerification,
  EmptyState,
  Icon,
  StatusPill,
  Tabs,
} from "@secai/ui";
import { api, ApiError, formatDate, type Scan, type ScanBrief, type Target, type VerificationMethod } from "@/lib/api";

const METHODS: Array<{ id: VerificationMethod; label: string }> = [
  { id: "dns_txt", label: "DNS record" },
  { id: "well_known_file", label: "File" },
  { id: "meta_tag", label: "Meta tag" },
];

export default function WebsitePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [target, setTarget] = useState<Target | null>(null);
  const [scans, setScans] = useState<ScanBrief[]>([]);
  const [notFound, setNotFound] = useState(false);
  const [method, setMethod] = useState<VerificationMethod>("dns_txt");
  const [checking, setChecking] = useState(false);
  const [verifyFailed, setVerifyFailed] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [starting, setStarting] = useState(false);
  const [scanError, setScanError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    Promise.all([api<Target>(`/targets/${id}`), api<ScanBrief[]>(`/targets/${id}/scans`)]).then(
      ([t, s]) => {
        setTarget(t);
        setScans(s);
      },
      (err) => {
        if (err instanceof ApiError && err.status === 404) setNotFound(true);
      },
    );
  }, [id]);

  async function verify() {
    setChecking(true);
    setVerifyFailed("");
    try {
      setTarget(await api<Target>(`/targets/${id}/verify`, { body: { method } }));
    } catch (err) {
      setVerifyFailed(err instanceof ApiError ? err.message : "The check didn't finish. Try again.");
    } finally {
      setChecking(false);
    }
  }

  async function startScan() {
    setStarting(true);
    setScanError("");
    try {
      const scan = await api<Scan>(`/targets/${id}/scans`, { body: { authorized } });
      router.push(`/scans/${scan.id}`);
    } catch (err) {
      setScanError(err instanceof ApiError ? err.message : "The scan didn't start. Try again.");
      setStarting(false);
    }
  }

  async function remove() {
    await api(`/targets/${id}`, { method: "DELETE" });
    router.push("/websites");
  }

  if (notFound) {
    return (
      <Card>
        <EmptyState icon="globe" title="Website not found">
          It may have been removed, or it belongs to another workspace.
        </EmptyState>
      </Card>
    );
  }
  if (!target) return <p className="text-ink-muted">Loading…</p>;

  const verified = Boolean(target.verified_at) && !target.verification_expired;
  const active = scans.find((s) => s.status === "queued" || s.status === "running");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <Link href="/websites" className="text-link text-[14px]">
          ← Websites
        </Link>
        <h1 className="page-title font-mono !text-[28px] break-all">{target.hostname}</h1>
        <p className="m-0 font-mono text-[13px] text-ink-muted">{target.url}</p>
      </div>

      {!verified ? (
        <Card title={target.verification_expired ? "Verify ownership again" : "Prove you own this website"}>
          <div className="flex flex-col gap-5">
            <p className="prose-text m-0">
              SecAI only scans websites you control. Pick one way to prove it, add the value below,
              then check.
            </p>
            <Tabs
              label="Verification method"
              tabs={METHODS}
              value={method}
              onChange={(m) => {
                setMethod(m as VerificationMethod);
                setVerifyFailed("");
              }}
            />
            <DomainVerification
              domain={target.hostname}
              method={method}
              token={target.verification_token}
              status={checking ? "checking" : verifyFailed ? "failed" : "pending"}
              onVerify={verify}
            />
            {verifyFailed && <Alert tone="danger" title={verifyFailed} />}
          </div>
        </Card>
      ) : (
        <Card title="Run a scan">
          <div className="flex flex-col gap-5">
            <p className="prose-text m-0">
              Checks security headers, cookies, TLS, exposed files and known vulnerabilities at a
              safe request rate. A scan usually takes a few minutes.
            </p>
            {active ? (
              <Alert
                tone="info"
                title="A scan is in progress"
                action={
                  <Button size="sm" onClick={() => router.push(`/scans/${active.id}`)}>
                    View progress
                  </Button>
                }
              />
            ) : (
              <>
                <Checkbox
                  label="I own this website or have written permission to test it"
                  description="SecAI records this confirmation, with the time and your IP address, for every scan."
                  checked={authorized}
                  onChange={(e) => setAuthorized(e.currentTarget.checked)}
                />
                {scanError && <Alert tone="danger" title={scanError} />}
                <div>
                  <Button variant="primary" icon="scan-search" disabled={!authorized} loading={starting} onClick={startScan}>
                    Run scan
                  </Button>
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      <Card title="Scan history" flush>
        {scans.length === 0 ? (
          <p className="m-0 px-5 py-4 text-ink-muted">No scans yet.</p>
        ) : (
          <ul className="m-0 list-none p-0">
            {scans.map((s) => (
              <li key={s.id} className="border-b border-line last:border-b-0">
                <Link
                  href={`/scans/${s.id}`}
                  className="flex flex-wrap items-center gap-x-5 gap-y-1 px-5 py-3 text-ink no-underline hover:bg-[var(--surface-hover)]"
                >
                  <span className="min-w-[180px] flex-1 text-[14px]">{formatDate(s.created_at)}</span>
                  <StatusPill status={s.status} />
                  <span className="w-24 text-right font-display text-[18px] font-bold">
                    {s.status === "succeeded" ? s.summary.grade : ""}
                    {s.status === "succeeded" && (
                      <span className="ml-1 font-sans text-[13px] font-normal text-ink-muted">{s.summary.score}/100</span>
                    )}
                  </span>
                  <Icon name="chevron-right" className="text-ink-muted" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Remove website">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="prose-text m-0">Deletes the website and all of its scan results.</p>
          {confirmDelete ? (
            <div className="flex gap-2">
              <Button variant="danger" onClick={remove}>
                Delete {target.hostname}
              </Button>
              <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
                Keep it
              </Button>
            </div>
          ) : (
            <Button onClick={() => setConfirmDelete(true)}>Remove website</Button>
          )}
        </div>
      </Card>
    </div>
  );
}
