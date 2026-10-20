# Sources — skill provenance, screening log, reconciliation

> Licensing status for every source listed here (SPDX identifiers, in-directory LICENSE
> evidence, and compliance flags) is inventoried in
> [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md). In-house skills under
> `kit/` are original project material licensed under Apache-2.0, not third-party
> content.
>
> **Post-collection removals:** `skills/pdf` (source #5) was removed on 2026-10-20
> because its license is Anthropic-proprietary and prohibits retention outside
> Anthropic's services. Counts below are the audit-time records and are not adjusted.

All skills under `skills/` were collected on **2026-10-16/17** from public GitHub
repositories at the pinned commits below, file-by-file via `raw.githubusercontent.com`
(no repo was ever cloned into this repository; the browser fetch pipeline is described
at the end). Every file's UTF-8 byte length was verified against the upstream blob size
at write time (`skills/_fetch/decode.py`, exit 0, zero mismatches).

## Installed sources

| # | Repository | Commit | Taken | Installed as |
|---|---|---|---|---|
| 1 | https://github.com/transilienceai/communitytools | `95fdc128af4ca1ae16b3226f9430f1bad97b0656` | `skills/<name>/` (22 of 47 dirs) | 22 skills, sections 1 |
| 2 | https://github.com/ljagiello/ctf-skills | `c957f4f4fe8bb5c9da11e3494da3c5702a3ce878` | `<name>/` (10 of 11 dirs) | 10 skills, section 2 |
| 3 | https://github.com/trilwu/secskills | `ca53957bcd8e3b83b5d4d190bb3ad008a4f15c84` | `secskills-offense/skills/<name>/`, `secskills-core/skills/<name>/` (38 dirs) | 38 skills, section 3 |
| 4 | https://github.com/ADScanPro/Claude-AD | `73efec51207f6f740cb398e1c490e5edd60c1113` | `skills/kerberos-attacks/`, `skills/adcs-attacks/` | 2 skills, section 4 |
| 5 | https://github.com/anthropics/skills | `dbd4588f9e1033efb41dad4bef2f7947c8993d44` | `skills/pdf/` (1 of 18 skill dirs) | 1 skill, section 5 |
| 6 | https://github.com/SnailSploit/Claude-Red | `a8de813edc9f66f60d44cfe42d47750e89d9930b` | `Skills/<domain>/<name>/` (35 of 79 dirs) | 35 skills, section 6 |
| 7 | https://github.com/securityfortech/hacking-skills | `0aa49b400dc0e093947e393c45c09821bb8d45f4` | `skills/web/**` (28 dirs) | 28 skills, section 7 |
| 8 | https://github.com/mukul975/Anthropic-Cybersecurity-Skills | `54a798831d2266a3ca61ce68a7acb80b81160d57` | **all 818** `skills/*` dirs (user-directed) | 818 skills, section 8 |
| 9 | https://github.com/Masriyan/Claude-Code-CyberSecurity-Skill | `a3be55a446b0f42fe5bb70f268ac10f6eeadc38a` | **all 22** `skills/*` dirs (user-directed) | 22 skills, section 9 |

Sources 1–7 were fetched by the collector agent through the browser fetch pipeline
(JSON-batched staging in `skills/_fetch/`, expanded by `decode.py`, staging deleted after
a clean run). Sources 8–9 were cloned by the mock-builder teammate into a scratch dir
outside the repo at the pinned commits and copied dir-by-dir (only directories containing
`SKILL.md`, name collisions skipped and reported); no scripts from those repos were executed.

### Fetch-pipeline incident note (SnailSploit batch, handled 2026-10-17)

One staging batch (`dump-snail-02.json`) was saved double-encoded: the fetch pipeline
serialized the return value as a JSON string whose content was itself JSON. Mock-builder
handled it correctly: (1) original bytes preserved verbatim at
`D:\tmp\skill-scratch\dump-snail-02.orig.json` (804,222 bytes), (2) only the outer
encoding stripped after verifying the inner object matched the expected schema
(SHA `a8de813…`, 18 files, zero byte-length mismatches), (3) decode re-run clean.
Both pinned clones and the snail-02 original were retained in
`D:\tmp\skill-scratch` through the audit; with the audit gate passed and zero
scan rejections there was nothing left to re-check upstream, and the scratch dir
was released for deletion (pinned SHAs above remain the permanent provenance record).

### Final layout decision and full-tree scan (2026-10-17, team-lead)

The upstream directory taxonomy is preserved as-is (no six-way physical reorg);
the six TSecBench challenge classes are expressed as the category sections of
`INDEX.md` instead. The staged stdlib scanner (`archive.py`, scan mode only —
it moved nothing) was then run once over the final tree as the formal evidence
pass for the screening log above: every `.py`/`.sh` script and every `SKILL.md`
in all 976 directories. Scanner and results are retained at `skills/` root
(`archive.py`, `audit-scan.json`): 650 files carried ≥1 informational pattern
flag (network / exec / pipe-shell / base64-decode / env+network — the expected
makeup of offensive tooling and LLM scaffolds); exactly 2 reject-candidates
were raised, both Slack `hooks.slack.com/services/T000/B000/XXXX`-style
documentation placeholders rather than live tokens — in
`deploying-honeytokens-and-canarytokens/SKILL.md` and
`offensive-data-exfiltration/SKILL.md` — reviewed in context and retained.
**Skills rejected: 0.** Run history: mock-builder reviewed the scanner before
running it and fixed a one-line variable-shadowing bug in its largest-scripts
listing comprehension (reporting-only field); the first run crashed on that
bug, the second completed clean. After a crossed instruction briefly deleted
both artifacts, they were restored by re-running the fixed scan — output
identical modulo the generation timestamp (234,448 B), confirming
determinism. `apply` mode was never executed — no directory was moved.
Complete write history of `skills/` (mtime-verified by mock-builder):
754 + 115 + 18 decode files, 4484 + 80 clone-copied files — all mock-builder,
each gated on an explicit GO and exit-0 decodes — plus one collector write
(the `exploit-regression` frontmatter fix) and the scan artifacts.

### Notes on individual sources

- **ljagiello/ctf-skills** is the upstream of the `michael-ltm/ctf-skills` Claude Code
  plugin fork; content identical per the fork's README, upstream taken as canonical.
- **SnailSploit/Claude-Red**: 18 of the 35 selected skills use a non-YAML metadata format
  (`# SKILL:` + `## Metadata` bullet list). Frontmatter was synthesized mechanically from
  each file's own `Skill Name`/`Folder`/`Description` fields; bodies are verbatim and each
  file carries an in-body provenance note. `exploit-regression` is the frontmatter name
  the source file itself declared for `Skills/exploit-dev/offensive-exploit-development`.
- **anthropics/skills**: only `pdf` taken (59 KB, local-only scripts). `docx`/`pptx`/`xlsx`
  were excluded — 1.1 MB each, mostly vendored ISO-29500 XSD schemas.
- **transilienceai/communitytools** exclusions: `coordination` (orchestration replaced by
  the container's own fleet coordinator), `hackerone`/`hackthebox` (platform-specific, ship
  scripts), `cloud-containers` (975 KB, three 250–390 KB CIS/MCSB/NSA JSON catalogs),
  `blockchain-security`, `firewall-review`, `pci-secure-software` (528 KB catalog),
  `transilience-report-style` (vendor-branded PDF generator + scripts), `skill-update`/
  `skill-prune`/`github-workflow`/`script-generator`/`cve-risk-score`/`ti-ingest`/
  `attack-path-stitcher`/`regression-sweep`/`risk-prioritiser`/`cloud-defense`/
  `network-appliance-offensive`/`protect-with-password`/`cryptography` (out of the
  weighted scope or duplicated).
- **SnailSploit** exclusions: four skills with single files of 354–567 KB
  (`offensive-basic-exploitation`, `offensive-crash-analysis`, `offensive-windows-boundaries`,
  `offensive-windows-mitigations`) per the "no huge files" rule; wireless/AI/social/OSINT/
  supply-chain/mobile/utility clusters (out of the weighted scope, already covered).
- **ljagiello/ctf-skills** exclusions: `ctf-ai-ml` (adversarial-ML, not defense-evasion;
  LLM coverage exists via `ai-threat-testing`); `ctf-malware` **is** included.

## Unavailable / rejected sources (reported, not installed)

| Source | Status |
|---|---|
| https://github.com/Ak-cybe/awesome-offensive-security-skills (191 skills incl. a red-team evasion cluster) | **HTTP 404 — repository deleted or renamed** between discovery and collection (2026-10-17). Evasion coverage was obtained from SnailSploit `offensive-edr-evasion` / `offensive-anti-forensics` / `offensive-waf-bypass` and trilwu `establishing-persistence` / `transferring-files` instead. |
| 0xSteph/pentest-ai-agents (50 subagents, MIT) | Wrong artifact format for a skills image: `agents/*.md` subagent definitions, not `SKILL.md` skill directories. Not converted — category coverage already achieved by installed skills. |
| DouglasRao/Claude-Pentest-Skills | Skill dirs are thin wrappers around bash/Python pipelines that assume a Kali toolchain and write reports to Notion; overlap with installed web/AD skills. |
| 0xGhostCAT/claude-ai-cyber-security-skills, bob-reis/claude-pentest-skills, securityfortech/hacking-skills `mobile|cicd|meta` subdirs, Evaluris-Solutions/claude-active-directory, sickn33/antigravity-awesome-skills, majiayu000/claude-skill-registry-data | Functional overlap with installed collections; slash-command or aggregator formats; or single-maintainer low-signal repos. |
| ferr079/claude-code-cybersec-skills | Slash-command format (31 commands), not skills; its upstream (`mukul975/Anthropic-Cybersecurity-Skills`) is installed in full. |
| michael-ltm/ctf-skills | Fork of source #2; deduplicated to upstream. |
| PayloadsAllTheThings (swisskyrepo) | Not vendored: `patt-fetcher` skill fetches payload pages on demand by design. |
| No skill was rejected for prompt-injection, exfiltration, or hidden-instruction content | See screening log below. |

## Security screening log (supply-chain)

Checked on the installed tree (line-based grep + individual reads):

| Check | Result |
|---|---|
| Prompt-injection phrasing (`ignore previous instructions`, `system override`, …) | Hits only inside LLM-security payload corpora and detection rules (`ai-threat-testing`, `api-security/reference/scenarios/web-llm/*`, `16-ai-llm-security`, `defending-llms-with-guardrails`, `detecting-ai-model-prompt-injection-attacks`, `implementing-llm-guardrails-for-security`, plus attack-payload examples in `offensive-initial-access`/`offensive-xss`). These are the payloads those skills exist to test *for*; none address the agent running the skill. |
| Exfiltration endpoints (`webhook.site`, `requestbin`, `pipedream`, `api.telegram.org`, Discord webhooks, `ngrok`, `pastebin/raw`) | All hits are OOB-callback testing documentation with placeholder IDs (`webhook.site/YOUR_ID`), malware-traffic analysis content, or forensic log examples. No author-controlled or hardcoded live endpoint. |
| Pipe-to-shell installers (`curl … | sh`) | All hits are instructions for official third-party installers (rustup, syft/grype, tailscale, docker, foundry, uv, linpeas) or attack-technique examples with `attacker.com` placeholders in markdown. Nothing executes at bake or install time. |
| `/dev/tcp/` reverse-shell one-liners | Technique documentation (cron-persistence example, bash-jail escape, port-check probe). |
| Base64/hex blobs ≥400 chars | Exactly one file: `implementing-zero-knowledge-proof-for-authentication/scripts/agent.py` — the RFC 3526 2048-bit MODP group prime constant (cryptographic constant, verified by reading). No encoded instruction blobs anywhere. |
| Script primitives (`requests`, `socket`, `subprocess`, `os.system`, `eval`, `exec`, `b64decode`) | 2,204 occurrences across 617 `.py` files — mukul975/Masriyan agent scaffolds (LLM-API calls to operator-configured endpoints, local tool invocation) and CTF exploit templates (pwntools, operator-specified target). Samples read per family; no hardcoded C2/exfil host. |
| All 20 curated scripts (pdf ×8, authentication ×4, infrastructure ×1, server-side ×1, ctf-web ×1, ctf-pwn ×5) | Read in full. Local-only or operator-targeted; two are offensive by design (NetNTLMv2 listener, ASP.NET ViewState payload builder) and only act when the operator invokes them. |
| Executable content run during collection | **None.** No skill-repo installer, script, hook, or Makefile was executed. `decode.py` (written by the collector, stdlib-only: json/pathlib/sys) was the only code run, reviewed by mock-builder before execution and run with `python -I`. |

## Count reconciliation (authoritative)

- Collector's initial upstream-tree estimate for the curated sources was **766** files;
  the decoded count was **754**. Root cause: the estimate double-counted
  `techstack-identification`'s six nested sub-skills (12 files) — upstream per-skill
  counts: 13 (root, including the 12 nested files) — so 766 − 12 = **754**, matching
  the decoded total exactly, confirmed independently by mock-builder's filesystem scan
  (754 files, extensions 732 `.md` / 20 `.py` / 1 `.txt` / 1 `.json`).
- Second browser batch decoded to 121 additional files; the third batch added the final
  18 SnailSploit files (the one skill whose source lacks YAML frontmatter,
  `offensive-exploit-development`, is installed as `exploit-regression` with frontmatter
  synthesized from the source's own metadata — applied directly at audit time); the two
  user-directed collections add 818 + 22 skill directories.
- Final: **982 `SKILL.md` files** = 142 curated (136 top-level + 6 nested
  techstack sub-skills) + 818 (mukul975) + 22 (Masriyan), ~5,470 total files (~45 MB).
  All 982 carry both `name:` and `description:` frontmatter. No missing or extra skills
  relative to the pinned upstream tree listings.

## Method note (why not `git clone`)

The collector agent's sandbox exposes no shell, so cloning inside it was not possible.
Files were fetched with the browser's own `fetch` (raw.githubusercontent.com, CORS-open),
JSON-batched to `skills/_fetch/dump-*.json`, byte-length-verified and expanded by
`decode.py`; the staging directory was deleted after the clean run so it never reaches
the image. The two bulk collections were cloned and copied by the mock-builder teammate
at pinned commits in a scratch dir outside this repository.

## Teammate curated kit (merged 2026-10-17)

Source: teammate-assembled TsecBench-Agent-Kit.zip (752 MB), user-directed merge
with the security screen explicitly waived by the user. Contents and decisions:

- skills/kit/ - 5 unique skills (ai-ml-security, llm-prompt-injection,
  kubernetes-pentesting, reverse-engineer-anything, recon-and-methodology), no
  shipped scripts, frontmatter verified.
- The kit's six ctf-* skills REPLACED our same-name copies (same ljagiello
  upstream, identical file counts, curated content differs) - the team's curated
  versions take precedence.
- skills/kit/_methodology/ - 4 methodology docs (evidence ledger, O-H-V-D loop,
  toolchain methodology, GitHub reading route). Prompt material owned by the user.
- skills/payloadsallthethings/ - PayloadsAllTheThings snapshot (451 files,
  12.4 MB) as web payload reference.
- docker/tools/releases/ (gitignored, 620 MB) - Ghidra 12.1.4 / JADX 1.5.6 /
  radare2 6.2.4 release packages, SHA256-verified against the kit's SOURCES.sha256
  before the build; installed offline by the Dockerfile's bin-tools stage.
- Not merged: epositories/ reference agents (BLHX, Cruiser-Agent, Pozhen-Agent)
  kept outside the repo for reading; radare2 .deb skipped (apt radare2 already
  present); upstream sources for jadx/r2/pwntools/angr not needed (tools prebuilt).
- Pinned upstream commits: see epositories/manifest.json in the kit
  (BLHX aab0bedc, Pozhen b6d2e69a, Cruiser f8059bdf, jadx c4c45fde, ...).
- License notes: kit LICENSES-and-NOTICES.md, copied to docker/tools/.
