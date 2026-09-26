# CodeBlock

Code with line numbers, for showing where a finding is and how to fix it. Lines can be marked added (+) or removed (−) for a fix diff, and a line can be highlighted.

## Props
- `lines` (required): strings, or `{ text, kind }` with `kind` `"add" | "remove" | "context"`.
- `startLine`: number of the first line, default 1. Removed lines don't take a number.
- `highlight`: line numbers to mark with `code-highlight` (the line the finding points at).
- `title`: a caption in `mono`, usually the file path.

## Do and don't
- Show only the lines that matter, with a few lines of context.
- Long lines scroll inside the block; they never widen the page.
