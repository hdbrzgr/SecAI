SecAI is an open-source security scanner. People point it at websites and repositories they own, and it tells them what is wrong and how to fix it. The interface should feel like a precise instrument: calm, exact and readable at a glance. It should never feel alarmist.

## Principles

- **Severity first, then detail.** Every screen that lists problems leads with how bad they are (`SeverityBadge`, `SeveritySummary`) before the explanation.
- **Calm about risk.** Color marks severity; the words stay level. A critical finding reads "Fix first", not "DANGER!".
- **Exact over decorative.** URLs, paths, headers, CWE ids and tokens are set in `mono`, exactly as the user must type or search them.
- **Never color alone.** Severity has a word and a pip count. Diffs have + and − signs. Statuses have an icon and a label.

## Voice and content

- Write to a developer who owns the site. Use "you" and "your site"; SecAI refers to itself as "SecAI", never "we" in product UI.
- Sentence case everywhere: buttons, titles, tabs ("Run scan", "Verify ownership", "Security settings"). Uppercase only through the `label` style.
- Name the fix, not the fear: "Add a Content-Security-Policy header", not "Your site is vulnerable to XSS!".
- Buttons say exactly what happens: "Run scan", "Copy", "Verify ownership", "Turn on". Confirmations name the result: "Scan started", "Copied".
- Errors say what happened and what to do: "The TXT record on example.com isn't visible yet. DNS changes can take a few minutes, so try again shortly."
- No emoji, no exclamation marks, no hacker slang ("pwned", "0day").
- Numbers carry units and are exact: "3 critical", "scanned 214 URLs in 4 min 12 s".
- Legal reminders are short and plain: "Only scan systems you own or have written permission to test."

## Color

Colors are semantic tokens with a Light and a Dark theme; Light is the fallback. Each text token's note names the grounds it may sit on, and every such pair clears 4.5:1 in both themes (`npm run check` in `packages/ui` verifies it).

- **Grounds.** `canvas` for the page, `surface` for cards, inputs and tables, `surface-sunken` for code, table headers and progress tracks, `surface-hover` for row hover. Separate them with `line` hairlines, not shadows.
- **Text.** `ink` for primary text, `ink-muted` for hints and metadata. There is no lighter grey; if text matters enough to show, it is `ink-muted` at least.
- **Brand.** `signal` (deep teal in Light, bright teal in Dark) is the one accent: primary buttons, links, the selected tab, the active nav item and the focus ring. Put `on-signal` text on it. Use `signal-soft` for selected backgrounds. Use it sparingly; one primary button per view.
- **Night.** `night` with `on-night` is for large brand areas only: marketing bands and the cover. Never inside the app UI.
- **Status.** `pass` (an alias of `signal`) for verified, passed and fixed; `warning` for things that need attention; `danger` for failures and destructive actions. Each has a `-soft` background. Status is always carried by an icon or word as well.
- **Severity.** `sev-critical`, `sev-high`, `sev-medium`, `sev-low` and `sev-info` with matching `-soft` backgrounds. They are reserved for findings: never reuse `sev-*` for buttons, charts of other data or decoration.
- **Code.** `code-add`/`code-remove` and their `-soft` backgrounds mark fix diffs; `code-highlight` marks the line a finding points at.

## Type

IBM Plex, one open-source superfamily in three voices. Self-host the files in `fonts/` (the app's CSP allows only its own origin).

- **Display** (IBM Plex Sans Condensed): `display-xl` for the marketing hero, `display` for page titles, `score` for the grade letter and big numbers. Always with tabular numerals for numbers.
- **Text** (IBM Plex Sans): `title` for card and section titles, `heading` for finding titles, `body` as the default (15/24), `body-strong` for emphasis and button labels, `body-sm` for metadata, `label` (uppercase, 0.06em tracking) for table headers and eyebrows.
- **Code** (IBM Plex Mono): `mono` for code blocks, URLs, headers and DNS records; `mono-sm` for locations in dense rows; `mono-strong` for a value the user must copy exactly.
- Keep explanation text within `prose-max` (680px). Titles use `text-wrap: balance`.

## Spacing and layout

- A 4px base: `space-1` 4 · `space-2` 8 · `space-3` 12 · `space-4` 16 · `space-5` 24 · `space-6` 32 · `space-7` 48 · `space-8` 64.
- App pages sit in a column of `content-max` (1120px) with a `space-4` side gutter on phones and `space-5` or more on desktop.
- Cards pad with `space-5`; dense lists pad rows with `space-3` × `space-4`. Sections are `space-6` apart.
- Control heights: `control-sm` 28 in tables and toolbars, `control-md` 36 by default, `control-lg` 44 for the main call to action on auth and marketing pages. Controls in one row share a height.
- A report page reads top to bottom: `ScoreGrade` and `SeveritySummary`, then `Tabs`, then `FindingRow` lists, then detail with `CodeBlock` fixes.

## Shape and elevation

- Small, precise radii: `radius-xs` 2 for pips and bar segments, `radius-sm` 4 for buttons, inputs and badges, `radius-md` 6 for cards, alerts and code, `radius-lg` 10 for dialogs. `radius-full` only for status dots and progress bars.
- Edges come from `line` borders. `shadow-raised` sits under cards on `canvas`; `shadow-overlay` is only for things that float (dialogs, menus, toasts).

## Focus and states

- Keyboard focus: 2px solid `focus` outline, offset 2px, on every interactive element. It clears 3:1 on every ground in both themes.
- Hover darkens fills (`signal` → `signal-strong`) or adds `surface-hover`. Disabled controls drop to 55% opacity and keep their layout.
- Loading swaps a button's icon for a spinning `loader-circle`; the label changes to say what is happening ("Checking").

## Motion

- Short and functional: 120ms for hover and press color changes, 300ms for progress. No entrance animations, no bouncing.
- Only one thing may move continuously: the spinner of a running scan. It stops under `prefers-reduced-motion`.

## Iconography

- Lucide (ISC license), 24px grid, drawn at a 1.75 stroke in `currentColor` through the `Icon` component. Sizes: 14 in badges and small text, 16 by default, 18 in alerts, 24 in empty states.
- Icons sit beside a label; an icon without a label needs an accessible name (`Icon label="…"`).
- The Icons asset group holds the shapes used across SecAI. The files are Lucide's originals with `stroke="currentColor"`, so as images they render black; in the product always draw them through `Icon`.
- No emoji and no illustrations of hackers, hoodies or padlocks-with-keyholes.

## The severity system

Five levels, in this order everywhere: Critical, High, Medium, Low, Info.

- Show severity with `SeverityBadge`: the uppercase word plus a meter of four pips (Critical 4, High 3, Medium 2, Low 1, Info 0). The pips let people with any kind of color vision rank findings at a glance.
- Summaries use `SeveritySummary`: a proportional bar plus the five counts, zero counts shown in `ink-muted`, never hidden.
- Sort findings by severity, then by how many locations they affect.

## Wordmark

SecAI has no drawn logo yet. The wordmark is type: "Sec" in `ink` and "AI" in `signal`, set in IBM Plex Sans Condensed Bold (`Wordmark` component). Don't substitute a shield, lock or eye symbol.

## License attribution

SecAI is AGPL-3.0 with an attribution term: every page of every SecAI instance shows the `Attribution` footer ("Powered by SecAI by hdbrzgr"). It may be restyled but never removed or hidden.
