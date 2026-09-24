# Alert

A message about the current page: a verified domain, a partial scan, a failed check. Not for findings.

## Props
- `tone`: `"info"` (default), `"success"`, `"warning"`, `"danger"`. Each has its own icon. `danger` uses `role="alert"`; the others `role="status"`.
- `title` (required): one sentence that says what happened.
- `children`: what to do next.
- `action`: an optional button.

## Do and don't
- Say what happened and what to do. Don't apologize or blame the user.
