// Checks every text/ground pair the token usage notes promise, in both themes.
import { readFileSync } from "node:fs";

const tokens = JSON.parse(readFileSync(new URL("../design-system/tokens.json", import.meta.url)));
const byName = Object.fromEntries(tokens.color.tokens.map((t) => [t.name, t.value]));
const themes = tokens.color.themes.map((t) => t.id);

function resolve(name, theme) {
  let v = byName[name];
  if (typeof v === "object") v = v[theme] ?? v[themes[0]];
  const alias = /^\{(.+)\}$/.exec(v);
  return alias ? resolve(alias[1], theme) : v;
}
function lum(hex) {
  const n = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(n.slice(i, i + 2), 16) / 255);
  const f = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}
function ratio(a, b) {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

const TEXT = 4.5, UI = 3;
const pairs = [];
const grounds = ["canvas", "surface", "surface-sunken", "surface-hover"];
for (const g of grounds) pairs.push(["ink", g, TEXT]);
for (const g of ["canvas", "surface", "surface-sunken"]) pairs.push(["ink-muted", g, TEXT]);
for (const g of ["canvas", "surface", "signal-soft"]) pairs.push(["signal", g, TEXT]);
for (const g of ["canvas", "surface", "surface-sunken"]) pairs.push(["focus", g, UI], ["line-control", g, UI]);
pairs.push(["on-signal", "signal", TEXT], ["on-signal", "signal-strong", TEXT], ["on-danger", "danger", TEXT]);
pairs.push(["on-night", "night", TEXT]);
for (const s of ["danger", "warning"]) pairs.push([s, "surface", TEXT], [s, `${s}-soft`, TEXT]);
pairs.push(["pass", "pass-soft", TEXT]);
for (const s of ["critical", "high", "medium", "low", "info"])
  pairs.push([`sev-${s}`, "surface", TEXT], [`sev-${s}`, `sev-${s}-soft`, TEXT], [`sev-${s}`, "surface-sunken", UI]);
pairs.push(["code-add", "code-add-soft", TEXT], ["code-remove", "code-remove-soft", TEXT]);
pairs.push(["ink", "code-add-soft", TEXT], ["ink", "code-remove-soft", TEXT], ["ink", "code-highlight", TEXT]);
pairs.push(["ink-muted", "code-highlight", TEXT]);

let failed = 0;
for (const theme of themes) {
  for (const [fg, bg, min] of pairs) {
    const r = ratio(resolve(fg, theme), resolve(bg, theme));
    if (r < min) {
      failed++;
      console.log(`FAIL ${theme}: ${fg} on ${bg} = ${r.toFixed(2)} (needs ${min})`);
    }
  }
}
console.log(failed ? `${failed} failing pairs` : `All ${pairs.length * themes.length} pairs pass`);
process.exit(failed ? 1 : 0);
