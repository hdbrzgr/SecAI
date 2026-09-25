"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Checkbox, EmptyState, Tabs, TextField } from "@secai/ui";
import {
  api,
  ApiError,
  formatDate,
  type AdminOverview,
  type AdminUser,
  type AuditEvent,
  type BlockedDomain,
  type InstanceSettings,
} from "@/lib/api";
import { useUser } from "@/lib/user";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "users", label: "Users" },
  { id: "settings", label: "Settings" },
  { id: "blocklist", label: "Blocked domains" },
  { id: "audit", label: "Audit log" },
];

function useLoad<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const reload = useCallback(() => {
    api<T>(path).then(setData, (err) =>
      setError(err instanceof ApiError ? err.message : "Couldn't load this section."),
    );
  }, [path]);
  useEffect(() => {
    reload();
  }, [reload]);
  return { data, setData, error, reload };
}

function Stat({ label, value, detail }: { label: string; value: number | string; detail?: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-line bg-surface p-4">
      <span className="eyebrow">{label}</span>
      <span className="font-display text-[28px] leading-8 font-bold tabular-nums">{value}</span>
      {detail && <span className="text-[13px] text-ink-muted">{detail}</span>}
    </div>
  );
}

function ServiceRow({ name, on, off }: { name: string; on: boolean; off: string }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 border-b border-line py-3 last:border-b-0">
      <span className="font-medium">{name}</span>
      {on ? (
        <Badge tone="signal" icon="circle-check">
          Configured
        </Badge>
      ) : (
        <span className="flex items-center gap-2 text-[13px] text-ink-muted">
          {off} <Badge>Off</Badge>
        </span>
      )}
    </li>
  );
}

function Overview() {
  const { data, error } = useLoad<AdminOverview>("/admin/overview");
  if (error) return <Alert tone="danger" title={error} />;
  if (!data) return <p className="text-ink-muted">Loading…</p>;
  return (
    <div className="flex flex-col gap-6">
      {data.scanning_paused && (
        <Alert tone="warning" title="Scanning is paused">
          No new scans start until you turn scanning back on in Settings.
        </Alert>
      )}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Users" value={data.users} detail={`${data.active_users} active`} />
        <Stat label="Websites" value={data.websites} detail={`${data.verified_websites} verified`} />
        <Stat label="Scans, 24 hours" value={data.scans_last_24h} detail={`${data.scans_total} in total`} />
        <Stat label="Running now" value={data.scans_running} />
      </div>
      <Card title="Services">
        <ul className="m-0 list-none p-0">
          <ServiceRow name="Email (SMTP)" on={data.smtp_configured} off="Set SECAI_SMTP_HOST to send verification and reset emails" />
          <ServiceRow name="OWASP ZAP" on={data.zap_configured} off="Runs with docker compose; needs SECAI_ZAP_API_KEY" />
          <ServiceRow name="AI analysis (Claude)" on={data.ai_configured} off="Set SECAI_ANTHROPIC_API_KEY" />
        </ul>
        {data.ai_configured && (
          <p className="mt-3 mb-0 text-[13px] text-ink-muted">
            AI analysis used {data.ai_tokens_last_30d.toLocaleString()} tokens in the last 30 days.
          </p>
        )}
      </Card>
    </div>
  );
}

