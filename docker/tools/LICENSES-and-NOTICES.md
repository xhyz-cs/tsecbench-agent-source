# Sources and license record (teammate kit)

> This file preserves the source/license notes that arrived with the teammate tool kit
> (`TsecBench-Agent-Kit`). It is kept for provenance. The authoritative, repository-wide
> inventory — skill sources, vendored releases, and the full build-time dependency
> stack — is [`../../THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).
>
> Kit-only references below (`repositories/manifest.json`, `requirements-linux.txt`,
> `tools/releases/SOURCES.txt`) are artifacts of the kit and are **not** part of this
> repository.

Snapshot provenance is recorded in the kit's `repositories/manifest.json`, archived at
the GitHub default branch and commit captured at download time; the source snapshots do
not carry Git history. Confirm the terms of use per repository from the LICENSE/NOTICE
files in each repository root and from that manifest; `NOASSERTION` means no SPDX license
has been confirmed by this record and does not imply a license grant.

- `BLHX`, `Pozhen-Agent`: no root-level license statement found; `NOASSERTION`.
- `Cruiser-Agent`: Apache-2.0.
- `jadx`: Apache-2.0; LICENSE/NOTICE retained.
- `radare2`: primarily LGPLv3, with different licenses for dependencies/plugins; read
  `COPYING.md` and `doc/licenses`.
- `pwntools`: primarily MIT, with portions under GPL/BSD and other licenses; read
  `LICENSE-pwntools.txt` and file-level declarations.
- `angr`: BSD-2-Clause.
- `PayloadsAllTheThings`: MIT.

Source snapshots are kept as-is from upstream. Before modifying or redistributing,
check each repository's LICENSE, NOTICE, third-party dependency licenses, and trademark
requirements file by file; source without a license statement is treated as local
reference material only, and confirmation from the maintainers is required before any
public redistribution.

## Nikto 2.6.1

Upstream: https://github.com/sullo/nikto (tag 2.6.1). The source archive is
redistributed unmodified and contains the upstream `COPYING` and `COPYING.LibWhisker`
files. Verified on 2026-10-20: `COPYING` is GPL-3.0-only with additional terms and
states that the database files are not GPL-licensed and may only be distributed as part
of the official Nikto package; `COPYING.LibWhisker` is BSD-2-Clause.

## Binary and Python dependencies

Ghidra, JADX, radare2, and the Python packages listed in the kit's
`requirements-linux.txt` each carry independent licenses and dependencies. Official
release packages are unmodified; versions and official download links were recorded in
the kit's `tools/releases/SOURCES.txt`, and download SHA-256 values are pinned in
`SOURCES.sha256` in this directory. Verify the licenses shipped with each release and
its dependencies before building or redistributing.

## Note for this repository

- Only `nikto-2.6.1.zip` (plus `SOURCES.sha256` and `README.md`) is committed here.
  Ghidra/JADX archives are optional and stay out of Git (see `.gitignore`).
- The in-repo build-time dependency stack and its license identifiers are inventoried in
  [`../../THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).
