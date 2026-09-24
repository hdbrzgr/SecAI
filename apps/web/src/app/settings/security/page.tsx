"use client";

import QRCode from "qrcode";
import { type FormEvent, useState } from "react";
import { Button, Card, ErrorText, Input } from "@/components/ui";
import { api, ApiError, type User } from "@/lib/api";
import { useUser } from "@/lib/useUser";

type Setup = { secret: string; otpauth_uri: string; qr: string };

export default function SecuritySettingsPage() {
  const [user, setUser] = useUser();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const startSetup = () =>
    run(async () => {
      const data = await api<Omit<Setup, "qr">>("/auth/mfa/setup", { method: "POST" });
      // Rendered locally: the secret never goes to a third-party QR service.
      setSetup({ ...data, qr: await QRCode.toDataURL(data.otpauth_uri, { margin: 1 }) });
    });

  const enable = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const code = new FormData(e.currentTarget).get("code");
    run(async () => {
      setUser(await api<User>("/auth/mfa/enable", { body: { code } }));
      setSetup(null);
    });
  };

  const disable = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    run(async () => {
      setUser(
        await api<User>("/auth/mfa/disable", {
          body: { password: form.get("password"), code: form.get("code") },
        }),
      );
    });
  };

  if (!user) return <p className="text-muted">Loading…</p>;

  return (
    <div className="flex max-w-lg flex-col gap-6">
      <h1 className="text-2xl font-semibold">Security settings</h1>
      <Card>
        <h2 className="font-semibold">Two-factor authentication</h2>
        <p className="mt-1 text-sm text-muted">
          Status: <strong>{user.mfa_enabled ? "On" : "Off"}</strong>
        </p>

        {!user.mfa_enabled && !setup && (
          <Button className="mt-4" onClick={startSetup} disabled={busy}>
            Set up authenticator app
          </Button>
        )}

        {setup && (
          <form onSubmit={enable} className="mt-4 flex flex-col gap-4">
            <p className="text-sm">
              Scan this QR code with an authenticator app (1Password, Aegis, Google
              Authenticator…), then enter the 6-digit code.
            </p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={setup.qr} alt="Authenticator QR code" className="h-44 w-44 rounded bg-white" />
            <p className="text-xs text-muted">
              Can&apos;t scan? Enter this key: <code className="break-all">{setup.secret}</code>
            </p>
            <Input label="Code" name="code" inputMode="numeric" autoComplete="one-time-code" required />
            <Button type="submit" disabled={busy}>
              Turn on
            </Button>
          </form>
        )}

        {user.mfa_enabled && (
          <form onSubmit={disable} className="mt-4 flex flex-col gap-4">
            <p className="text-sm text-muted">To turn it off, confirm your password and a code.</p>
            <Input label="Password" name="password" type="password" autoComplete="current-password" required />
            <Input label="Code" name="code" inputMode="numeric" autoComplete="one-time-code" required />
            <Button type="submit" disabled={busy}>
              Turn off
            </Button>
          </form>
        )}
        <div className="mt-4">
          <ErrorText>{error}</ErrorText>
        </div>
      </Card>
    </div>
  );
}