function Users() {
  const { user: me } = useUser();
  const [q, setQ] = useState("");
  const { data, setData, error } = useLoad<AdminUser[]>(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  const [actionError, setActionError] = useState("");

  async function update(u: AdminUser, patch: Partial<Pick<AdminUser, "is_active" | "is_superuser">>) {
    setActionError("");
    try {
      const updated = await api<AdminUser>(`/admin/users/${u.id}`, { method: "PATCH", body: patch });
      setData((list) => (list ?? []).map((x) => (x.id === u.id ? updated : x)));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "The change wasn't saved.");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="max-w-[360px]">
        <TextField label="Search by email" name="q" value={q} onChange={(e) => setQ(e.currentTarget.value)} />
      </div>
      {actionError && <Alert tone="danger" title={actionError} />}
      {error && <Alert tone="danger" title={error} />}
      <Card flush>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-[14px]">
            <thead>
              <tr className="bg-surface-sunken">
                {["User", "Status", "Websites", "Scans", "Joined", ""].map((h) => (
                  <th key={h} className="eyebrow px-4 py-2 font-medium whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((u) => (
                <tr key={u.id} className="border-t border-line align-top">
                  <td className="px-4 py-3">
                    <div className="font-medium break-all">{u.email}</div>
                    {u.name && <div className="text-[13px] text-ink-muted">{u.name}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {!u.is_active && <Badge tone="danger">Deactivated</Badge>}
                      {u.is_superuser && <Badge tone="signal">Admin</Badge>}
                      {u.mfa_enabled && <Badge icon="lock">2FA</Badge>}
                      {!u.email_verified && <Badge tone="warning">Email not confirmed</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3 tabular-nums">{u.websites}</td>
                  <td className="px-4 py-3 tabular-nums">{u.scans}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-ink-muted">{formatDate(u.created_at)}</td>
                  <td className="px-4 py-3">
                    {u.id !== me.id && (
                      <div className="flex flex-wrap justify-end gap-2">
                        <Button size="sm" onClick={() => update(u, { is_superuser: !u.is_superuser })}>
                          {u.is_superuser ? "Remove admin" : "Make admin"}
                        </Button>
                        <Button
                          size="sm"
                          variant={u.is_active ? "danger" : "secondary"}
                          onClick={() => update(u, { is_active: !u.is_active })}
                        >
                          {u.is_active ? "Deactivate" : "Reactivate"}
                        </Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function Settings() {
  const { data, setData, error } = useLoad<InstanceSettings>("/admin/settings");
  const [notice, setNotice] = useState("");
  const [saveError, setSaveError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(patch: Partial<InstanceSettings>, message: string) {
    setBusy(true);
    setNotice("");
    setSaveError("");
    try {
      setData(await api<InstanceSettings>("/admin/settings", { method: "PATCH", body: patch }));
      setNotice(message);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "The settings weren't saved.");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <Alert tone="danger" title={error} />;
  if (!data) return <p className="text-ink-muted">Loading…</p>;

  const onLimits = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    save(
      {
        registration_open: f.get("registration_open") === "on",
        scans_per_day_per_org: Number(f.get("scans_per_day_per_org")),
        max_targets_per_org: Number(f.get("max_targets_per_org")),
      },
      "Settings saved.",
    );
  };

  return (
    <div className="flex max-w-[680px] flex-col gap-6">
      {notice && <Alert tone="success" title={notice} />}
      {saveError && <Alert tone="danger" title={saveError} />}
      <Card title="Scanning">
        {data.scanning_paused ? (
          <div className="flex flex-col gap-4">
            <Alert tone="warning" title="Scanning is paused">
              {data.scanning_paused_reason ?? "No reason given."} Queued scans fail instead of running.
            </Alert>
            <div>
              <Button variant="primary" onClick={() => save({ scanning_paused: false }, "Scanning is back on.")} loading={busy}>
                Resume scanning
              </Button>
            </div>
          </div>
        ) : (
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              const reason = String(new FormData(e.currentTarget).get("reason") || "") || null;
              save({ scanning_paused: true, scanning_paused_reason: reason }, "Scanning is paused.");
            }}
          >
            <p className="prose-text m-0">
              Stop all new scans on this instance, for example during maintenance or after an abuse
              report. Scans already running finish.
            </p>
            <TextField label="Reason shown to users (optional)" name="reason" maxLength={300} />
            <div>
              <Button type="submit" variant="danger" loading={busy}>
                Pause scanning
              </Button>
            </div>
          </form>
        )}
      </Card>
      <Card title="Accounts and limits">
        <form onSubmit={onLimits} className="flex flex-col gap-4" key={data.updated_at}>
          <Checkbox
            name="registration_open"
            label="Anyone can create an account"
            description="Turn this off once you've created the accounts you need."
            defaultChecked={data.registration_open}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="Scans per workspace per day"
              name="scans_per_day_per_org"
              type="number"
              min={0}
              max={10000}
              defaultValue={data.scans_per_day_per_org}
              required
            />
            <TextField
              label="Websites per workspace"
              name="max_targets_per_org"
              type="number"
              min={0}
              max={10000}
              defaultValue={data.max_targets_per_org}
              required
            />
          </div>
          <div>
            <Button type="submit" variant="primary" loading={busy}>
              Save settings
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function Blocklist() {
  const { data, error, reload } = useLoad<BlockedDomain[]>("/admin/blocked-domains");
  const [formError, setFormError] = useState("");

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const el = e.currentTarget;
    const f = new FormData(el);
    setFormError("");
    try {
      await api("/admin/blocked-domains", { body: { domain: f.get("domain"), reason: f.get("reason") || null } });
      el.reset();
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "The domain wasn't added.");
    }
  }

  async function remove(id: string) {
    await api(`/admin/blocked-domains/${id}`, { method: "DELETE" });
    reload();
  }

  return (
    <div className="flex flex-col gap-6">
      <Card title="Block a domain">
        <form onSubmit={add} className="flex flex-col gap-4">
          <p className="prose-text m-0">
            Nobody on this instance can add, verify or scan a blocked domain or any of its
            subdomains. Use it for abuse reports and for sites you must never touch.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Domain" name="domain" mono placeholder="example.com" required />
            <TextField label="Reason (optional)" name="reason" maxLength={300} />
          </div>
          {formError && <Alert tone="danger" title={formError} />}
          <div>
            <Button type="submit" variant="primary" icon="plus">
              Block domain
            </Button>
          </div>
        </form>
      </Card>
      <Card title="Blocked domains" flush>
        {error && <Alert tone="danger" title={error} />}
        {data && data.length === 0 ? (
          <EmptyState icon="shield-check" title="No blocked domains" />
        ) : (
          <ul className="m-0 list-none p-0">
            {(data ?? []).map((d) => (
              <li key={d.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line px-5 py-3 last:border-b-0">
                <span className="flex-1 font-mono font-medium">{d.domain}</span>
                <span className="text-[13px] text-ink-muted">{d.reason}</span>
                <span className="text-[13px] text-ink-muted">{formatDate(d.created_at)}</span>
                <Button size="sm" variant="ghost" onClick={() => remove(d.id)}>
                  Unblock
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function AuditLog() {
  const { data, error } = useLoad<AuditEvent[]>("/admin/audit?limit=300");
  if (error) return <Alert tone="danger" title={error} />;
  return (
    <Card flush>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-[14px]">
          <thead>
            <tr className="bg-surface-sunken">
              {["When", "Event", "Who", "Subject", "IP", "Details"].map((h) => (
                <th key={h} className="eyebrow px-4 py-2 font-medium whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((e) => (
              <tr key={e.id} className="border-t border-line align-top">
                <td className="px-4 py-2 whitespace-nowrap text-ink-muted">{formatDate(e.created_at)}</td>
                <td className="px-4 py-2 font-mono text-[13px] whitespace-nowrap">{e.action}</td>
                <td className="px-4 py-2 break-all">{e.actor_email ?? "—"}</td>
                <td className="px-4 py-2 font-mono text-[13px] break-all">{e.subject ?? ""}</td>
                <td className="px-4 py-2 font-mono text-[13px] text-ink-muted">{e.ip ?? ""}</td>
                <td className="px-4 py-2 font-mono text-[12px] text-ink-muted break-all">
                  {Object.keys(e.details).length ? JSON.stringify(e.details) : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default function AdminPage() {
  const { user } = useUser();
  const [tab, setTab] = useState("overview");

  if (!user.is_superuser) {
    return (
      <Card>
        <EmptyState icon="lock" title="Admins only">
          This page is for administrators of this SecAI instance.
        </EmptyState>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="page-title">Instance admin</h1>
      <Tabs label="Admin sections" tabs={TABS} value={tab} onChange={setTab} />
      {tab === "overview" && <Overview />}
      {tab === "users" && <Users />}
      {tab === "settings" && <Settings />}
      {tab === "blocklist" && <Blocklist />}
      {tab === "audit" && <AuditLog />}
    </div>
  );
}
