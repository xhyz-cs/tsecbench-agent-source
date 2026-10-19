// Scan the Claude Code native binary for environment-variable and endpoint strings.
// The binary is a Bun single-file executable (~271MB), so stream it in overlapping
// chunks and collect unique matches instead of loading it whole.
import fs from 'node:fs';
import readline from 'node:readline';

const target = process.argv[2];
if (!target) {
  console.error('usage: node scan-env.mjs <claude binary> [patternGroup]');
  process.exit(64);
}

const patterns = {
  env: /[A-Z][A-Z0-9_]{3,}[A-Z0-9]/g,
  urls: /https?:\/\/[a-z0-9.-]+\.[a-z]{2,}(?:\/[a-zA-Z0-9._~:/?#[\]@!$&'()*+,;=%-]*)?/g,
};

// `raw:<regex>` scans for an arbitrary literal pattern — used to probe a specific
// API surface (e.g. hook event names) in the shipped binary.
if (process.argv[3]?.startsWith('raw:')) {
  patterns.raw = new RegExp(process.argv[3].slice(4), 'g');
}

const which = process.argv[3]?.startsWith('raw:') ? 'raw' : (process.argv[3] || 'env');
const re = patterns[which];
if (!re) { console.error(`unknown group ${which}`); process.exit(64); }

// Interesting prefixes keep the env dump readable; everything else is noise.
const INTERESTING = which === 'raw'
  ? /.*/
  : /^(CLAUDE|ANTHROPIC|DISABLE|MAX|MCP|API_|BASE_URL|OTEL|BASH|USE_|IS_|FORCE_|SKIP_|ENABLE|HTTP|HTTPS|NO_|NODE|NPM|TINI|BASH_DEFAULT|SANDBOX|PLUGIN|IDE|TERM|COMPUTER|DOCKER)/;

const CHUNK = 8 * 1024 * 1024;
const OVERLAP = 1024; // wider than any plausible match
const found = new Map();

const fh = fs.openSync(target, 'r');
const buf = Buffer.alloc(CHUNK + OVERLAP);
let offset = 0;
let previousTail = '';

while (true) {
  const read = fs.readSync(fh, buf, 0, buf.length, offset);
  if (read <= 0) break;
  const text = previousTail + buf.toString('latin1', 0, read);
  for (const match of text.matchAll(re)) {
    const value = match[0];
    found.set(value, (found.get(value) || 0) + 1);
  }
  previousTail = text.slice(Math.max(0, text.length - OVERLAP));
  offset += read;
  if (read < buf.length) break;
}
fs.closeSync(fh);

let entries = [...found.entries()];
if (which === 'env') entries = entries.filter(([name]) => INTERESTING.test(name));
entries.sort((a, b) => b[1] - a[1]);

const out = process.stdout;
for (const [name, count] of entries) out.write(`${count}\t${name}\n`);
out.write(`\n# ${entries.length} unique ${which} matches\n`);
