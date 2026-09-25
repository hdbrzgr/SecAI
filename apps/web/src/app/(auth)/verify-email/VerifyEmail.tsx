"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Alert, Card } from "@secai/ui";
import { ButtonLink } from "@/components/ButtonLink";
import { api, ApiError } from "@/lib/api";

export function VerifyEmail() {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<"checking" | "done" | "error">(token ? "checking" : "error");
  const [message, setMessage] = useState(token ? "" : "This link is incomplete.");
  const started = useRef(false);

  useEffect(() => {
    // The token is single-use: don't post it twice (React strict mode runs effects twice in dev).
    if (!token || started.current) return;
    started.current = true;
    api("/auth/email/verify", { body: { token } }).then(
      () => setState("done"),
      (err) => {
        setState("error");
        setMessage(err instanceof ApiError ? err.message : "Something went wrong.");
      },
    );
  }, [token]);

  return (
    <Card title="Confirm your email address">
      {state === "checking" && <p className="m-0 text-ink-muted">Checking the link…</p>}
      {state === "done" && (
        <div className="flex flex-col gap-4">
          <Alert tone="success" title="Your email address is confirmed">
            You can now add websites and run scans.
          </Alert>
          <ButtonLink href="/dashboard" variant="primary">
            Go to your dashboard
          </ButtonLink>
        </div>
      )}
      {state === "error" && (
        <div className="flex flex-col gap-4">
          <Alert tone="danger" title={message} />
          <p className="m-0 text-[14px] text-ink-muted">
            Sign in and use <strong>Send again</strong> on your dashboard to get a new link.{" "}
            <Link href="/login" className="text-link">
              Sign in
            </Link>
          </p>
        </div>
      )}
    </Card>
  );
}
