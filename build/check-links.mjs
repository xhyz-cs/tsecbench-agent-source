// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 James and minc
// Check that every markdown link in llms.txt / README.md / mcp/README.md resolves to a
// real file on disk (skips http(s) and anchors). Exit 1 if any local link is broken.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const files = ['llms.txt', 'llms-full.txt', 'README.md', 'mcp/README.md', 'mcp/tests/README.md'];

let broken = 0;
for (const rel of files) {
  const full = path.join(repo, rel);
  if (!fs.existsSync(full)) { console.log(`MISSING DOC: ${rel}`); broken++; continue; }
  const text = fs.readFileSync(full, 'utf8');
  // [label](target) — ignore images, code spans, http(s) targets, pure anchors
  const re = /(?<!!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
  let seen = 0;
  for (const m of text.matchAll(re)) {
    const target = m[1].split('#')[0];
    seen++;
    if (!target || /^https?:/i.test(target) || target.startsWith('mailto:')) continue;
    // resolve relative to the containing file
    const resolved = path.resolve(path.dirname(full), decodeURIComponent(target));
    if (!fs.existsSync(resolved)) {
      console.log(`  BROKEN in ${rel}: ${m[1]} -> ${resolved}`);
      broken++;
    }
  }
  console.log(`${rel}: ${seen} link(s) scanned`);
}
console.log(broken ? `\n${broken} problem(s)` : '\nAll local links resolve.');
process.exit(broken ? 1 : 0);
