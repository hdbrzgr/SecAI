"use client";

import QRCode from "qrcode";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Alert, Badge, Button, Card, TextField } from "@secai/ui";
import { api, ApiError, type User } from "@/lib/api";
import { useUser } from "@/lib/user";

type Setup = { secret: string; otpauth_uri: string; qr: string };

export default function SecuritySettingsPage() {
  const router = useRouter();
  const { user, setUser } = useUser();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
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
      setNotice("Two-factor authentication is on. Other devices were signed out.");
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
      setNotice("Two-factor authentication is off.");
    });
  };

  const signOutEverywhere = () =>
    run(async () => {
      await api("/auth/logout-all", { method: "POST" });
      router.push("/login");
    });

  return (
    <div className="flex max-w-[680px] flex-col gap-6">
      <h1 className="page-title">Security settings</h1>

      {notice && <Alert tone="success" title={notice} />}
      {error && <Alert tone="danger" title={error} />}

      <Card
        title="Two-factor authentication"
        actions={
          user.mfa_enabled ? (
            <Badge tone="signal" icon="shield-check">
              On
            </Badge>
          ) : (
            <Badge>Off</Badge>
          )
        }
      >
        {!user.mfa_enabled && !setup && (
          <div className="flex flex-col items-start gap-4">
            <p className="prose-text m-0">
              Ask for a code from an authenticator app (1Password, Aegis, Google Authenticator)
              every time you sign in.
            </p>
            <Button variant="primary" icon="lock" onClick={startSetup} loading={busy}>
              Set up authenticator app
            </Button>
          </div>
        )}

        {setup && (
          <form onSubmit={enable} className="flex flex-col gap-4">
            <p className="m-0">Scan this QR code with your authenticator app, then enter the 6-digit code it shows.</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={setup.qr} alt="QR code for your authenticator app" className="h-44 w-44 rounded-sm bg-white p-1" />
            <p className="m-0 text-[13px] leading-5 text-ink-muted">
              Can&apos;t scan it? Enter this key instead:{" "}
              <code className="font-mono break-all text-ink">{setup.secret}</code>
            </p>
            <div className="max-w-[240px]">
              <TextField label="Code" name="code" mono inputMode="numeric" autoComplete="one-time-code" required />
            </div>
            <div className="flex gap-2">
              <Button type="submit" variant="primary" loading={busy}>
                Turn on
              </Button>
              <Button variant="ghost" onClick={() => setSetup(null)}>
                Cancel
              </Button>
            </div>
          </form>
        )}

        {user.mfa_enabled && (
          <form onSubmit={disable} className="flex flex-col gap-4">
            <p className="prose-text m-0">To turn it off, confirm your password and a current code.</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField label="Password" name="password" type="password" autoComplete="current-password" required />
              <TextField label="Code" name="code" mono inputMode="numeric" autoComplete="one-time-code" required />
            </div>
            <div>
              <Button type="submit" variant="danger" loading={busy}>
                Turn off
              </Button>
            </div>
          </form>
        )}
      </Card>

      <Card title="Sessions">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="prose-text m-0">Sign out on every device, including this one.</p>
          <Button icon="log-out" onClick={signOutEverywhere} disabled={busy}>
            Sign out everywhere
          </Button>
        </div>
      </Card>
    </div>
  );
}
