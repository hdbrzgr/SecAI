"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Alert, Button, Card, TextField } from "@secai/ui";
import { ButtonLink } from "@/components/ButtonLink";
import { api, ApiError, type Target } from "@/lib/api";

export default function NewWebsitePage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const url = new FormData(e.currentTarget).get("url");
    setBusy(true);
    setError("");
    try {
      const target = await api<Target>("/targets", { body: { url } });
      router.push(`/websites/${target.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add the website. Try again.");
      setBusy(false);
    }
  }

  return (
    <div className="flex max-w-[680px] flex-col gap-6">
      <h1 className="page-title">Add a website</h1>
      <Card>
        <form onSubmit={onSubmit} className="flex flex-col gap-5">
          <TextField
            label="Website address"
            name="url"
            mono
            placeholder="https://example.com"
            hint="SecAI scans this address and pages it links to on the same domain. Next, you'll prove you own it."
            autoFocus
            required
          />
          {error && <Alert tone="danger" title={error} />}
          <div className="flex gap-2">
            <Button type="submit" variant="primary" loading={busy}>
              Add website
            </Button>
            <ButtonLink href="/websites" variant="ghost">
              Cancel
            </ButtonLink>
          </div>
        </form>
      </Card>
      <p className="m-0 text-[13px] leading-5 text-ink-muted">
        Only add websites you own or have written permission to test.
      </p>
    </div>
  );
}
