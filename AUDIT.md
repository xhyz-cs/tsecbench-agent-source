# TSecBench competition image: source audit and changes

## Scope and result

Reviewed the container entrypoint, Claude Code hooks/configuration, fleet coordinator, MCP platform client, model gateway URL rewriting, Docker build context, documentation link checker, and the customized run prompts. Fixed the reproducible source issues listed below. The build context excludes `.env`, `.env.*`, local files, ZIPs, and Python bytecode; no model API key or benchmark token is included in the source changes.

## Findings fixed

| Severity | Location | Finding | Change and verification |
|---|---|---|---|
| High | `mcp/tsecbench_mcp.py` (`base_url`, `http_json`) | The MCP client sent `BENCHMARK_TOKEN` to whatever host `BENCHMARK_BASE_URL` named and followed redirects. A bad runtime URL or redirect could disclose the token. | Restrict public platform requests to `https://tsecbench.zc.tencent.com` (local HTTP test hosts only); reject userinfo/query/fragment and refuse redirects. Added regression tests for host validation and redirect refusal. |
| High | `docker/tsec_gw.py` | Gateway rewriting accepted arbitrary model API hosts, while the API key is passed to Claude Code as an authorization credential. | Enforce the documented model-provider host/path allowlist, require HTTPS for public endpoints and HTTP only for valid gateway endpoints, and reject URL userinfo/fragments. DeepSeek's `/anthropic` endpoint is accepted. Five gateway regression tests pass. |
| Medium | `docker/entrypoint.sh` | An environment override of `CLAUDE_CONFIG_DIR` was recursively deleted by `rm -rf`; a bad value could erase unrelated container paths. | Fix work/config directories at `/work` and `/work/.claude`; fail closed on conflicting overrides. Bash syntax check passes. |
| Medium | `docker/fleet.py` | API-provided `unique_code` was interpolated into a shell-agent prompt and a log filename without validation, permitting prompt/log-path injection if malformed. The worker instructions were also Chinese despite the requested EN-US prompts. | Validate IDs against a bounded safe identifier pattern before prompt/file use; encode the identifier as JSON data; rewrite the worker-specific instructions in English. |
| Low | `build/check-links.mjs` | Link validation was pinned to a developer's `D:/tmp/...` checkout and reported all docs missing elsewhere. | Derive repository root from the script's own path. Baseline fails with five `MISSING DOC` results; modified checker scans all five docs and passes. |

## Remaining deployment risk

## Accepted execution design

Running as root with `--dangerously-skip-permissions` and the wildcard auto-allow hook is intentional for this unattended, disposable benchmark sandbox; it is not classified as a source bug and was not changed. The benchmark container is the isolation boundary. Keep the platform's disposable-container model and avoid host mounts/host credentials; no prompt change is treated as a substitute for the sandbox.

## Skill-tree integrity check

Verified the original `tsecbench-src.zip` CRCs and compared extracted skill file SHA-256 values against the archive. The source ZIP SHA-256 is `b64cb59b4123a30781d403bb38ecff417bceedbf82bf7d96fdcaa842e8ae9090`; the ZIP contains 9,171 entries and `testzip()` returned `PASS`. It contains 5,904 skill files; 5,902 extracted files match byte-for-byte, with no modified or extra skill files. Two files are absent from the extraction: `skills/archive.py` (a build-time curator with destructive `apply` behavior) and `skills/payloadsallthethings/Upload Insecure Files/Extension ASP/shell.asp` (an executable ASP webshell sample). They were not reintroduced into the competition image. `.dockerignore` explicitly excludes both paths so an intact re-extraction cannot silently package either file.

## Prompt branch

`docker/claude/RUNBOOK.md`, `docker/claude/LOOP_PROMPT.md`, and `docker/claude/SYSTEM_APPEND.md` are now tailored in English for this platform's actual MCP/state lifecycle. The campaign objective remains active across turns; the Stop hook continues intermediate work, while task completion/`/work/state/STOP` ends the loop. The prompts bound work to the assigned challenge and require evidence-backed flags. The runbook and loop are each below 4,000 characters.

`.env.example` now uses the supplied DeepSeek Anthropic-compatible base path and `deepseek-flash` model with `LLM_API_TYPE=anthropic-messages`; the key field remains blank for runtime injection and no credential is baked into the source.

## Test and build status

- Baseline MCP suite: 134 tests passed; baseline MCP self-test and 14 keep-working hook tests passed.
- Baseline link checker: failed because of its hard-coded external checkout path (five missing-doc errors).
- Modified MCP suite: 136 tests passed; modified MCP self-test passed; 14 keep-working hook tests passed; local mock start → ready → close E2E passed.
- Modified gateway tests: 5 passed; DeepSeek URL conversion produced `http://api.deepseek.com.tsecbench.gw/anthropic`.
- Static checks: 13 Python application modules compiled in memory, 4 JS/MJS files passed `node --check`, 1 Docker JSON config parsed, and `docker/entrypoint.sh` passed `bash -n`.
- **Docker image build not run successfully:** this host has no Docker, Podman, Buildah, or Nerdctl executable/engine. `docker build -f docker/Dockerfile -t tsecbench:competition .` exits because the `docker` command is unavailable. No image artifact is claimed.
- Live benchmark/VPN E2E intentionally remains pending until the image can be built and the user supplies the time-limited target configuration after that build.
