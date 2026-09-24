# SeveritySummary

The count of findings per severity: a proportional bar and the five counts. Zero counts stay visible in `ink-muted`.

## Props
- `counts` (required): `{ critical?, high?, medium?, low?, info? }`. Missing keys count as 0.

## Do and don't
- Put it at the top of a scan report, beside `ScoreGrade`.
- Don't use it for anything except finding counts.
