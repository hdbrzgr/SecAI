# Button

Triggers an action. `secondary` is the default; use one `primary` per view for the main action, `danger` only for destructive actions that are confirmed, and `ghost` inside toolbars, tables and code blocks.

## Props
- `variant`: `"primary" | "secondary" | "ghost" | "danger"`, default `"secondary"`.
- `size`: `"sm"` (`control-sm`, tables and toolbars), `"md"` (default), `"lg"` (`control-lg`, main call to action on auth and marketing pages).
- `icon`: an `IconName` shown before the label.
- `loading`: swaps the icon for a spinner, disables the button and sets `aria-busy`. Change the label to say what is happening ("Checking").
- Every other `<button>` attribute passes through. `type` defaults to `"button"`; set `type="submit"` in forms.

## Do and don't
- Labels are verbs in sentence case that say what happens: "Run scan", "Verify ownership", "Copy".
- Don't put two primary buttons side by side. Don't use `danger` for "Cancel".
