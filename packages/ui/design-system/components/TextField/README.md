# TextField

A labelled single-line input with an optional hint or error. Use it for every text input; never an input without a visible label.

## Props
- `label` (required): the visible label, in sentence case.
- `hint`: help shown under the input. Replaced by `error` when both are set.
- `error`: what is wrong and how to fix it; turns the border `danger` and sets `aria-invalid`.
- `mono`: sets the value in `mono`, for URLs, domains and tokens.
- Every other `<input>` attribute passes through (`type`, `name`, `autoComplete`, `required`…). An `id` is generated when you don't pass one.

## Do and don't
- Errors explain the fix: "Enter a full URL, like https://example.com".
- Don't use the placeholder as the label.
