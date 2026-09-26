# Card

A `surface` panel with a `line` border that groups one topic: a scan summary, a list of findings, a settings section.

## Props
- `title`: a `title` heading (rendered as `h2`).
- `actions`: buttons shown at the right of the header (use `size="sm"`).
- `flush`: removes body padding, for lists and tables that run edge to edge.
- `children`: the content.

## Do and don't
- One topic per card. Don't nest cards; use a `line` divider inside instead.
- Put `FindingRow` lists in a `flush` card.
