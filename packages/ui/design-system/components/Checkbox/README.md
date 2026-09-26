# Checkbox

A labelled on/off choice with an optional description. SecAI uses it for the authorization attestation before a scan, and for settings.

## Props
- `label` (required) and `description` (optional, `ink-muted` under the label).
- Every other `<input>` attribute passes through (`checked`, `defaultChecked`, `onChange`, `required`, `name`).

## Do and don't
- The attestation label is exact and plain: "I own this website or have written permission to test it".
- Don't use a checkbox for an action that takes effect immediately; use a button.
