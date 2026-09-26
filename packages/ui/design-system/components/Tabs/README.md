# Tabs

Switches between views of the same object, like the sections of a scan report. Arrow keys move between tabs.

## Props
- `tabs` (required): `[{ id, label, count? }]`. `count` shows a tabular number badge.
- `value` and `onChange` for a controlled tab, or `defaultValue` for an uncontrolled one.
- `label`: the accessible name of the tab list, default "Sections".

## Do and don't
- Keep labels to one or two words. Show counts when they help decide where to look ("Findings 23").
- Don't use tabs for steps in a sequence.
