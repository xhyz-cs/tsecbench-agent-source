# Third-Party Notices

This repository — the **TSecBench Agent** source — combines original project code with
vendored third-party skill collections, pinned tool releases, and a build-time
dependency stack. This document is the authoritative inventory of those third-party
components: provenance, license identifiers, in-tree license evidence, and the
obligations that follow.

Original project contributions are **Copyright 2026 James and minc** and licensed under
the **Apache License 2.0** (`LICENSE`; attribution in `NOTICE`). That set includes the
MCP server, the Docker/entrypoint/orchestration code, the `build/` helpers, the Claude
Code plugin, **the hook components under `docker/claude/hooks/` and the mod components
under `plugin/mods/` (all in-house)**, the in-house skills under `skills/kit/`, and the
project documentation. None of those appear in the third-party inventory below. This
document is written in English; a Chinese summary for human readers is included in
`README.md` ("许可证（中文）") and in `README_CN.md`.

`NOASSERTION` in this document means that no SPDX license has been confirmed by this
inventory; it does not imply that a license is granted.

---

## 1. Vendored skill library (`skills/`)

`skills/` contains **987 `SKILL.md` files** from nine public GitHub collections, one
reference snapshot, and in-house skills. Files were taken file-by-file at the pinned
commits below (provenance detail: `skills/SOURCES.md`). Every vendored directory that
ships its own `LICENSE` file is governed by that file.

| ID | Upstream repository | Pinned commit | Installed as | Skills | SPDX | License evidence |
|---|---|---|---:|---:|---|---|
| S1 | https://github.com/transilienceai/communitytools | `95fdc128af4ca1ae16b3226f9430f1bad97b0656` | `skills/<name>/` | 22 (+6 nested) | MIT | Upstream `LICENSE` — Copyright (c) 2025 Transilience AI |
| S2 | https://github.com/ljagiello/ctf-skills | `c957f4f4fe8bb5c9da11e3494da3c5702a3ce878` | `skills/ctf-*/` (9 directories, incl. `ctf-writeup`), `skills/solve-challenge/` | 10 | MIT | Upstream `LICENSE` — Copyright (c) 2026 Lukasz Jagiello; per-file `license: MIT` |
| S3 | https://github.com/trilwu/secskills | `ca53957bcd8e3b83b5d4d190bb3ad008a4f15c84` | `skills/<name>/` | 38 | MIT | Upstream `LICENSE` — Copyright (c) 2025 Tri Luu |
| S4 | https://github.com/ADScanPro/Claude-AD | `73efec51207f6f740cb398e1c490e5edd60c1113` | `skills/kerberos-attacks/`, `skills/adcs-attacks/` | 2 | MIT | Upstream `LICENSE` — Copyright (c) 2026 ADscan |
| S5 | https://github.com/anthropics/skills | `dbd4588f9e1033efb41dad4bef2f7947c8993d44` | `skills/pdf/` | 1 | **Proprietary (Anthropic)** | In-tree `skills/pdf/LICENSE.txt`; frontmatter `license: Proprietary` |
| S6 | https://github.com/SnailSploit/Claude-Red | `a8de813edc9f66f60d44cfe42d47750e89d9930b` | `skills/<name>/` | 35 | MIT | Upstream `LICENSE` — Copyright (c) 2024-2025 SnailSploit / Kai Aizen |
| S7 | https://github.com/securityfortech/hacking-skills | `0aa49b400dc0e093947e393c45c09821bb8d45f4` | `skills/web/**` directories | 28 | 24 × MIT + 4 × Apache-2.0 (per file) | **No repository-level LICENSE.** Frontmatter declares MIT for 24 skills and Apache-2.0 for 4 (`jwt-misconfig`, `mass-assignment`, `open-redirect`, `insecure-file-upload`); no license text accompanies either declaration. See F2 |
| S8 | https://github.com/mukul975/Anthropic-Cybersecurity-Skills | `54a798831d2266a3ca61ce68a7acb80b81160d57` | `skills/<name>/` | 818 | Apache-2.0 | Repository license Apache-2.0; 817 of the 818 directories ship an Apache-2.0 `LICENSE` (see 1.1) |
| S9 | https://github.com/Masriyan/Claude-Code-CyberSecurity-Skill | `a3be55a446b0f42fe5bb70f268ac10f6eeadc38a` | `skills/01-recon-osint/` … `skills/22-purple-team/` | 22 | MIT | Upstream `LICENSE` — Copyright (c) 2026 Riyan Pratama; per-file `license: MIT` |

Additional in-tree content:

