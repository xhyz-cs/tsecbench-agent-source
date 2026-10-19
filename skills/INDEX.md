# Skills Index — TSecBench hosted-mode container

Collected from public GitHub sources on 2026-10-16/17, audited by the skill-collector
agent. Provenance, pinned commits, and the security-screening log: see `SOURCES.md`.

## Audit summary (2026-10-17)

- **Skill directories:** 136 curated top-level installed (+ 6 nested sub-skills under
  `techstack-identification/`), plus the two user-directed collections: **818** dirs from
  `mukul975/Anthropic-Cybersecurity-Skills` and **22** from
  `Masriyan/Claude-Code-CyberSecurity-Skill` — **982 SKILL.md total**, ~5,470 files.
- **Frontmatter check:** 982/982 have `name:` AND `description:`. `name` == directory
  name verified by construction (curated) and by sampling (bulk). `exploit-regression`
  (a no-YAML source format) carries frontmatter synthesized from the author's own
  metadata; see SOURCES.md.
- **Scripts:** every shipped script is listed below with a one-line description.
  20 curated scripts read in full; bulk-collection scripts (mukul975 `agent.py`/`process.py`,
  Masriyan testers) read by representative sample per family + primitive scan
  (requests/socket/subprocess/eval/base64): all operator-targeted tooling, no
  author-controlled endpoints, no obfuscated blobs (the single 400+-char base64-like
  string is the RFC 3526 MODP prime constant in the ZKP skill).
- **Injection/exfil scan:** all hits reviewed in context — prompt-injection phrases exist
  only inside LLM-testing payload corpora (the payloads those skills test *for*);
  webhook/interactsh/ngrok references are OOB-callback testing docs with placeholder IDs.
  No data-exfiltration or hidden-instruction content found. Rejections: none at file
  level; see SOURCES.md for whole-source exclusions.
- **Category coverage** (TSecBench v1 question mix): all six categories have multiple
  independent sources — Web (70+), Adversarial evasion (12+), Binary/RE (30+),
  Exploitation (40+), Cloud (14), Multi-stage (12). No category needed the
  "no ready-made skills found" marker.

Legend: WEB web-vuln · EVASION adversarial evasion · BIN binary/RE · EXPL exploitation ·
CLOUD cloud · MULTI multi-stage · AD Active Directory · PASSWD passwords · CRYPTO crypto ·
FORENSICS forensics/stego · OSINT/RECON recon · LLM LLM security · MOBILE mobile ·
METH methodology/reporting/CTF-workflow · NET network · API api

---

## 1. transilienceai/communitytools @ 95fdc12 (22 skills)

| Skill | Categories | Purpose | Files | Scripts |
|---|---|---|---|---|
| reconnaissance | RECON,WEB | subdomain/port/endpoint/API attack-surface mapping | 10 | no |
| osint | OSINT,RECON | repo enumeration, secret scanning, git-history analysis | 2 | no |
| techstack-identification | RECON | passive tech-stack inference (root + 6 nested sub-skills) | 13 | no |
| patt-fetcher | WEB,EXPL | on-demand PayloadsAllTheThings payload extraction | 1 | no |
| cve-poc-generator | EXPL,METH | CVE research → safe Python PoC + vulnerability report | 2 | no |
| source-code-scanning | METH | SAST, dependency CVEs, secret & malicious-code detection | 7 | no |
| essential-tools | METH,WEB | Burp/Playwright usage, binary-analysis quickstart, reporting standards | 9 | no |
| social-engineering | METH | phishing/pretexting/vishing/physical methodology | 13 | no |
| mobile-security | MOBILE | Android+iOS VAPT (MASVS/MASTG), Frida, pinning/root bypass | 11 | no |
| ai-threat-testing | LLM | OWASP LLM Top 10 attack & eval scenarios | 26 | no |
| dfir | FORENSICS | forensic "Sherlock" analysis: network/memory/log/AD-attack detection | 34 | no |
| api-security | WEB,API | GraphQL/REST/WebSocket/Web-LLM testing | 43 | no |
| infrastructure | NET,RECON | port scanning, DNS, SMB/NetBIOS, MITM, ICS, UPnP/IoT | 50 | yes — `tools/zmtp_probe.py`: read-only ZMTP/ZeroMQ handshake prober (operator-specified host) |
| injection | WEB,EXPL | SQL/NoSQL/OS-command/SSTI/XXE/LDAP injection | 46 | no |
| web-app-logic | WEB | race conditions, IDOR, mass assignment, cache poisoning, logic bugs | 56 | no |
| client-side | WEB | XSS (R/S/DOM), CSRF, clickjacking, CORS, prototype pollution | 45 | no |
| server-side | WEB,EXPL | SSRF, request smuggling, traversal, file upload, deserialization, host header | 50 | yes — `.../deserialization/tools/aspnet_viewstate_build.py`: builds signed ASP.NET ViewState RCE payload from operator-supplied keys (writes /tmp) |
| authentication | WEB,PASSWD | auth bypass, JWT, OAuth, password attacks, 2FA bypass | 66 | yes — `tools/credential_manager.py` (local test-credential store), `tools/password_generator.py` (policy-compliant password generation), `reference/ntlm-http-listener.py` (local NetNTLMv2 capture listener; binds only when invoked) |
| system | AD,BIN,EXPL,MULTI | Active Directory, Linux+Windows privesc, exploit development | 116 | no |
| reverse-engineering | BIN | static RE of ELF/PE, custom-VM bytecode, MBA deobfuscation | 26 | no |
| pentest-engagement | METH,MULTI | scoped end-to-end pentest workflow (web + network modes) | 2 | no |
| authenticated-session-acquisition | WEB,METH | acquire sessions through MFA/OTP for post-auth testing | 2 | no |

