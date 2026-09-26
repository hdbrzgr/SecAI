# Badge

A short label for a state: "Verified", "Fixed", "Not verified", "Accepted risk". Not for severity; use `SeverityBadge`.

## Props
- `tone`: `"neutral"` (default), `"signal"` (pass, verified, fixed), `"warning"`, `"danger"`.
- `icon`: an optional `IconName` before the text; use one when the tone carries meaning.
- `children`: one or two words.
