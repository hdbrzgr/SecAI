"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Button, Card, ErrorText, Input } from "@/components/ui";
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
      setError(err instanceof ApiError ? err.message : "Could not sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="mx-auto max-w-sm">
      <h1 className="mb-6 text-xl font-semibold">
        {step === "password" ? "Sign in" : "Two-factor authentication"}
      </h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        {step === "password" ? (
          <>
            <Input label="Email" name="email" type="email" autoComplete="email" required />
            <Input
              label="Password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </>
        ) : (
          <Input
            key="code"
            label="6-digit code from your authenticator app"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9 ]{6,8}"
            autoFocus
            required
          />
        )}
        <ErrorText>{error}</ErrorText>
        <Button type="submit" disabled={busy}>
          {step === "password" ? "Sign in" : "Verify"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted">
        No account?{" "}
        <Link href="/register" className="text-foreground underline">
          Create one
        </Link>
      </p>
    </Card>
  );
}
