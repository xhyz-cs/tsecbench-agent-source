#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
# =============================================================================
# Build the TSecBench hosted-mode image and export it for upload.
#
#   ./docker/build.sh                                    # full build + export, includes angr + z3
#   WITH_SYMBEX=0 ./docker/build.sh                    # smaller build without symbex (~0.4 GB less)
#   CLAUDE_CODE_VERSION=2.1.301 ./docker/build.sh        # pin a different release
#   ./docker/build.sh tsecbench-agent:v2 out.tar.gz      # custom tag / output
#
# Every Dockerfile ARG is passable as an environment variable (see the ARG table in
# docker/README.md): NODE_IMAGE, JRE_IMAGE, DEBIAN_MIRROR, DEBIAN_SECURITY_MIRROR,
# NPM_REGISTRY, PIP_INDEX, CLAUDE_CODE_VERSION, CHROME_DEVTOOLS_MCP_VERSION, WITH_SYMBEX.
#
# The upload artefact must stay under 3 GB (平台托管模式要求), so this fails loudly
# instead of letting you discover it in the upload queue.
# =============================================================================
set -euo pipefail

TAG="${1:-tsecbench-agent:latest}"
OUT="${2:-tsecbench-agent.tar.gz}"
MAX_BYTES=$((3 * 1024 * 1024 * 1024))   # 平台上限：3GB

cd "$(dirname "$0")/.."

command -v docker >/dev/null 2>&1 || { echo "docker not found in PATH" >&2; exit 1; }

# The platform sandbox is x86-64. Claude Code ships a native per-arch binary and the
# tool releases are amd64 - an arm64 build would start fine and die in the sandbox.
arch="$(uname -m)"
if [[ "$arch" != "x86_64" && "$arch" != "amd64" ]]; then
  echo "ERROR: host arch is $arch; the image must be linux/amd64." >&2
  echo "       On an arm64 box: docker build --platform linux/amd64 (slow, emulated)" >&2
  echo "       - or build on any x86_64 machine." >&2
  exit 1
fi
echo "host arch: $arch (x86-64 required by the platform sandbox)"

# Forward every documented ARG as --build-arg when the caller exported it.
ARGS=(--build-arg)
ARGS+=("CLAUDE_CODE_VERSION=${CLAUDE_CODE_VERSION:-2.1.301}")
ARGS+=(--build-arg)
ARGS+=("CHROME_DEVTOOLS_MCP_VERSION=${CHROME_DEVTOOLS_MCP_VERSION:-0.6.0}")
for name in NODE_IMAGE JRE_IMAGE DEBIAN_MIRROR DEBIAN_SECURITY_MIRROR NPM_REGISTRY PIP_INDEX WITH_SYMBEX; do
  if [[ -n "${!name:-}" ]]; then
    ARGS+=(--build-arg "${name}=${!name}")
  fi
done

echo "== building ${TAG} (claude-code ${CLAUDE_CODE_VERSION:-2.1.301}) =="

# Supply-chain gate: skills/ holds third-party content collected from the internet.
# The collector's audit produces INDEX.md; building without it ships unaudited skills.
if [[ ! -f "skills/INDEX.md" ]]; then
  echo "WARNING: skills/INDEX.md is missing — the skill audit has not completed." >&2
  echo "         Proceeding will bake UNAUDITED third-party skill content into the image." >&2
  echo "         Expected layout: skills/<skill-name>/SKILL.md (see skills/SOURCES.md)." >&2
fi

# Binary tools come from local release packages (teammate kit; SHA256-pinned in
# docker/tools/releases/SOURCES.sha256). Missing packages = no Ghidra/JADX in the
# image — the build still succeeds, the entrypoint probe reports the gap.
if [[ ! -f "docker/tools/releases/ghidra-12.1.4.zip" ]]; then
  echo "WARNING: docker/tools/releases/ghidra-12.1.4.zip missing — image ships WITHOUT Ghidra/JADX." >&2
  echo "         Place the release packages from the teammate kit there to enable them." >&2
fi

docker build -f docker/Dockerfile "${ARGS[@]}" -t "${TAG}" .

raw_bytes="$(docker image inspect "${TAG}" --format '{{.Size}}')"
printf 'image size (uncompressed): %s bytes\n' "${raw_bytes}"

echo "== exporting ${OUT} =="
docker save "${TAG}" | gzip > "${OUT}"

bytes="$(wc -c <"${OUT}")"
printf 'artefact: %s (%d bytes)\n' "${OUT}" "${bytes}"

if (( bytes > MAX_BYTES )); then
  echo "ERROR: artefact is $(awk -v b="${bytes}" 'BEGIN{printf "%.2f", b/1073741824}') GB, over the 3 GB upload limit." >&2
  echo "       usual suspects: chromium, the python stack, or Ghidra + JDK 25." >&2
  echo "       shrink it: move docker/tools/releases/ghidra-*.zip away and rebuild." >&2
  exit 1
fi

echo "== OK: under the 3 GB limit =="
echo "next: upload ${OUT} on 评测第 3 步「制作并上传 Docker 镜像」"
echo "      the container must auto-start solving — the entrypoint already does."
echo "      smoke-test first (local MCP checks only; no benchmark token or live task):"
echo "        docker run --rm -e TSEC_PREFLIGHT_ONLY=1 -e TSEC_REQUIRE_BENCH_ENV=0 \\"
echo "          -e LLM_API_BASE_URL=https://api.deepseek.com/anthropic \\"
echo "          -e LLM_API_KEY=preflight-dummy -e LLM_DEFAULT_MODEL=deepseek-flash \\"
echo "          tsecbench-agent:latest"
