# Documentation style guide

This guide defines how first-party prose in this repository is written. It applies to
maintained documentation: `README.md`, `README_CN.md`, `CONTRIBUTING.md`,
`DISCLAIMER.md`, `THIRD_PARTY_NOTICES.md`, `NOTICE`, `docs/`, component README files,
and the navigation/provenance files under `skills/`.

It does **not** apply to vendored third-party content under `skills/` (except the
first-party files `skills/INDEX.md`, `skills/SOURCES.md`, and `skills/audit-scan.json`),
which must remain verbatim under its upstream licenses. Historical records
(`AUDIT.md`, `PROGRESS.md`, `REVIEW.md`, `SECURITY_AUDIT.md`) are dated evidence and are
not retro-edited; corrections are appended, not substituted.

The rules below follow the Google developer documentation style guide, the Microsoft
Writing Style Guide, RFC 2119 for normative language, and standard Chinese technical
typography conventions.

## 1. Voice and tone

- Use the second person ("you") in instructions. Avoid "we" except when naming the
  maintainers as an accountable party.
- Use the active voice and name the actor: "The entrypoint writes the log", not "the
  log is written".
- State facts directly. Avoid metaphors, marketing language, exclamations, and
  subjective judgements ("powerful", "awesome", "瑞士军刀").
- Do not use contractions in normative or reference text ("do not", not "don't").
  Contractions are acceptable only inside quoted upstream text.
- Keep sentences short. One idea per sentence; one topic per paragraph.
- Do not pre-announce: write "Run the tests", not "This section will explain how to run
  the tests".

## 2. Normative language

Rules that constrain contributors or implementations use RFC 2119 keywords in
uppercase:

- **MUST / MUST NOT** — absolute requirement or prohibition.
- **SHOULD / SHOULD NOT** — recommended; deviations require a stated reason.
- **MAY** — genuinely optional.

Do not use these keywords for ordinary description.

## 3. Structure

- Each maintained document starts with a single H1 title and one paragraph stating its
  purpose and audience.
- Use sentence case for English headings: "Build and test", not "Build And Test".
- Use numbered lists for sequences and bulleted lists for unordered sets.
- One blank line around headings, lists, and code blocks.
- Give every link descriptive text. Do not use "here" or bare URLs as link text.
- Prefer tables for inventories (dependencies, licenses, configuration keys).

## 4. Terminology (project glossary)

Use these terms consistently in English and Chinese.

| English | Chinese | Meaning; do not use |
|---|---|---|
| repository | 仓库 | The Git repository. Not "repo" in prose (placeholders such as `<repository-root>` are allowed). |
| TSecBench Agent | TSecBench Agent | The product shipped by this repository. Always capitalized. Not "tsecbench agent". |
| agent / Agent | Agent | The evaluated program. Capitalize when referring to the product's Agent role; use lowercase only in code identifiers. |
| worker | worker | A Claude Code worker process started by `docker/fleet.py`. Not "Agent" when the process is meant. |
| image | 镜像 | The built container image. |
| skill | 技能 | A `SKILL.md` directory in the skill library. |
| skill library | 技能库 | The vendored collection under `skills/`. Not "skills library" or "skill-library". |
| challenge | 题目 / 挑战 | A benchmark task. Use "题目" in Chinese prose. |
| harness | 运行框架 / Harness | The platform's execution harness. |
| hosted mode | 托管模式 | The platform mode. Not "Hosted-mode" mid-sentence. |
| first-party | 第一方 | Content authored by this project. |
| third-party | 第三方 | Content owned by others. |
| maintainer | 维护者 | The project maintainers. |

Tag, command, and path names are always written in code font and are never translated.

## 5. English typography

- One space after punctuation; no space before punctuation.
- Serial comma in lists of three or more items.
- Dates in ISO 8601: `2026-10-20`. Do not write `Oct 20, 2026` in maintained docs.
- Percentages and units: a space between the number and the unit (`3 GB`, `30 s`),
  except for `%` (`50%`).
