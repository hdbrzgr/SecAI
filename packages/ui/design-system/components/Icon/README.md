# Icon

Draws a Lucide icon at a 1.75 stroke in `currentColor`, so it takes the color of the text around it.

## Props
- `name` (required): one of the icon names bundled with the system: every icon in the Icons asset group plus `ban`, `check`, `chevron-right`, `loader-circle` and `plus` (see `IconName` in the types).
- `size`: px, default 16. Use 14 in badges, 18 in alerts, 24 in empty states.
- `label`: an accessible name. Without it the icon is decorative (`aria-hidden`).

## Do and don't
- Pair icons with text. An icon-only button needs `label` or an `aria-label` on the button.
