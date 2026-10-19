// Extract long string literals (the bundled markdown docs) from a minified Vite chunk.
// Usage: node extract-docs.mjs <input.js> <outdir>
import fs from 'node:fs';
import path from 'node:path';

const [, , input, outdir] = process.argv;
const src = fs.readFileSync(input, 'utf8');
fs.mkdirSync(outdir, { recursive: true });

// Vite emits template literals / quoted strings. Sniff both, keep the big ones.
const found = new Map();
let n = 0;

// Template literals (no interpolation handling needed: docs use no ${})
const tplRe = /`((?:[^`\\]|\\.)*)`/gs;
for (const m of src.matchAll(tplRe)) {
  const body = m[1];
  if (body.length < 800) continue;
  found.set(`tpl-${n++}`, body);
}

// Double-quoted strings, Json-escaped
const dqRe = /"((?:[^"\\]|\\.)*)"/g;
for (const m of src.matchAll(dqRe)) {
  const raw = m[1];
  if (raw.length < 800) continue;
  let body;
  try { body = JSON.parse(`"${raw}"`); } catch { continue; }
  found.set(`dq-${n++}`, body);
}

const manifest = [];
for (const [key, body] of found) {
  const head = body.slice(0, 120).replace(/\s+/g, ' ');
  const isDoc = /openapi\/v1\/challenges|tsec-benchmark|BENCHMARK_TOKEN|pip install/.test(body);
  const file = `${key}${isDoc ? '.DOC' : ''}.md`;
  fs.writeFileSync(path.join(outdir, file), body, 'utf8');
  manifest.push({ file, len: body.length, isDoc, head });
}

manifest.sort((a, b) => b.len - a.len);
console.log(JSON.stringify(manifest, null, 2));
console.log(`\n${manifest.length} literals >= 800 chars extracted to ${outdir}`);
