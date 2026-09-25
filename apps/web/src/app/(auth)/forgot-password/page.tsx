"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Alert, Button, Card, TextField } from "@secai/ui";
import { api, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const email = String(new FormData(e.currentTarget).get("email"));
    setBusy(true);
    setError("");
    try {
      await api("/auth/password/forgot", { body: { email } });
      setSent(email);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Reset your password">
      {sent ? (
        <div className="flex flex-col gap-4">
          <Alert tone="success" title="Check your email">
            If an account exists for {sent}, a link to choose a new password is on its way. It
            works for 30 minutes.
          </Alert>
          <Link href="/login" className="text-link text-[14px]">
            Back to sign in
          </Link>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <p className="m-0 text-[14px] text-ink-muted">
            Enter your account&apos;s email address to get a link for choosing a new password.
          </p>
          <TextField label="Email" name="email" type="email" autoComplete="email" required autoFocus />
          {error && <Alert tone="danger" title={error} />}
          <Button type="submit" variant="primary" size="lg" loading={busy}>
            Send reset link
          </Button>
          <Link href="/login" className="text-link text-[14px]">
            Back to sign in
          </Link>
        </form>
      )}
    </Card>
  );
}
