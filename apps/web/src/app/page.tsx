import Link from "next/link";

const features = [
  {
    title: "Website pentest",
    body: "OWASP ZAP, Nuclei, TLS and header checks run against sites you've proven you own.",
  },
  {
    title: "Code scanning",
    body: "Connect GitHub to find insecure code, vulnerable dependencies and leaked secrets.",
  },
  {
    title: "AI fix guidance",
    body: "Findings are deduplicated, prioritized and explained, with fixes for your stack.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-5 pt-8">
        <h1 className="max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl">
          Find and fix security issues in your own projects.
        </h1>
        <p className="max-w-xl text-lg text-muted">
          SecAI runs proven open-source security tools and uses AI to turn the results into a
          clear, prioritized list of what to fix and how.
        </p>
        <div className="flex gap-3">
          <Link
            href="/register"
            className="inline-flex h-10 items-center rounded-md bg-accent px-4 text-sm font-medium text-accent-foreground"
          >
            Create account
          </Link>
          <Link
            href="/login"
            className="inline-flex h-10 items-center rounded-md border border-border px-4 text-sm font-medium"
          >
            Sign in
          </Link>
        </div>
      </section>
      <section className="grid gap-4 sm:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="rounded-xl border border-border bg-surface p-5">
            <h2 className="font-semibold">{f.title}</h2>
            <p className="mt-2 text-sm text-muted">{f.body}</p>
          </div>
        ))}
      </section>
      <p className="text-sm text-muted">
        Only scan systems you own or have written permission to test.
      </p>
    </div>
  );
}
