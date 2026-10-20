// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 James and minc
// Assemble llms-full.txt from the header + docs/*.md, rewriting the docs-relative links
// so they resolve from the repo root. Re-run after editing any docs/ file:
//   node build/assemble-llms-full.mjs
import fs from 'node:fs';
import path from 'node:path';

const repo = 'D:/tmp/secbench.zc.tencent.com';
const enc = 'utf8';

const header = fs.readFileSync(path.join(repo, 'build/llms-full-header.md'), enc);
const docs = [
  'challenges-api.md',
  'platform-modes.md',
  'sdk-python.md',
  'agent-prompt.md',
];

const docDir = path.join(repo, 'docs');
const outDir = repo; // llms-full.txt lives at the root, so links must be root-relative

function rewriteLinks(text) {
  // Rewrite  ](target.md)  /  ](target.md#anchor)  where `target.md` is a file that only
  // exists inside docs/ — i.e. a link authored relative to docs/, not to the root.
  return text.replace(/\]\(([^)#\s]+\.md)(#[^)\s]*)?\)/g, (whole, target, anchor = '') => {
    const docResolves = fs.existsSync(path.join(docDir, target));
    const rootResolves = fs.existsSync(path.join(outDir, target));
    if (docResolves && !rootResolves) return `](docs/${target}${anchor})`;
    return whole;
  });
}

const body = [header.trimEnd(), ...docs.map((name) => rewriteLinks(fs.readFileSync(path.join(docDir, name), enc).trimEnd()))].join('\n\n---\n\n');
fs.writeFileSync(path.join(repo, 'llms-full.txt'), body + '\n', enc);

console.log(`llms-full.txt: ${fs.statSync(path.join(repo, 'llms-full.txt')).size} bytes from ${docs.length} doc(s)`);
