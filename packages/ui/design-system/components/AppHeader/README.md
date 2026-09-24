# AppHeader

The top bar of the signed-in app: the `Wordmark`, main navigation and account actions.

## Props
- `nav`: `[{ label, href, active? }]`. The active item gets `signal` text on `signal-soft` and `aria-current="page"`.
- `actions`: content at the right, usually a ghost button for the account.

## Do and don't
- Keep the nav to the main areas: Dashboard, Websites, Repositories, Settings.
- Don't put the primary action ("Run scan") in the header; it belongs on the page.
