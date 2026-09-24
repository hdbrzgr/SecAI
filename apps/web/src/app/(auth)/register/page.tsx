"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Alert, Button, Card, TextField } from "@secai/ui";
import { api, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api("/auth/register", {
        body: {
          name: form.get("name") || null,
          email: form.get("email"),
          password: form.get("password"),
        },
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create the account. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Create your account">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <TextField label="Name" name="name" autoComplete="name" />
        <TextField label="Email" name="email" type="email" autoComplete="email" required />
        <TextField
          label="Password"
          hint="At least 12 characters. A short sentence works well."
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          required
        />
        {error && <Alert tone="danger" title={error} />}
        <Button type="submit" variant="primary" size="lg" loading={busy}>
          Create account
        </Button>
      </form>
      <p className="mt-5 mb-0 text-[14px] text-ink-muted">
        Already have an account?{" "}
        <Link href="/login" className="text-link">
          Sign in
        </Link>
      </p>
    </Card>
  );
}