## 2. ljagiello/ctf-skills @ c957f4f (10 skills)

| Skill | Categories | Purpose | Files | Scripts |
|---|---|---|---|---|
| ctf-web | WEB,CTF | CTF web exploitation technique library | 25 | yes — `scripts/async_fuzz.py`: Intruder-style FUZZ fuzzer (operator `--url`, rate-limit aware) |
| ctf-pwn | BIN,CTF | binary pwn technique library | 25 | yes — 5 pwntools exploit templates: fmtstr suite, ret2libc two-stage, seccomp ORW generator, shellcraft variants, SROP execve (all target operator-specified binary/host) |
| ctf-crypto | CRYPTO,CTF | RSA/AES/ECC/padding attack playbook | 20 | no |
| ctf-reverse | BIN,CTF | static/dynamic RE, obfuscation, decompilation | 22 | no |
| ctf-forensics | FORENSICS,CTF | disk/memory/network/stego forensics | 15 | no |
| ctf-misc | CTF,METH | pyjails, encodings, RF/SDR, sandbox escapes | 13 | no |
| ctf-osint | OSINT,CTF | CTF-flavored OSINT techniques | 5 | no |
| ctf-malware | BIN,CTF | malware analysis: RATs, C2 protocols, unpacking | 5 | no |
| solve-challenge | CTF,METH | orchestrator: route a challenge to category skills | 1 | no |
| ctf-writeup | CTF,METH | standardized writeup generation | 1 | no |

## 3. trilwu/secskills @ ca53957 (38 skills, single-file markdown)

Source paths: `secskills-offense/skills/<name>/` unless noted `core:` (= `secskills-core/skills/`).

