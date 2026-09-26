# @secai/ui: the SecAI design system

The source of the SecAI design system, published in Claude Design at
https://claude.ai/artifact/Eu7M6wukvHRi69oLHyuLSE (see `design-system-artifact.json`).

| Path | What |
|---|---|
| `design-system/tokens.json` | Colors (light and dark), type, spacing, radius, shadow and size tokens |
| `design-system/README.md` | The brand book: voice, color, type, layout, severity system, iconography |
| `design-system/components/<Name>/` | Guidelines (`README.md`) and a live preview for each component |
| `src/components.tsx`, `src/styles.css` | The React components and their styles (class prefix `sx-`) |
| `scripts/build.mjs` | Builds the bundle, types, fonts, `dist/tokens.css` and the files published to Claude Design |
| `scripts/check-contrast.mjs` | Checks every text/background pair the tokens promise, in both themes |

```bash
npm install
npm run check   # contrast of every promised pair, light and dark
npm run build   # dist/design-system/project, dist/tokens.css, dist/fonts
```

Fonts: IBM Plex (SIL Open Font License). Icons: Lucide (ISC).
