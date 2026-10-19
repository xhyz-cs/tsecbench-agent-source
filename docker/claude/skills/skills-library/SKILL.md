---
name: skills-library
description: An offline library of ~980 community security skills lives at /opt/tsecbench/skills-library/, mapped to the six TSecBench challenge classes. If a task touches web exploitation, evasion, binary work, cloud, or red-team pivoting, someone has probably already mapped that ground.
---

# Skills library

`/opt/tsecbench/skills-library/` holds community-written security skills
(~980 of them) in the sources' own category folders — `01-recon-osint`,
`03-exploit-development`, `04-reverse-engineering`, `09-web-security`,
`10-cloud-security`, and so on.

`INDEX.md` at the root is the map: it groups skills by TSecBench challenge class
(web, evasion, binary, exploit, cloud, multi-stage) and gives each one's path,
purpose, and whether it ships scripts.

A cheap way in, since the index is long:

```
Grep  pattern="SSRF|JWT|deserial|heap"  path="/opt/tsecbench/skills-library/INDEX.md"
```

then read the `SKILL.md` it points at and take whatever is useful. Scripts you
come across are worth a read first, like any code you didn't write.

If the library doesn't have what you need, your own approach is at least as good.