- Use em dashes sparingly and without surrounding spaces.
- Code identifiers, paths, commands, environment variables, and SPDX identifiers use
  code font: `TSEC_WORKERS`, `skills/pdf`.

## 6. Chinese typography

- Use full-width punctuation in Chinese sentences: `，。；：！？（）`.
- Use Chinese quotation marks `“”` for quoted Chinese text, `‘’` for nested quotes.
  Do not use ASCII `"` in Chinese prose. Book and law titles use `《》`.
- Put one space between Chinese characters and adjacent Latin letters, digits, or code
  spans: `使用 Claude Code 运行`, `共 3 GB`.
- Do not use spaces around full-width punctuation.
- Do not mix half-width and full-width punctuation in the same sentence.
- Quoted program output and fixed platform messages are reproduced verbatim, even if
  they use half-width punctuation; mark them as quoted text.

## 7. Licensing and attribution wording

- State the repository license as "Apache License 2.0" (not "Apache 2" or "ALv2") and
  link to `LICENSE`; attribution terms are in `NOTICE`.
- Third-party inventories live in `THIRD_PARTY_NOTICES.md`; license identifiers use SPDX
  short forms (`Apache-2.0`, `MIT`, `BSD-2-Clause`, `GPL-3.0-only`).
- New or changed third-party content MUST be mapped in `REUSE.toml` and pass
  `reuse lint`.
- Do not describe a third-party component as "free" or "open" without naming its
  license. `NOASSERTION` means the license is not confirmed; it is not a grant.

## 8. Security and legal wording

- Use "MUST NOT" for prohibitions that protect credentials or boundaries: "Do not print,
  save, or submit credentials".
- Refer to misuse as the responsibility of the actor: "The maintainers are not
  responsible for non-compliant third-party use", not "the tool could be misused".
- Legal documents follow `DISCLAIMER.md`; the Chinese text is authoritative. Do not
  paraphrase legal terms in other documents — link to `DISCLAIMER.md` instead.
- This guide is not legal advice.

## 9. Document classes

| Class | Files | Editing rule |
|---|---|---|
| Governance and legal | `LICENSE`, `NOTICE`, `DISCLAIMER.md`, `THIRD_PARTY_NOTICES.md`, `CONTRIBUTING.md`, `README*.md` | Maintained; edit freely under this guide |
| Reference documentation | `docs/`, `mcp/README.md`, `docker/README.md`, plugin README, `llms.txt` | Maintained; edit under this guide, preserving verified platform facts |
| Provenance records | `skills/INDEX.md`, `skills/SOURCES.md`, `skills/audit-scan.json` | Counts and findings are audit-time records; append corrections instead of rewriting |
| Historical records | `AUDIT.md`, `PROGRESS.md`, `REVIEW.md`, `SECURITY_AUDIT.md` | Do not rewrite; append dated corrections |
| Functional prompt text | `docker/claude/RUNBOOK.md`, `SYSTEM_APPEND.md`, `LOOP_PROMPT.md`, `plugin/**/commands/*.md`, `docker/claude/skills/**` | Treat as executable prompts. Do not change wording without a behavior review; register edits are out of scope |
| Quoted official text | `docs/agent-prompt.md` | Reproduce the platform's text verbatim; do not edit |
| Generated | `llms-full.txt` | Regenerate from source documents; do not hand-edit |
| Vendored third-party | everything else under `skills/` | Do not modify; governed by upstream licenses |

## 10. Review checklist

- [ ] H1 title and purpose paragraph present.
- [ ] Sentence-case English headings; consistent Chinese headings.
- [ ] No contractions, metaphors, exclamations, or subjective adjectives in maintained
      documents.
- [ ] Terminology matches section 4; code identifiers in code font.
- [ ] English dates are ISO 8601; Chinese punctuation is full-width.
- [ ] Normative rules use RFC 2119 keywords.
- [ ] Licensing statements match `LICENSE`, `NOTICE`, and `THIRD_PARTY_NOTICES.md`.
- [ ] `reuse lint` passes.