| Skill | Categories | Purpose | Files | Scripts |
|---|---|---|---|---|
| escalating-linux-privileges | MULTI,EXPL | SUID/capabilities/sudo/cron/kernel privesc | 3 | no |
| escalating-windows-privileges | MULTI,EXPL | services, DLL hijack, tokens, potato family | 2 | no |
| cracking-passwords | PASSWD | hashcat/john judgment, wordlists, spraying | 2 | no |
| exploiting-cloud-platforms | CLOUD | AWS/Azure/GCP enumeration → abuse paths | 2 | no |
| exploiting-containers | CLOUD,MULTI | Docker/Kubernetes escape and misconfig | 1 | no |
| abusing-ci-cd-oidc | CLOUD,MULTI | CI/CD OIDC trust abuse (GitHub Actions/GitLab/Jenkins) | 1 | no |
| reporting-security-findings (core) | METH | finding quality and report structure | 1 | no |
| analyzing-binaries (core) | BIN | RE triage, Ghidra/radare2/IDA, instrumentation | 1 | no |
| analyzing-dotnet-assemblies (core) | BIN | .NET RE (dnSpy/ILSpy) | 1 | no |
| analyzing-firmware-images (core) | BIN | firmware unpack/analysis (binwalk, UEFI) | 1 | no |
| analyzing-go-binaries (core) | BIN | Go binary RE | 1 | no |
| analyzing-ios-binaries (core) | BIN | Mach-O / iOS RE | 1 | no |
| analyzing-macos-binaries (core) | BIN | macOS binary RE | 1 | no |
| analyzing-rust-binaries (core) | BIN | Rust binary RE | 1 | no |
| devirtualizing-vm-protected-code (core) | BIN | custom-VM bytecode devirtualization | 1 | no |
| diffing-binary-patches (core) | BIN | patch/binary diffing | 1 | no |
| unpacking-protected-binaries (core) | BIN | packer identification + unpacking | 1 | no |
| reversing-network-protocols (core) | BIN | unknown-protocol RE | 1 | no |
| escaping-hardened-containers | EVASION,CLOUD | seccomp/capability-dropped container escapes | 1 | no |
| establishing-persistence | MULTI,EVASION | persistence tradecraft + cleanup register | 2 | no |
| transferring-files | MULTI,EVASION | file-transfer tradecraft | 2 | no |
| recognizing-deception | METH,EVASION | honeypot/canary/decoy recognition | 1 | no |
| exploiting-deserialization | EXPL | deserialization gadget chains | 1 | no |
| exploiting-memory-corruption | EXPL,BIN | memory-corruption exploitation | 1 | no |
| exploiting-ssrf | EXPL,WEB | SSRF exploitation judgment | 1 | no |
| exploiting-xxe | EXPL,WEB | XXE exploitation | 1 | no |
| attacking-jwt | WEB,EXPL | JWT attack set | 1 | no |
| attacking-graphql | WEB,EXPL | GraphQL attack set | 1 | no |
| attacking-oauth-oidc | WEB,EXPL | OAuth/OIDC attack set | 1 | no |
| attacking-saml | WEB,EXPL | SAML attack set | 1 | no |
| attacking-eks-gke-aks | CLOUD | managed-Kubernetes attack paths | 1 | no |
| attacking-entra-id | CLOUD | Entra ID / Azure AD attacks | 1 | no |
| attacking-kerberos-delegation | AD,MULTI | unconstrained/constrained/RBCD delegation abuse | 1 | no |
| attacking-serverless | CLOUD,EXPL | serverless function attacks | 1 | no |
| testing-web-applications | WEB | end-to-end web testing workflow | 1 | no |
| testing-apis | API,WEB | API testing workflow | 2 | no |
| enumerating-network-services | RECON,MULTI | service enumeration and exploitation | 2 | no |
| performing-reconnaissance | RECON,OSINT | OSINT, subdomain enum, surface mapping | 2 | no |

## 4. ADScanPro/Claude-AD @ 73efec5 (2 skills)

| Skill | Categories | Purpose | Files | Scripts |
|---|---|---|---|---|
| kerberos-attacks | AD | Kerberoasting, AS-REP, delegation attacks | 1 | no |
| adcs-attacks | AD | ADCS ESC1–ESC17 with certipy | 1 | no |

## 5. anthropics/skills @ dbd4588 (1 skill)

| Skill | Categories | Purpose | Files | Scripts |
|---|---|---|---|---|
| pdf | METH,CTF | PDF reading/form-filling/annotation (report output; PDF-based CTF tasks) | 12 | yes — 8 local scripts: pypdf/pdfplumber/pdf2image/PIL form extraction, filling, validation-image generation; no network |

## 6. SnailSploit/Claude-Red @ a8de813 (35 skills, single-file markdown)

Source paths: `Skills/<domain>/<name>/SKILL.md`. All 35 installed. 17 arrived with valid
YAML frontmatter; 18 used a non-YAML metadata format and had frontmatter added
mechanically from the files' own Metadata/Description sections (body verbatim, provenance
note inside each file). `exploit-regression` = source `Skills/exploit-dev/offensive-exploit-development`.

