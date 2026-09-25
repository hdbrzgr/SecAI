"use client";
// SecAI — Copyright (C) 2026 hdbrzgr. AGPL-3.0 with an attribution term; see NOTICE.
import * as React from "react";
import { ICONS, type IconName } from "./icons.gen";

type Children = { children?: React.ReactNode };
const cx = (...c: Array<string | false | null | undefined>) => c.filter(Boolean).join(" ");

/* ---------- Icon ---------- */

export type IconProps = { name: IconName; size?: number; label?: string; className?: string };

/** Lucide icon, 1.75 stroke, drawn in currentColor. Decorative unless `label` is given. */
export function Icon({ name, size = 16, label, className }: IconProps) {
  const parts = ICONS[name] ?? [];
  return (
    <svg
      className={cx("sx-icon", className)}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      {parts.map(([tag, attrs], i) => React.createElement(tag, { key: i, ...attrs }))}
    </svg>
  );
}

/* ---------- Wordmark & attribution ---------- */

export function Wordmark({ size = 20 }: { size?: number }) {
  return (
    <span className="sx-wordmark" style={{ fontSize: size }}>
      Sec<span className="sx-wordmark-ai">AI</span>
    </span>
  );
}

/** Required by the SecAI license (AGPL-3.0 §7(b) term): keep it visible on every page. */
export function Attribution() {
  return (
    <footer className="sx-attribution">
      Powered by{" "}
      <a href="https://github.com/hdbrzgr/SecAI" target="_blank" rel="noopener noreferrer">
        SecAI by hdbrzgr
      </a>{" "}
      · Open source under AGPL-3.0
    </footer>
  );
}

export type NavItem = { label: string; href: string; active?: boolean };

export function AppHeader({
  nav = [],
  actions,
}: {
  nav?: NavItem[];
  actions?: React.ReactNode;
}) {
  return (
    <header className="sx-header">
      <div className="sx-header-inner">
        <a href="/" className="sx-header-brand" aria-label="SecAI home">
          <Wordmark />
        </a>
        <nav className="sx-header-nav" aria-label="Main">
          {nav.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={cx("sx-header-link", item.active && "is-active")}
              aria-current={item.active ? "page" : undefined}
            >
              {item.label}
            </a>
          ))}
        </nav>
        {actions && <div className="sx-header-actions">{actions}</div>}
      </div>
    </header>
  );
}

/* ---------- Actions ---------- */

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  icon?: IconName;
  loading?: boolean;
};

export function Button({
  variant = "secondary",
  size = "md",
  icon,
  loading = false,
  className,
  children,
  disabled,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx("sx-btn", `sx-btn-${variant}`, `sx-btn-${size}`, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <Icon name="loader-circle" className="sx-spin" />
      ) : (
        icon && <Icon name={icon} />
      )}
      {children}
    </button>
  );
}

/* ---------- Forms ---------- */

export type TextFieldProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  mono?: boolean;
};

export function TextField({ label, hint, error, mono, id, className, ...rest }: TextFieldProps) {
  const autoId = React.useId();
  const inputId = id ?? autoId;
  const noteId = `${inputId}-note`;
  const hasError = Boolean(error);
  return (
    <div className={cx("sx-field", hasError && "has-error", className)}>
      <label htmlFor={inputId} className="sx-field-label">
        {label}
      </label>
      <input
        id={inputId}
        className={cx("sx-input", mono && "is-mono")}
        aria-invalid={hasError || undefined}
        aria-describedby={hasError || hint ? noteId : undefined}
        {...rest}
      />
      {(hasError || hint) && (
        <p id={noteId} className={cx("sx-field-note", hasError && "is-error")}>
          {hasError && <Icon name="circle-x" size={14} />}
          {hasError ? error : hint}
        </p>
      )}
    </div>
  );
}

export type CheckboxProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: React.ReactNode;
  description?: React.ReactNode;
};

export function Checkbox({ label, description, id, className, ...rest }: CheckboxProps) {
  const autoId = React.useId();
  const inputId = id ?? autoId;
  return (
    <div className={cx("sx-check", className)}>
      <input id={inputId} type="checkbox" className="sx-check-input" {...rest} />
      <label htmlFor={inputId} className="sx-check-text">
        <span className="sx-check-label">{label}</span>
        {description && <span className="sx-check-desc">{description}</span>}
      </label>
    </div>
  );
}

