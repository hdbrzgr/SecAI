import { Badge, Card, FindingRow, ScoreGrade, SeveritySummary } from "@secai/ui";
import { ButtonLink } from "@/components/ButtonLink";

const steps = [
  {
    title: "Add and verify your site",
    body: "Prove you own the domain with a DNS record, a file or a meta tag. SecAI never scans a site that isn't verified.",
  },
  {
    title: "Run a scan",
    body: "OWASP ZAP, Nuclei, TLS and header checks run against the site at a safe rate, from containers on your own server.",
  },
  {
    title: "Fix what matters first",
    body: "AI groups duplicate findings, sorts them by real risk and explains each fix for your stack, with code.",
  },
];

const checks: Array<{ name: string; what: string; soon?: boolean }> = [
  { name: "OWASP ZAP", what: "Crawls the site and tests for injection, XSS and misconfiguration" },
  { name: "Nuclei", what: "Checks thousands of known CVEs and exposed panels" },
  { name: "TLS", what: "Protocols, ciphers and certificate problems" },
  { name: "Headers and cookies", what: "CSP, HSTS, CORS and cookie flags" },
  { name: "Code scanning", what: "Insecure code, vulnerable dependencies and leaked secrets in GitHub repos", soon: true },
];

export default function Home() {
  return (
    <div className="mx-auto flex max-w-[1120px] flex-col gap-16 px-4 py-12 sm:px-6 sm:py-16">
      <section className="grid items-center gap-10 lg:grid-cols-[1fr_minmax(0,500px)]">
        <div className="flex flex-col gap-5">
          <span className="eyebrow">Open-source security scanning</span>
          <h1 className="m-0 font-display text-[40px] leading-[44px] font-bold tracking-[-0.01em] text-balance sm:text-[48px] sm:leading-[52px]">
            Find and fix security issues in the sites and code you own.
          </h1>
          <p className="prose-text m-0 text-[17px] leading-[28px]">
            SecAI runs proven open-source scanners against your website and uses AI to turn the
            results into a short, prioritized list of what to fix and exactly how.
          </p>
          <div className="flex flex-wrap gap-3">
            <ButtonLink href="/register" variant="primary" size="lg">
              Create account
            </ButtonLink>
            <ButtonLink href="https://github.com/hdbrzgr/SecAI" size="lg">
              Self-host from GitHub
            </ButtonLink>
          </div>
        </div>

        <Card
          title="Example report"
          actions={<span className="font-mono text-[13px] text-ink-muted">shop.example.com</span>}
          flush
        >
          <div className="flex flex-col gap-5 p-5">
            <ScoreGrade grade="C" score={64} caption="Example data" />
            <SeveritySummary counts={{ critical: 1, high: 2, medium: 5, low: 3, info: 6 }} />
          </div>
          <div className="border-t border-line">
            <FindingRow
              severity="critical"
              title="SQL injection in the search parameter"
              location="/search?q="
              cwe="CWE-89"
              tool="ZAP"
            />
            <FindingRow
              severity="high"
              title="Admin panel reachable without login"
              location="/admin/"
              cwe="CWE-306"
              tool="Nuclei"
            />
            <FindingRow
              severity="medium"
              title="Missing Content-Security-Policy header"
              location="/"
              cwe="CWE-693"
              tool="Headers"
            />
          </div>
        </Card>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="page-title">How it works</h2>
        <ol className="m-0 grid list-none gap-4 p-0 md:grid-cols-3">
          {steps.map((step, i) => (
            <li key={step.title} className="flex flex-col gap-2 rounded-md border border-line bg-surface p-5">
              <span className="font-mono text-[13px] text-ink-muted">Step {i + 1}</span>
              <h3 className="m-0 text-[17px] leading-6 font-semibold">{step.title}</h3>
              <p className="m-0 text-[15px] leading-6 text-ink-muted">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="page-title">What SecAI checks</h2>
        <dl className="m-0 grid gap-x-8 gap-y-4 md:grid-cols-2">
          {checks.map((c) => (
            <div key={c.name} className="flex flex-col gap-1 border-t border-line pt-4">
              <dt className="flex items-center gap-2 font-semibold">
                {c.name}
                {c.soon && <Badge>Coming soon</Badge>}
              </dt>
              <dd className="m-0 text-[15px] leading-6 text-ink-muted">{c.what}</dd>
            </div>
          ))}
        </dl>
      </section>

      <p className="m-0 text-[13px] leading-5 text-ink-muted">
        Only scan systems you own or have written permission to test.
      </p>
    </div>
  );
}