| Skill | Categories | Purpose | Files | Scripts |
|---|---|---|---|---|
| offensive-sqli | WEB | SQLi testing checklist | 1 | no |
| offensive-ssti | WEB | SSTI testing checklist | 1 | no |
| offensive-xss | WEB | XSS checklist (stored/reflected/DOM/blind, CSP bypass) | 1 | no |
| offensive-xxe | WEB,EXPL | XXE checklist | 1 | no |
| offensive-idor | WEB | IDOR checklist | 1 | no |
| offensive-open-redirect | WEB | open redirect checklist | 1 | no |
| offensive-parameter-pollution | WEB | HPP checklist | 1 | no |
| offensive-race-condition | WEB | race condition checklist | 1 | no |
| offensive-request-smuggling | WEB | HTTP request smuggling checklist | 1 | no |
| offensive-ssrf | WEB | SSRF checklist | 1 | no |
| offensive-rce | WEB,EXPL | RCE checklist | 1 | no |
| offensive-file-upload | WEB | file-upload bypass checklist | 1 | no |
| offensive-business-logic | WEB | business-logic testing | 1 | no |
| offensive-graphql | WEB,API | GraphQL testing | 1 | no |
| offensive-deserialization | WEB,EXPL | deserialization checklist | 1 | no |
| offensive-waf-bypass | WEB,EVASION | WAF bypass playbook | 1 | no |
| offensive-edr-evasion | EVASION | EDR/AV evasion methodology | 1 | no |
| offensive-anti-forensics | EVASION | anti-forensics (timestomping, log tampering) | 1 | no |
| offensive-advanced-redteam | MULTI,EVASION | advanced red-team tradecraft | 1 | no |
| offensive-data-exfiltration | MULTI,EVASION | exfiltration methodology | 1 | no |
| offensive-lateral-movement | MULTI | lateral movement playbook | 1 | no |
| offensive-persistence | MULTI | persistence playbook | 1 | no |
| offensive-c2-frameworks | MULTI | C2 framework tradecraft | 1 | no |
| offensive-initial-access | MULTI | initial access playbook | 1 | no |
| offensive-cloud | CLOUD | AWS/Azure/GCP attack methodology | 1 | no |
| offensive-container-escape | CLOUD,MULTI | container escape playbook | 1 | no |
| offensive-k8s-attacks | CLOUD | Kubernetes attack playbook | 1 | no |
| exploit-regression (src: offensive-exploit-development) | BIN,EXPL | exploit development operational guide | 1 | no |
| offensive-exploit-dev-course | BIN | exploit-dev course roadmap | 1 | no |
| offensive-mitigations | BIN | exploit mitigations reference | 1 | no |
| offensive-toctou | BIN,EXPL | TOCTOU race conditions | 1 | no |
| offensive-bug-identification | BIN | crash→bug triage | 1 | no |
| offensive-fuzzing | BIN | fuzzing fundamentals | 1 | no |
| offensive-fuzzing-course | BIN | fuzzing course | 1 | no |
| offensive-vuln-classes | BIN | vulnerability class catalog | 1 | no |

## 7. securityfortech/hacking-skills @ 0aa49b4 (28 skills, single-file markdown)

Source paths: `skills/web/<category>/<name>/SKILL.md`. All: Categories WEB, 1 file, no scripts.

| Skill (source category) | Purpose |
|---|---|
| auth-bypass (auth) | authentication bypass patterns |
| default-credentials (auth) | default/weak credential testing |
| jwt-misconfig (auth) | JWT misconfiguration testing |
| password-reset-flaws (auth) | password-reset logic flaws |
| authz-bypass (authz) | authorization bypass patterns |
| bola-idor (authz) | BOLA/IDOR testing |
| mass-assignment (authz) | mass-assignment testing |
| path-traversal (authz) | path traversal testing |
| clickjacking (client-side) | clickjacking testing |
| cors-misconfig (client-side) | CORS misconfiguration |
| cspt (client-side) | client-side path traversal |
| csrf (client-side) | CSRF testing |
| dom-xss (client-side) | DOM XSS sinks and testing |
| open-redirect (client-side) | open redirect testing |
| cmd-injection (injection) | command injection testing |
| http-request-smuggling (injection) | request smuggling testing |
| sql-injection (injection) | SQLi testing |
| ssrf (injection) | SSRF testing |
| ssti (injection) | SSTI testing |
| xss-reflected (injection) | reflected XSS testing |
| xss-stored (injection) | stored XSS testing |
| xxe (injection) | XXE testing |
| business-logic-flaws (logic) | business logic flaw hunting |
| graphql-idor-via-introspection-leak (logic) | GraphQL introspection → IDOR |
| insecure-file-upload (logic) | file upload exploitation |
| web-fingerprinting (recon) | web stack fingerprinting |
| cookie-attacks (session) | cookie attack techniques |
| session-fixation (session) | session fixation testing |

