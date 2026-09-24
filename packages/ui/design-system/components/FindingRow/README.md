# FindingRow

One finding in a list: severity, title, where it is (URL or file and line in `mono-sm`), CWE, the tool that found it and its status. Rows stack into two lines on phones.

## Props
- `severity`, `title`, `location`, `tool` (required).
- `cwe`: the CWE id, like "CWE-79".
- `status`: `"open"` (default), `"fixed"` (struck through, with a Fixed badge) or `"accepted"`.
- `href`: makes the whole row a link to the finding, with a chevron.

## Do and don't
- Titles name the problem in plain words ("Missing Content-Security-Policy header"), not the rule id.
- Put rows in a `flush` `Card`, sorted by severity.
