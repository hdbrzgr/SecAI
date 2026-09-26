"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Alert, Button, Card, TextField } from "@secai/ui";
import { api, ApiError } from "@/lib/api";

export function ResetForm() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    if (form.get("password") !== form.get("confirm")) {
      setError("The two passwords don't match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api("/auth/password/reset", { body: { token, password: form.get("password") } });
      router.push("/login?reset=1");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <Card title="Reset your password">
        <Alert tone="danger" title="This link is incomplete">
          Open the link from the email again, or{" "}
          <Link href="/forgot-password" className="text-link">
            request a new one
          </Link>
          .
        </Alert>
      </Card>
    );
  }

  return (
    <Card title="Choose a new password">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <TextField
          label="New password"
          hint="At least 12 characters. You'll be signed out on every device."
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          required
          autoFocus
        />
        <TextField label="Repeat new password" name="confirm" type="password" autoComplete="new-password" required />
        {error && <Alert tone="danger" title={error} />}
        <Button type="submit" variant="primary" size="lg" loading={busy}>
          Save new password
        </Button>
      </form>
    </Card>
  );
}