## 8. mukul975/Anthropic-Cybersecurity-Skills @ 54a7988 (818 skills, user-directed)

Every directory under upstream `skills/` (each contains `SKILL.md` + `LICENSE` + 1–3
`references/*.md` + 1–2 `scripts/*.py`). Purpose below is mechanically derived from the
directory name; full description lives in each `SKILL.md` (frontmatter validated).
**Every skill in this collection: has scripts = YES — `scripts/agent.py` (LLM-API-driven
agent scaffold, operator-specified target/endpoint via args/env) and, where present,
`scripts/process.py` (task-specific automation, e.g. urlscan.io submission in
`analyzing-malicious-url-with-urlscan`).** Sampled and primitive-scanned; no
author-controlled endpoints found. ~5–8 files each, ~30.7 MB total.

Offensive/red-team cluster (Web/Exploitation/AD/Cloud/Multi-stage relevance):
bypassing-authentication-with-forced-browsing; coercing-authentication-with-coercer-petitpotam;
conducting-domain-persistence-with-dcsync; conducting-full-scope-red-team-engagement;
conducting-internal-network-penetration-test; conducting-internal-reconnaissance-with-bloodhound-ce;
conducting-man-in-the-middle-attack-simulation; conducting-pass-the-ticket-attack;
conducting-social-engineering-penetration-test; conducting-wireless-network-penetration-test;
emulating-cloud-attacks-with-stratus-red-team; enumerating-cloud-with-cloudfox;
escaping-containers-to-host; executing-active-directory-attack-simulation;
exploiting-active-directory-certificate-services-esc1; exploiting-active-directory-with-bloodhound;
exploiting-adcs-with-certipy; exploiting-api-injection-vulnerabilities; exploiting-aws-with-pacu;
exploiting-bgp-hijacking-vulnerabilities; exploiting-broken-function-level-authorization;
exploiting-broken-link-hijacking; exploiting-constrained-delegation-abuse;
exploiting-deeplink-vulnerabilities; exploiting-excessive-data-exposure-in-api;
exploiting-http-request-smuggling; exploiting-idor-vulnerabilities;
exploiting-insecure-data-storage-in-mobile; exploiting-insecure-deserialization;
exploiting-ipv6-vulnerabilities; exploiting-jwt-algorithm-confusion-attack;
exploiting-kerberoasting-with-impacket; exploiting-mass-assignment-in-rest-apis;
exploiting-ms17-010-eternalblue-vulnerability; exploiting-nopac-cve-2021-42278-42287;
exploiting-nosql-injection-vulnerabilities; exploiting-oauth-misconfiguration;
exploiting-prototype-pollution-in-javascript; exploiting-race-condition-vulnerabilities;
exploiting-server-side-request-forgery; exploiting-smb-vulnerabilities-with-metasploit;
exploiting-sql-injection-vulnerabilities; exploiting-sql-injection-with-sqlmap;
exploiting-template-injection-vulnerabilities; exploiting-type-juggling-vulnerabilities;
exploiting-vulnerabilities-with-metasploit-framework; exploiting-websocket-vulnerabilities;
exploiting-zerologon-vulnerability-cve-2020-1472; attacking-entra-id-with-roadtools;
attacking-oauth-with-device-code-phishing; relaying-ntlm-for-adcs-esc8;
moving-laterally-with-netexec; post-exploiting-microsoft-graph-with-graphrunner;
operating-havoc-c2; operating-sliver-c2; building-c2-infrastructure-with-sliver-framework;
building-c2-redirector-infrastructure; building-red-team-c2-infrastructure-with-havoc;
performing-arp-spoofing-attack-simulation; performing-bandwidth-throttling-attack-simulation;
performing-clickjacking-attack-test; performing-csrf-attack-simulation;
performing-vlan-hopping-attack; performing-ssl-stripping-attack; performing-packet-injection-attack;
performing-graphql-depth-limit-attack; performing-graphql-introspection-attack;
performing-graphql-security-assessment; performing-second-order-sql-injection;
performing-web-cache-deception-attack; performing-web-cache-poisoning-attack;
performing-web-application-firewall-bypass; performing-content-security-policy-bypass;
performing-api-rate-limiting-bypass; performing-blind-ssrf-exploitation;
performing-ssrf-vulnerability-exploitation; performing-directory-traversal-testing;
performing-http-parameter-pollution-attack; performing-hash-cracking-with-hashcat;
performing-kerberoasting-attack; performing-jwt-none-algorithm-attack;
performing-binary-exploitation-analysis; performing-privilege-escalation-assessment;
performing-privilege-escalation-on-linux; performing-credential-access-with-lazagne;
extracting-credentials-from-memory-dump; performing-active-directory-bloodhound-analysis;
performing-active-directory-penetration-test; performing-active-directory-forest-trust-attack;
performing-active-directory-vulnerability-assessment; mapping-attack-paths-with-bloodhound-ce;
conducting-external-reconnaissance-with-osint; conducting-external-network-penetration-test;
conducting-network-penetration-test; conducting-mobile-app-penetration-test;
conducting-cloud-penetration-testing; performing-cloud-penetration-testing-with-pacu;
performing-aws-privilege-escalation-assessment; performing-aws-account-enumeration-with-scout-suite;
performing-gcp-penetration-testing-with-gcpbucketbrute; performing-gcp-security-assessment-with-forseti;
performing-kubernetes-penetration-testing; performing-subdomain-enumeration-with-subfinder;
performing-dns-enumeration-and-zone-transfer; scanning-network-with-nmap-advanced;
performing-api-fuzzing-with-restler; performing-api-security-testing-with-postman;
performing-fuzzing-with-aflplusplus; performing-firmware-extraction-with-binwalk;
performing-firmware-malware-analysis; performing-thick-client-application-penetration-test;
performing-soap-web-service-security-testing; performing-web-application-penetration-test;
performing-web-application-scanning-with-nikto; performing-web-application-vulnerability-triage;
performing-security-headers-audit; performing-serverless-function-security-review;
performing-ios-app-security-assessment; performing-android-app-static-analysis-with-mobsf;
performing-dynamic-analysis-of-android-app; performing-mobile-app-certificate-pinning-bypass;
intercepting-mobile-traffic-with-burpsuite; testing-android-intents-for-vulnerabilities;
testing-mobile-api-authentication; exploiting-deeplink-vulnerabilities;
reverse-engineering-android-malware-with-jadx; reverse-engineering-dotnet-malware-with-dnspy;
reverse-engineering-ios-app-with-frida; reverse-engineering-malware-with-ghidra;
reverse-engineering-ransomware-encryption-routine; reverse-engineering-rust-malware;
analyzing-golang-malware-with-ghidra; analyzing-linux-elf-malware; analyzing-packed-malware-with-upx-unpacker;
analyzing-malware-sandbox-evasion-techniques; analyzing-heap-spray-exploitation;
analyzing-ethereum-smart-contract-vulnerabilities; auditing-foundry-smart-contract-security;
performing-steganography-detection; performing-initial-access-with-evilginx3;
performing-red-team-with-covenant; performing-red-team-phishing-with-gophish;
performing-phishing-simulation-with-gophish; executing-phishing-simulation-campaign;
conducting-spearphishing-simulation-campaign; conducting-social-engineering-pretext-call;
performing-supply-chain-attack-simulation; performing-physical-intrusion-assessment;
performing-adversary-in-the-middle-phishing-detection (defensive-phishing focus).

