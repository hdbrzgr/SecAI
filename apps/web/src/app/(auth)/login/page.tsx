"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Alert, Button, Card, TextField } from "@secai/ui";
import { api, ApiError, type LoginResult } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<"password" | "mfa">("password");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      const result =
        step === "password"
          ? await api<LoginResult>("/auth/login", {
              body: { email: form.get("email"), password: form.get("password") },
            })
          : await api<LoginResult>("/auth/login/mfa", { body: { code: form.get("code") } });
      if (result.mfa_required) setStep("mfa");
      else router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't sign in. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title={step === "password" ? "Sign in" : "Two-factor authentication"}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        {step === "password" ? (
          <>
            <TextField label="Email" name="email" type="email" autoComplete="email" required />
            <TextField
              label="Password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </>
        ) : (
          <TextField
            key="code"
            label="Code"
            hint="The 6-digit code from your authenticator app."
            name="code"
            mono
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9 ]{6,8}"
            autoFocus
            required
          />
        )}
        {error && <Alert tone="danger" title={error} />}
        <Button type="submit" variant="primary" size="lg" loading={busy}>
          {step === "password" ? "Sign in" : "Verify"}
        </Button>
      </form>
      <p className="mt-5 mb-0 text-[14px] text-ink-muted">
        No account yet?{" "}
        <Link href="/register" className="text-link">
          Create one
        </Link>
      </p>
    </Card>
  );
}