| Item | Source | License | Notes |
|---|---|---|---|
| `skills/payloadsallthethings/` | https://github.com/swisskyrepo/PayloadsAllTheThings (snapshot, 451 files) | MIT — Copyright (c) 2019 Swissky | In-tree `skills/payloadsallthethings/LICENSE` |
| `skills/kit/` (5 skills + `_methodology/`) | In-house skills authored by this project's team | Apache-2.0 (this repository) | Not third-party. Original project material; frontmatter declares `license: Apache-2.0` |
| `skills/ctf-*` (9 directories in the current tree) | Derived from ljagiello/ctf-skills (S2, MIT); curated versions supplied in the teammate kit, six of them replacing earlier copies | MIT | Modifications by the team; MIT notice of the upstream holder applies |

### 1.1 Per-directory license files — census

`skills/` contains **819 license-bearing files** (818 `LICENSE` + `skills/pdf/LICENSE.txt`):

| Count | Text | Copyright holder | Scope |
|---:|---|---|---|
| 814 | Apache-2.0 (standard appendix form) | 2026 mukul975 | S8 skill directories |
| 2 | Apache-2.0 (short form) | 2025 mukul975 | `implementing-attack-surface-management`, `performing-cloud-log-forensics-with-athena` |
| 1 | Apache-2.0 (standard appendix form) | 2026 dakshverma23 | `conducting-gdpr-compliance-assessment` |
| 1 | MIT | 2019 Swissky | `payloadsallthethings` |
| 1 | Anthropic proprietary terms | 2025 Anthropic, PBC | `pdf` |

Note: of the 818 S8 directories, 817 carry one of the Apache-2.0 files above; one
directory has no readable `LICENSE` text. Its `SKILL.md` still declares
`license: Apache-2.0`, and the upstream repository is Apache-2.0, so the license
status is unchanged — only the per-directory copy is missing.

### 1.2 Frontmatter `license:` declarations

Across the 987 `SKILL.md` files: **827** declare `license: Apache-2.0`, **56** declare
`license: MIT`, **1** declares `license: Proprietary. LICENSE.txt has complete terms`
(`skills/pdf`), and **103** carry no license field. Files without a field are governed
by the license of their source repository in the table above. (The 827 includes the
five in-house `skills/kit/` skills, whose declarations were added by this project.)

### 1.3 MIT copyright notices

The MIT license (full text in section 6) requires that the copyright notice and
permission notice accompany copies. Upstream copyright lines for the MIT-licensed
sources are:

- `Copyright (c) 2025 Transilience AI` — transilienceai/communitytools (S1)
- `Copyright (c) 2026 Lukasz Jagiello` — ljagiello/ctf-skills (S2)
- `Copyright (c) 2025 Tri Luu` — trilwu/secskills (S3)
- `Copyright (c) 2026 ADscan` — ADScanPro/Claude-AD (S4)
- `Copyright (c) 2024-2025 SnailSploit / Kai Aizen` — SnailSploit/Claude-Red (S6)
- securityfortech/hacking-skills (S7) — no repository-level copyright line; 24 files
  declare `license: MIT` in their frontmatter and 4 declare `license: Apache-2.0` (see
  F2)
- `Copyright (c) 2026 Riyan Pratama` — Masriyan/Claude-Code-CyberSecurity-Skill (S9)
- `Copyright (c) 2019 Swissky` — swisskyrepo/PayloadsAllTheThings (in-tree `LICENSE`)

---

## 2. Pinned tool releases (`docker/tools/releases/`)

| Component | Version | Ships in this repository | SPDX | Notes |
|---|---|---|---|---|
| Nikto | 2.6.1 | **Yes** — `nikto-2.6.1.zip`, unmodified official source archive | Code: **GPL-3.0-only** with additional distribution terms; database files: **not GPL** | Upstream `COPYING` requires the database files to be distributed only as part of the official Nikto package (this archive satisfies that); commercial terms: cirt.net/Nikto-Licensing. Bundled LibWhisker (`COPYING.LibWhisker`) is **BSD-2-Clause**. SHA-256 pinned in `SOURCES.sha256` |
| Ghidra | 12.1.4 | No — optional, gitignored; verified against `SOURCES.sha256` | Apache-2.0 | Official release package, unmodified |
| JADX | 1.5.6 | No — optional, gitignored; verified against `SOURCES.sha256` | Apache-2.0 | Official release package, unmodified |
| Eclipse Temurin JDK | 25 (base image `eclipse-temurin:25-jre-noble`) | Base image layer | GPL-2.0-only WITH Classpath-exception-2.0 | Runs Ghidra/JADX |