The remaining ~700 directories are defensive/ops coverage (detection engineering,
DFIR, threat hunting, cloud/K8s hardening & auditing, GRC/compliance, zero-trust,
SOC/SIEM, OT/ICS, malware analysis, TI) — installed per the user's "every complete
skill directory" instruction; the fleet coordinator should treat the `detecting-*`,
`implementing-*`, `configuring-*`, `hardening-*`, `building-*`, `hunting-*`,
`triaging-*`, `auditing-*`, `performing-*-assessment/audit/review` families as
blue-team reference material.

## 9. Masriyan/Claude-Code-CyberSecurity-Skill @ a3be55a (22 skills, user-directed)

Source paths: `skills/<NN-name>/`. Each: SKILL.md + references + 1–4 scripts.

| Skill | Categories | Purpose | Files | Scripts |
|---|---|---|---|---|
| 01-recon-osint | RECON,OSINT | recon & OSINT methodology | 6 | yes — recon helper scripts |
| 02-vulnerability-scanner | WEB,METH | dependency/CVE/config scanning workflows | 5 | yes |
| 03-exploit-development | EXPL,BIN | PoC development, payload crafting, shellcode analysis | 3 | yes — `payload_generator.py` (local payload encoder/crafter) |
| 04-reverse-engineering | BIN | disassembly/decompilation methodology | 3 | yes |
| 05-malware-analysis | BIN | malware triage & analysis | 4 | yes |
| 06-threat-hunting | METH | hypothesis-driven hunting | 4 | yes |
| 07-incident-response | METH | IR playbooks, evidence collection, timelines | 4 | yes |
| 08-network-security | NET | traffic analysis, PCAP, IDS/IPS rules | 3 | yes |
| 09-web-security | WEB | OWASP Top 10 testing, injection, API security | 4 | yes — `api_security_tester.py` (operator-specified target) |
| 10-cloud-security | CLOUD | AWS/Azure/GCP auditing, container/K8s hardening | 4 | yes — `cloud_auditor.py` (posture checks) |
| 11-csoc-automation | METH | SOC alert triage/playbook automation | 4 | yes |
| 12-log-analysis | METH | log parsing, anomaly detection, Sigma rules | 4 | yes |
| 13-crypto-analysis | CRYPTO | TLS auditing, cipher/hash identification | 3 | yes |
| 14-red-team-ops | MULTI | engagement planning, C2 architecture | 3 | yes |
| 15-blue-team-defense | METH | hardening, detection engineering, baselines | 3 | yes — `hardening_checker.py` |
| 16-ai-llm-security | LLM | prompt-injection/jailbreak testing harness | 4 | yes — `prompt_injection_tester.py` (sends payload corpus to operator-specified endpoint; includes refusal-judge) |
| 17-mobile-security | MOBILE | mobile app security testing | 3 | yes |
| 18-ot-ics-security | NET | OT/ICS security assessment | 3 | yes |
| 19-grc-compliance | METH | GRC/risk assessment workflows | 4 | yes |
| 20-supply-chain-security | METH | supply-chain auditing (SBOM, deps) | 3 | yes |
| 21-threat-intelligence | METH | TI processing/enrichment | 3 | yes — `cti_processor.py` |
| 22-purple-team | METH | attack simulation vs detection validation | 3 | yes |

