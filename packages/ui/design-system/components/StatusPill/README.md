# StatusPill

The state of a scan: an icon and a word. Running scans show a spinner that stops under reduced motion.

## Props
- `status` (required): `"queued" | "running" | "succeeded" | "failed" | "cancelled"`, shown as Queued, Scanning, Completed, Failed and Cancelled.
- `label`: overrides the word, for example "Scanning · 62%".
