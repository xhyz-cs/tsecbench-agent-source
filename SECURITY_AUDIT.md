# Security Audit / 敏感信息审计

**Reviewed tree:** source-only staging copy of `tsecbench-src-gateway-fix`  
**Audit date:** 2026-10-19  
**Purpose:** pre-push credential and generated-artifact review for this private repository.

## Result / 结论

No active API key, benchmark token, GitHub token, AWS credential, bearer credential, JWT, complete PEM private key, `.env`, or private-key file was identified in the source/configuration reviewed. The live `.env` file is absent; `.env.example` remains and its `LLM_API_KEY` value is blank. Runtime credentials are documented as environment-injected.

The first pattern scan found credential-shaped strings used as training/test examples in the bundled skills. Before commit, 21 AWS-key-shaped examples, 16 JWT-shaped examples, 2 literal bearer-token examples, and 1 private-key canary prefix were replaced with explicit non-secret placeholders. A post-sanitization scan found no credential-like AWS/GitHub/OpenAI/Anthropic token, long bearer token, JWT, or complete PEM key block. PEM header syntax still appears in instructional examples (e.g. format descriptions); no private-key body/block is present.

The `.env.example` includes a model gateway/base URL and model name as configuration examples, not credentials. This repository is private as requested.

## Included/excluded material

- Included: source, prompts, skills, docs, tests, build scripts, Dockerfile, and the pinned Nikto archive with SHA-256 record.
- Excluded: prebuilt source bundle/archive, `.env`, Python bytecode/cache, `.tsecbench-state` runtime notes, and large optional Ghidra/JADX release archives. The optional archive checksums remain in `docker/tools/releases/SOURCES.sha256`.
- Test-created `__pycache__` and `.tsecbench-state` files are ignored by `.gitignore` and are not staged.

## Verification / 验证

- `python mcp/tsecbench_mcp.py --selftest` — PASS.
- `python -m unittest discover -s mcp/tests -q` — PASS, 136 tests.
- Docker helper suite — 12 of 16 tests passed when run natively (9 gateway/tool-release tests and 2 runtime-env tests passed, plus the static pre-init ordering test). Four tests that invoke `bash -c` failed because this Windows host resolves `bash.exe` to the WSL launcher and WSL reports a missing virtual-disk mount. This is an environment limitation; those shell tests were not validated here.
- Docker image build — not run; Docker CLI is not installed on this host.

This is a source-tree scan and local verification, not a guarantee that third-party archives or future commits contain no secrets. Re-run secret scanning after subsequent changes and before making the repository public.
