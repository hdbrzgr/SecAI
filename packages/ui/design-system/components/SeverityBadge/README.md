# SeverityBadge

The severity of a finding: the uppercase word plus a four-pip meter (Critical 4, High 3, Medium 2, Low 1, Info 0), in the matching `sev-*` color on its `-soft` background. The pips make severity readable without color.

## Props
- `severity` (required): `"critical" | "high" | "medium" | "low" | "info"`.
- `pips`: set `false` to show the word only, in very dense tables.

## Do and don't
- Use it everywhere severity appears. Don't recolor a `Badge` to show severity.