/* ---------- Layout ---------- */

export function Card({
  title,
  actions,
  children,
  flush = false,
  className,
}: Children & {
  title?: React.ReactNode;
  actions?: React.ReactNode;
  flush?: boolean;
  className?: string;
}) {
  return (
    <section className={cx("sx-card", flush && "is-flush", className)}>
      {(title || actions) && (
        <div className="sx-card-head">
          {title && <h2 className="sx-card-title">{title}</h2>}
          {actions && <div className="sx-card-actions">{actions}</div>}
        </div>
      )}
      <div className="sx-card-body">{children}</div>
    </section>
  );
}

export type TabItem = { id: string; label: string; count?: number };

export function Tabs({
  tabs,
  value,
  defaultValue,
  onChange,
  label = "Sections",
}: {
  tabs: TabItem[];
  value?: string;
  defaultValue?: string;
  onChange?: (id: string) => void;
  label?: string;
}) {
  const [inner, setInner] = React.useState(defaultValue ?? tabs[0]?.id);
  const current = value ?? inner;
  const refs = React.useRef<Array<HTMLButtonElement | null>>([]);
  const select = (id: string) => {
    setInner(id);
    onChange?.(id);
  };
  const onKeyDown = (e: React.KeyboardEvent, index: number) => {
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = (index + step + tabs.length) % tabs.length;
    select(tabs[next].id);
    refs.current[next]?.focus();
  };
  return (
    <div className="sx-tabs" role="tablist" aria-label={label}>
      {tabs.map((t, i) => {
        const selected = t.id === current;
        return (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            className={cx("sx-tab", selected && "is-selected")}
            onClick={() => select(t.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {t.label}
            {t.count !== undefined && <span className="sx-tab-count">{t.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

/* ---------- Status ---------- */

export type BadgeTone = "neutral" | "signal" | "warning" | "danger";

export function Badge({
  tone = "neutral",
  icon,
  children,
}: Children & { tone?: BadgeTone; icon?: IconName }) {
  return (
    <span className={cx("sx-badge", `sx-badge-${tone}`)}>
      {icon && <Icon name={icon} size={12} />}
      {children}
    </span>
  );
}

export type ScanStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

const STATUS: Record<ScanStatus, { label: string; icon: IconName }> = {
  queued: { label: "Queued", icon: "clock" },
  running: { label: "Scanning", icon: "loader-circle" },
  succeeded: { label: "Completed", icon: "circle-check" },
  failed: { label: "Failed", icon: "circle-x" },
  cancelled: { label: "Cancelled", icon: "ban" },
};

export function StatusPill({ status, label }: { status: ScanStatus; label?: string }) {
  const s = STATUS[status];
  return (
    <span className={cx("sx-status", `sx-status-${status}`)}>
      <Icon name={s.icon} size={14} className={status === "running" ? "sx-spin" : undefined} />
      {label ?? s.label}
    </span>
  );
}

export function ProgressBar({
  value,
  max = 100,
  label,
  detail,
}: {
  value: number;
  max?: number;
  label: string;
  detail?: React.ReactNode;
}) {
  const pct = Math.max(0, Math.min(100, Math.round((value / max) * 100)));
  return (
    <div className="sx-progress">
      <div className="sx-progress-top">
        <span className="sx-progress-label">{label}</span>
        <span className="sx-progress-value">{pct}%</span>
      </div>
      <div
        className="sx-progress-track"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="sx-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      {detail && <div className="sx-progress-detail">{detail}</div>}
    </div>
  );
}

export type AlertTone = "info" | "success" | "warning" | "danger";
const ALERT_ICON: Record<AlertTone, IconName> = {
  info: "info",
  success: "circle-check",
  warning: "triangle-alert",
  danger: "octagon-alert",
};

export function Alert({
  tone = "info",
  title,
  children,
  action,
}: Children & { tone?: AlertTone; title: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className={cx("sx-alert", `sx-alert-${tone}`)} role={tone === "danger" ? "alert" : "status"}>
      <Icon name={ALERT_ICON[tone]} size={18} className="sx-alert-icon" />
      <div className="sx-alert-text">
        <p className="sx-alert-title">{title}</p>
        {children && <div className="sx-alert-body">{children}</div>}
      </div>
      {action && <div className="sx-alert-action">{action}</div>}
    </div>
  );
}

export function EmptyState({
  icon = "scan-search",
  title,
  children,
  action,
}: Children & { icon?: IconName; title: string; action?: React.ReactNode }) {
  return (
    <div className="sx-empty">
      <span className="sx-empty-icon">
        <Icon name={icon} size={24} />
      </span>
      <h3 className="sx-empty-title">{title}</h3>
      {children && <p className="sx-empty-body">{children}</p>}
      {action && <div className="sx-empty-action">{action}</div>}
    </div>
  );
}

/* ---------- Security ---------- */

export type Severity = "critical" | "high" | "medium" | "low" | "info";
export const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];
const SEV_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};
const SEV_PIPS: Record<Severity, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };

/** Severity word plus a 4-pip meter, so severity reads without color. */
export function SeverityBadge({ severity, pips = true }: { severity: Severity; pips?: boolean }) {
  const filled = SEV_PIPS[severity];
  return (
    <span className={cx("sx-sev", `sx-sev-${severity}`)}>
      {pips && (
        <span className="sx-sev-pips" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className={cx("sx-sev-pip", i < filled && "is-on")} />
          ))}
        </span>
      )}
      {SEV_LABEL[severity]}
    </span>
  );
}

export function SeveritySummary({ counts }: { counts: Partial<Record<Severity, number>> }) {
  const total = SEVERITIES.reduce((n, s) => n + (counts[s] ?? 0), 0);
  return (
    <div className="sx-sevsum">
      <div className="sx-sevsum-bar" aria-hidden="true">
        {total === 0 ? (
          <span className="sx-sevsum-empty" />
        ) : (
          SEVERITIES.filter((s) => counts[s]).map((s) => (
            <span
              key={s}
              className={cx("sx-sevsum-seg", `sx-sevsum-${s}`)}
              style={{ flexGrow: counts[s] }}
            />
          ))
        )}
      </div>
      <dl className="sx-sevsum-legend">
        {SEVERITIES.map((s) => (
          <div key={s} className={cx("sx-sevsum-item", !counts[s] && "is-zero")}>
            <dt>
              <span className={cx("sx-sevsum-key", `sx-sevsum-${s}`)} aria-hidden="true" />
              {SEV_LABEL[s]}
            </dt>
            <dd>{counts[s] ?? 0}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export type Grade = "A" | "B" | "C" | "D" | "F";

export function ScoreGrade({
  grade,
  score,
  label = "Security grade",
  caption,
}: {
  grade: Grade;
  score: number;
  label?: string;
  caption?: React.ReactNode;
}) {
  const tone = grade === "A" || grade === "B" ? "pass" : grade === "C" ? "warning" : "danger";
  return (
    <div className={cx("sx-grade", `sx-grade-${tone}`)}>
      <span className="sx-grade-letter" aria-hidden="true">
        {grade}
      </span>
      <div className="sx-grade-text">
        <span className="sx-grade-label">{label}</span>
        <span className="sx-grade-score">
          <span className="sr-only">
            Grade {grade},{" "}
          </span>
          {score}
          <span className="sx-grade-max">/100</span>
        </span>
        {caption && <span className="sx-grade-caption">{caption}</span>}
      </div>
    </div>
  );
}

export type FindingStatus = "open" | "fixed" | "accepted";

export function FindingRow({
  severity,
  title,
  location,
  tool,
  cwe,
  status = "open",
  href,
  onClick,
  expanded,
}: {
  severity: Severity;
  title: string;
  location: string;
  tool: string;
  cwe?: string;
  status?: FindingStatus;
  href?: string;
  onClick?: () => void;
  expanded?: boolean;
}) {
  const body = (
    <>
      <span className="sx-finding-sev">
        <SeverityBadge severity={severity} />
      </span>
      <span className="sx-finding-main">
        <span className="sx-finding-title">{title}</span>
        <span className="sx-finding-loc">{location}</span>
      </span>
      <span className="sx-finding-meta">
        {cwe && <span className="sx-finding-cwe">{cwe}</span>}
        <span>{tool}</span>
      </span>
      <span className="sx-finding-status">
        {status === "fixed" && (
          <Badge tone="signal" icon="check">
            Fixed
          </Badge>
        )}
        {status === "accepted" && <Badge>Accepted risk</Badge>}
        {(href || onClick) && (
          <Icon name="chevron-right" className={cx("sx-finding-chevron", expanded && "is-open")} />
        )}
      </span>
    </>
  );
  const className = cx("sx-finding", status === "fixed" && "is-fixed", expanded && "is-expanded");
  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick} aria-expanded={expanded}>
        {body}
      </button>
    );
  }
  return href ? (
    <a href={href} className={className}>
      {body}
    </a>
  ) : (
    <div className={className}>{body}</div>
  );
}

export type CodeLine = { text: string; kind?: "add" | "remove" | "context" };

/** Code or a fix diff. Line kinds are shown with +/− signs as well as color. */
export function CodeBlock({
  title,
  lines,
  startLine = 1,
  highlight = [],
}: {
  title?: string;
  lines: Array<string | CodeLine>;
  startLine?: number;
  highlight?: number[];
}) {
  const rows = lines.map((l) => (typeof l === "string" ? { text: l } : l));
  let n = startLine - 1;
  return (
    <figure className="sx-code">
      {title && <figcaption className="sx-code-title">{title}</figcaption>}
      <div className="sx-code-scroll">
        <table className="sx-code-table">
          <tbody>
            {rows.map((row, i) => {
              const lineNo = row.kind === "remove" ? "" : String(++n);
              const sign = row.kind === "add" ? "+" : row.kind === "remove" ? "−" : "";
              return (
                <tr
                  key={i}
                  className={cx(
                    row.kind && `is-${row.kind}`,
                    row.kind !== "remove" && highlight.includes(n) && "is-highlight",
                  )}
                >
                  <td className="sx-code-no">{lineNo}</td>
                  <td className="sx-code-sign" aria-label={sign === "+" ? "added" : sign ? "removed" : undefined}>
                    {sign}
                  </td>
                  <td className="sx-code-text">{row.text || " "}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

export type VerificationMethod = "dns_txt" | "well_known_file" | "meta_tag";

const METHOD: Record<VerificationMethod, { label: string; where: (d: string) => string; value: (t: string) => string }> = {
  dns_txt: {
    label: "DNS TXT record",
    where: (d) => `Add a TXT record on ${d}`,
    value: (t) => `secai-verify=${t}`,
  },
  well_known_file: {
    label: "File on your site",
    where: (d) => `Serve this text at https://${d}/.well-known/secai-verify.txt`,
    value: (t) => t,
  },
  meta_tag: {
    label: "HTML meta tag",
    where: () => "Add this tag inside <head> on your home page",
    value: (t) => `<meta name="secai-verify" content="${t}">`,
  },
};

export function DomainVerification({
  domain,
  method,
  token,
  status = "pending",
  onVerify,
}: {
  domain: string;
  method: VerificationMethod;
  token: string;
  status?: "pending" | "checking" | "verified" | "failed";
  onVerify?: () => void;
}) {
  const m = METHOD[method];
  const value = m.value(token);
  const [copied, setCopied] = React.useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(value).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1600);
      },
      () => setCopied(false),
    );
  };
  return (
    <div className="sx-verify">
      <div className="sx-verify-head">
        <span className="sx-verify-domain">
          <Icon name="globe" />
          {domain}
        </span>
        {status === "verified" ? (
          <Badge tone="signal" icon="shield-check">
            Verified
          </Badge>
        ) : status === "failed" ? (
          <Badge tone="danger" icon="circle-x">
            Not found yet
          </Badge>
        ) : (
          <Badge icon="clock">Not verified</Badge>
        )}
      </div>
      <p className="sx-verify-where">
        <span className="sx-verify-method">{m.label}</span>
        {m.where(domain)}
      </p>
      <div className="sx-verify-value">
        <code>{value}</code>
        <Button size="sm" variant="ghost" icon={copied ? "check" : "copy"} onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      {status !== "verified" && (
        <div className="sx-verify-foot">
          <span className="sx-verify-hint">DNS changes can take a few minutes to show up.</span>
          <Button variant="primary" loading={status === "checking"} onClick={onVerify}>
            {status === "checking" ? "Checking" : "Verify ownership"}
          </Button>
        </div>
      )}
    </div>
  );
}
