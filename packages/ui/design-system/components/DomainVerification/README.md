# DomainVerification

Proves a user owns a website before SecAI will scan it. Shows the record to add for the chosen method, a copy button and the verify action.

## Props
- `domain` (required): the hostname, like "example.com".
- `method` (required): `"dns_txt"` (a TXT record `secai-verify=<token>`), `"well_known_file"` (the token served at `/.well-known/secai-verify.txt`) or `"meta_tag"` (a `<meta name="secai-verify">` tag).
- `token` (required): the verification token.
- `status`: `"pending"` (default), `"checking"`, `"verified"` or `"failed"`.
- `onVerify`: called by "Verify ownership".

## Do and don't
- Show the exact value in `mono-strong`, with Copy. Never ask the user to retype it.
- On failure, say what wasn't found and suggest waiting for DNS; don't say "error".