Kit provenance notes (including components that are **not** in this repository —
BLHX, Pozhen-Agent, Cruiser-Agent, pwntools, angr) are preserved in
`docker/tools/LICENSES-and-NOTICES.md`.

---

## 3. Build-time dependency stack (`docker/Dockerfile`)

These components are installed into the image at build time and are not part of the
repository tree. They carry their own licenses; identifiers below were verified against
each package registry or upstream source.

### 3.1 Base images

| Component | Version | SPDX | Notes |
|---|---|---|---|
| Node.js (`node:22-bookworm-slim`) | 22 | MIT | Node.js core is MIT (Node contributors, Joyent); third-party libraries bundled in Node are listed in its LICENSE file |
| Eclipse Temurin JRE (`eclipse-temurin:25-jre-noble`) | 25 | GPL-2.0-only WITH Classpath-exception-2.0 | Secondary license terms as published by the Eclipse Temurin project |

### 3.2 npm packages

| Package | Version | SPDX | Notes |
|---|---|---|---|
| `@anthropic-ai/claude-code` | 2.1.301 | **Proprietary** (`SEE LICENSE IN README.md`) | No OSI license; Anthropic commercial terms. See F4 |
| `chrome-devtools-mcp` | 0.6.0 | Apache-2.0 | — |

### 3.3 Python packages (pip)

| Package | SPDX | Notes |
|---|---|---|
| requests | Apache-2.0 | — |
| httpx | BSD-3-Clause | — |
| pwntools | MIT, with GPL/BSD portions | `Mostly MIT, some GPL/BSD, see LICENSE-pwntools.txt` |
| scapy | GPL-2.0-only | — |
| pycryptodome | BSD-2-Clause AND public domain | Upstream states portions are in the public domain |
| cryptography | Apache-2.0 OR BSD-3-Clause | Dual-licensed; either applies |
| beautifulsoup4 | MIT | — |
| lxml | BSD-3-Clause | — |
| PySocks | BSD-3-Clause | — |
| paramiko | LGPL-2.1 | Upstream ships the LGPL-2.1 text |
| dnspython | ISC | — |
| pyOpenSSL | Apache-2.0 | — |
| websockets | BSD-3-Clause | — |
| aiohttp | Apache-2.0 | — |
| impacket | **Modified Apache-1.1** (Fortra/SecureAuth variant) | Not Apache-2.0 and not a standard SPDX text; read the upstream LICENSE before redistribution |
| sympy | BSD-3-Clause | — |
| gmpy2 | LGPL-3.0-or-later | — |
| lief | Apache-2.0 | — |
| z3-solver | MIT | — |
| dirsearch | GPL-2.0-only | — |
| wafw00f | BSD-3-Clause | — |
| capstone | BSD-3-Clause | — |
| unicorn | GPL-2.0 (engine) | PyPI metadata still says "BSD License"; upstream repository LICENSE/README say GPLv2. Recorded as GPL-2.0 |
| ROPGadget | BSD-3-Clause | License file is `LICENSE_BSD.txt` |
| ropper | BSD-3-Clause | — |
| awscli | Apache-2.0 | — |
| angr (optional, `WITH_SYMBEX=1`) | BSD-2-Clause | — |
| mitmproxy (isolated venv, pinned 11.0.2) | MIT | — |

### 3.4 Debian packages (apt, bookworm)

About 60 Debian packages are installed (toolchain, Python runtime, Perl modules,
networking and archive utilities, browsers, and security tools). Each package carries
its own license; Debian's copyright metadata is retained in the image under
`/usr/share/doc/*/copyright`. Verified identifiers for the notable tools:

| Package | SPDX | Notes |
|---|---|---|
| nmap | NPSL-0.95 (Nmap Public Source License) | GPLv2-derived but not GPL-compatible; review before redistribution |
| sqlmap | GPL-2.0-or-later | Third-party components have additional exceptions (`doc/THIRD-PARTY.md`) |
| john | GPL-2.0-or-later | OpenSSL/unRAR linkage exceptions; some components are BSD-style |
| binwalk | MIT | — |
| tcpdump | BSD-3-Clause | — |
| chromium | BSD-3-Clause (primary) plus bundled third-party licenses | — |
| radare2 | GPL-3.0-only AND LGPL-3.0-only (where packaged) | **Not packaged in Debian bookworm**; the optional `apt install radare2` step reports `SKIPPED` on bookworm. The kit's radare2 6.2.4 snapshot is LGPL-3.0-primary |