Script descriptions for Masriyan above are from representative reads (5 of 60 scripts)
plus per-file name inspection; the family is uniform (argparse CLI, operator-supplied
target, no hardcoded endpoints).

---

## Notes for the fleet coordinator

- Mount per task, never all at once (this set is ~45 MB / ~5,400 files).
- `mukul975` `scripts/agent.py|process.py` are tool-scaffolds the agent may run;
  if the bake wants a leaner image, excluding all `scripts/` dirs of section 8 is a
  documented, reversible choice (INDEX rows stay valid; skills remain markdown-complete).
- `techstack-identification/` contains 6 nested sub-skills (backend/correlation/frontend/
  infra/osint/security) — Claude Code discovers them independently.
- `offensive-*` (SnailSploit) and `sft` single-file skills are checklists; the
  communitytools/ctf skills are deep reference libraries — prefer the deep ones first.

## Teammate curated kit (2026-10-17)

| Skill | Class | Purpose | Path | Scripts |
|---|---|---|---|---|
| `ai-ml-security` | web | AI/ML attack playbook: pickle RCE, model poisoning, agent risks | `kit/ai-ml-security/` | none |
| `llm-prompt-injection` | web | Prompt-injection technique set | `kit/llm-prompt-injection/` | none |
| `kubernetes-pentesting` | cloud | Kubernetes pentest methodology | `kit/kubernetes-pentesting/` | none |
| `reverse-engineer-anything` | binary | RE routing method. The upstream REA MCP is not present in the sandbox - route to ghidra-headless / jadx / r2 instead | `kit/reverse-engineer-anything/` | none |
| `recon-and-methodology` | methodology | Recon routing + evidence ledger + O-H-V-D loop | `kit/recon-and-methodology/` | none |

Reference material (plain files, not SKILL.md):

- `payloadsallthethings/` - PayloadsAllTheThings snapshot (web payload and technique library)
- `kit/_methodology/` - evidence-ledger template, O-H-V-D loop, toolchain methodology,
  GitHub reading route (prompt material owned by the user)

The six `ctf-*` skills shipped in the same kit replaced the earlier same-name copies
identical file counts, different curated content; see SOURCES.md.
