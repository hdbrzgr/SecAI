"use client";

import { useEffect, useState } from "react";
import { api, type PublicConfig } from "@/lib/api";

export function usePublicConfig(): PublicConfig | null {
  const [config, setConfig] = useState<PublicConfig | null>(null);
  useEffect(() => {
    api<PublicConfig>("/auth/config").then(setConfig, () =>
      setConfig({ registration_open: true, email_enabled: false }),
    );
  }, []);
  return config;
}