The remaining packages (build-essential, cmake, python3, perl, curl, git, jq, ripgrep,
openssl, gdb, binutils, compression tools, `*_perl` modules, etc.) are under their
respective Debian-recorded licenses; the statement above covers them collectively.

---

## 4. External reference material (not distributed in this repository)

The teammate kit keeps reference sources in a `repositories/` directory outside this
repository. They are **not** part of this repository and must not be merged into it
without a license review:

| Component | SPDX | Note |
|---|---|---|
| `BLHX` | NOASSERTION | No root-level license statement found |
| `Pozhen-Agent` | NOASSERTION | No root-level license statement found |
| `Cruiser-Agent` | Apache-2.0 | — |
| pwntools | MIT, with portions under GPL/BSD and other licenses | Read `LICENSE-pwntools.txt` and file-level declarations |
| angr | BSD-2-Clause | — |
| jadx (source snapshot) | Apache-2.0 | — |
| radare2 (source snapshot) | LGPL-3.0 (primary) | Read `COPYING.md`, `doc/licenses` |

---

## 5. Compliance flags and required actions

### F1 — `skills/pdf` is Anthropic-proprietary (blocker before publication)

`skills/pdf/LICENSE.txt` states that the materials may not be extracted from
Anthropic's services, retained outside them, reproduced, used to create derivative
works, or distributed/sublicensed to third parties. The directory (12 files, including
8 scripts) was fetched from the public `anthropics/skills` repository, but its in-tree
license imposes those restrictions regardless of the fetch path.

Required action before making this repository public **or** distributing a built image:

```bash
git rm -r skills/pdf
```

Then remove the `pdf` row from `skills/INDEX.md` §5 and the related audit references.
If the skill is needed at runtime, retrieve it from Anthropic's distribution channel
under the applicable agreement instead of vendoring it.

### F2 — `securityfortech/hacking-skills` has no repository-level license (S7)

The upstream repository publishes no `LICENSE` file and no copyright notice. Of the 28
integrated skills, 24 declare `license: MIT` and 4 declare `license: Apache-2.0` in
their frontmatter, with no license text accompanying either declaration. This inventory
records the per-file declarations as-is. If a stricter provenance standard is required,
drop the 28 directories or obtain written confirmation from the maintainer.

### F3 — Nikto is GPL-3.0 (with non-GPL database files) and is redistributed as source

Nikto's `COPYING` is **GPL-3.0-only with additional terms**, not GPL-2.0. It also
states that Nikto's database files are not licensed under the GPL and may be
distributed only as part of the official Nikto package; the committed archive is the
official source release, which satisfies that condition. The bundled LibWhisker
(`COPYING.LibWhisker`) is BSD-2-Clause. If a built image containing Nikto is ever
distributed, GPLv3 source-availability obligations attach to Nikto's code; the pinned
unmodified archive in `docker/tools/releases/` satisfies that for the bundled version.

### F4 — Claude Code is proprietary (npm `@anthropic-ai/claude-code`)

The built image installs the package under Anthropic's commercial terms. The image is
for the evaluation environment; do not publish or redistribute it without confirming
the redistribution terms of that package.

### F5 — Base image / Debian packages

The image contains Debian packages and a Temurin JDK under their own licenses (mostly
GPL-2.0+, BSD, Apache-2.0, and Artistic, plus non-GPL terms such as nmap's NPSL-0.95
and Nikto's GPL-3.0 terms). Debian copyright files are retained in
`/usr/share/doc/*/copyright` inside the image. Do not distribute the built image
without a corresponding notice bundle.

---

## 6. MIT license text

The following text applies to the MIT-licensed components identified above, with the
copyright holders listed in section 1.3:

```text
MIT License

Copyright (c) <year> <copyright holder>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Apache-2.0 components retain their upstream `LICENSE` files in their directories; the
standard Apache-2.0 text is also the text of this repository's root `LICENSE`.

---

## 7. Verification method

- Skill sources: GitHub repository metadata and the `LICENSE` file fetched from each
  repository at the pinned commit (2026-10-20), cross-checked against the in-tree
  per-directory `LICENSE` files and `SKILL.md` frontmatter.
- In-tree census: repository-wide search for `LICENSE`/`COPYING`/`NOTICE` files and
  frontmatter `license:` fields; counts in sections 1.1 and 1.2 are reproducible from
  the tree.
- Build-time dependencies: license fields from the npm registry and PyPI metadata, and
  upstream/package-tracker sources for Debian packages.
- This inventory describes the tree at the time of writing. Re-run the census after
  adding or updating vendored content.
