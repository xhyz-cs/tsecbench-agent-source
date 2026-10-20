# syntax=docker.m.daocloud.io/docker/dockerfile:1
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
# =============================================================================
# TSecBench hosted-mode (托管模式) agent image — harness: Claude Code
#
# ONE-COMMAND BUILD (from the repo root):
#
#     docker build -f docker/Dockerfile -t tsecbench-agent:latest .
#     # or:  ./docker/build.sh          (builds AND exports agent.tar.gz, checks 3 GB)
#
# All package sources default to CN mirrors so a build in mainland China is fast.
# Override any of them with --build-arg if you build elsewhere:
#
#     --build-arg NODE_IMAGE=node:22-bookworm-slim
#     --build-arg JRE_IMAGE=eclipse-temurin:25-jre-noble
#     --build-arg DEBIAN_MIRROR=deb.debian.org/debian
#     --build-arg NPM_REGISTRY=https://registry.npmjs.org
#     --build-arg PIP_INDEX=https://pypi.org/simple
#
# Binary-analysis tools (Ghidra 12.1.4, JADX 1.5.6) are installed from the LOCAL
# release packages in docker/tools/releases/ (from the teammate kit; integrity
# pinned by SOURCES.sha256 there) — no network fetch, no version drift. Drop the
# zips out of that folder to build a smaller image without them. The JRE they
# need (Ghidra 12 wants JDK 21+, bookworm ships 17) comes from a JRE image stage.
#
# Sandbox constraints this image is built around (docs/platform-modes.md):
#   * the hosted sandbox has NO public internet, so EVERYTHING is installed here,
#     at build time — the toolchain, the Python libs, the skills, all of it;
#   * BENCHMARK_TOKEN / BENCHMARK_BASE_URL are injected by the platform at run time;
#   * secrets are never baked in (评测须知第 3 条);
#   * the uploaded artefact must stay under 3 GB — docker/build.sh enforces it.
# =============================================================================

# --- global build args --------------------------------------------------------
# ARGs used in FROM lines MUST precede the first FROM (globals); a stage that
# wants a global's value re-declares it bare ("ARG NAME") inside the stage.
ARG NODE_IMAGE=docker.m.daocloud.io/library/node:22-bookworm-slim
ARG JRE_IMAGE=docker.m.daocloud.io/library/eclipse-temurin:25-jre-noble
ARG DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn/debian
ARG DEBIAN_SECURITY_MIRROR=mirrors.tuna.tsinghua.edu.cn/debian-security

# --- JRE for the Java-based binary tools (Ghidra 12 / JADX need JDK 21+) ------
FROM ${JRE_IMAGE} AS jre

# --- binary tools stage: unpack Ghidra/JADX/Nikto from pinned local archives ---
# Installs the required pinned Nikto release plus any optional Ghidra/JADX
# packages from docker/tools/releases/. Nikto is required for the full image;
# Ghidra/JADX may be omitted to reduce image size.
# It runs on the node base (already pulled, same CN apt mirror as the main stage)
# instead of the JRE image: the only thing it needs from apt is unzip, and one
# base keeps the mirror handling in one place.
FROM ${NODE_IMAGE} AS bin-tools
ARG DEBIAN_MIRROR
ARG DEBIAN_SECURITY_MIRROR
USER root
RUN set -eux; \
    for f in /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list; do \
      [ -f "$f" ] || continue; \
      sed -ri \
        -e "s#https?://deb\.debian\.org/debian-security#http://${DEBIAN_SECURITY_MIRROR}#g" \
        -e "s#https?://security\.debian\.org/debian-security#http://${DEBIAN_SECURITY_MIRROR}#g" \
        -e "s#https?://deb\.debian\.org/debian#http://${DEBIAN_MIRROR}#g" \
        "$f"; \
    done; \
    apt-get update; \
    apt-get install -y --no-install-recommends unzip; \
    rm -rf /var/lib/apt/lists/*
COPY --from=jre /opt/java/openjdk /opt/jdk25
ENV JAVA_HOME=/opt/jdk25 \
    PATH="/opt/jdk25/bin:${PATH}"
COPY docker/tools/releases/ /tmp/rel/
RUN set -eux; \
    test -f /tmp/rel/nikto-2.6.1.zip; \
    if [ -f /tmp/rel/ghidra-12.1.4.zip ] || [ -f /tmp/rel/jadx-1.5.6.zip ] || [ -f /tmp/rel/nikto-2.6.1.zip ]; then \
      test -f /tmp/rel/SOURCES.sha256; \
      for f in ghidra-12.1.4.zip jadx-1.5.6.zip nikto-2.6.1.zip; do \
        if [ -f "/tmp/rel/$f" ]; then \
          expected="$(awk -v name="$f" '{ gsub(/\r/, "", $2); if ($2 == name) print $1 }' /tmp/rel/SOURCES.sha256)"; \
          test -n "$expected"; \
          printf '%s  %s\n' "$expected" "/tmp/rel/$f" | sha256sum -c -; \
        fi; \
      done; \
    fi; \
    mkdir -p /opt/java-tools; \
    if [ -f /tmp/rel/ghidra-12.1.4.zip ]; then \
      unzip -q /tmp/rel/ghidra-12.1.4.zip -d /opt/java-tools; \
      d="$(find /opt/java-tools -maxdepth 1 -type d -name 'ghidra_*' -print -quit)"; \
      test -n "$d" && mv "$d" /opt/java-tools/ghidra; \
    fi; \
    if [ -f /tmp/rel/jadx-1.5.6.zip ]; then \
      mkdir -p /opt/java-tools/jadx && unzip -q /tmp/rel/jadx-1.5.6.zip -d /opt/java-tools/jadx; \
    fi; \
    if [ -f /tmp/rel/nikto-2.6.1.zip ]; then \
      mkdir -p /opt/nikto-unpack; \
      unzip -q /tmp/rel/nikto-2.6.1.zip -d /opt/nikto-unpack; \
      test -f /opt/nikto-unpack/nikto-2.6.1/program/nikto.pl; \
      mv /opt/nikto-unpack/nikto-2.6.1 /opt/nikto; \
    fi; \
    rm -rf /tmp/rel /opt/nikto-unpack

# =============================================================================
# main image
# =============================================================================
FROM ${NODE_IMAGE}

# --- build-time knobs (stage-scoped) ------------------------------------------
ARG CLAUDE_CODE_VERSION=2.1.301
ARG CHROME_DEVTOOLS_MCP_VERSION=0.6.0
# Debian 12 (bookworm), archive and security pocket alike. Both defaults live in
# the global block above and are inherited by this bare re-declaration.
ARG DEBIAN_MIRROR
ARG DEBIAN_SECURITY_MIRROR
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
# angr + z3 full symbolic-execution stack: enabled by default in the full build.
# Set WITH_SYMBEX=0 only when image size/build time takes priority.
ARG WITH_SYMBEX=1

ENV DEBIAN_FRONTEND=noninteractive

# --- apt over the CN mirror ---------------------------------------------------
# bookworm ships deb822-style sources in /etc/apt/sources.list.d/debian.sources;
# the second file covers images that still use the classic one-line format.
#
# http, NOT https: the slim base carries no CA bundle (/etc/ssl/certs is empty),
# so pointing apt at an https archive fails with "Certificate verification
# failed ... No system certificates available" and the whole build dies before
# ca-certificates can ever be installed. apt over http is also Debian's own
# default. ca-certificates is installed by the next RUN, so pip and npm below
# are free to use https.
RUN set -eux; \
    for f in /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list; do \
      [ -f "$f" ] || continue; \
      sed -ri \
        -e "s#https?://deb\.debian\.org/debian-security#http://${DEBIAN_SECURITY_MIRROR}#g" \
        -e "s#https?://security\.debian\.org/debian-security#http://${DEBIAN_SECURITY_MIRROR}#g" \
        -e "s#https?://deb\.debian\.org/debian#http://${DEBIAN_MIRROR}#g" \
        "$f"; \
    done

# --- the toolchain ------------------------------------------------------------
# Everything the agent may need while solving, baked in because the sandbox cannot
# install anything at run time.
#
# Split in two on purpose. The REQUIRED set fails the build if this archive does
# not carry it — without those the image is not fit to ship. The OPTIONAL set is
# installed one package per apt call, so anything the archive lacks degrades to a
# printed "SKIPPED" line instead of killing a 15-minute build; the skipped list is
# echoed at the end so the loss is never silent.
#   * binary/CTF:  nmap, john, binwalk, upx, radare2, strace/ltrace
#   * web:         sqlmap, vendored Nikto 2.6.1, dirb, wfuzz, whatweb
#   * pivoting:    proxychains4, tcpdump, whois, traceroute
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      build-essential cmake pkg-config libc6-dev libssl-dev libffi-dev libgmp-dev \
      python3 python3-pip python3-venv python3-dev \
      ca-certificates curl wget netcat-openbsd socat iproute2 iputils-ping \
      perl libnet-ssleay-perl libio-socket-ssl-perl libxml-writer-perl libxml-libxml-perl \
      dnsutils openssh-client openssl \
      file xxd binutils gdb \
      unzip zip gzip bzip2 xz-utils p7zip-full zstd \
      git jq ripgrep fd-find less procps lsof rsync tini \
      chromium chromium-driver; \
    skipped=""; \
    for p in nmap sqlmap john binwalk traceroute whois tcpdump strace \
             ltrace dirb wfuzz whatweb upx-ucl proxychains4 radare2; do \
      if apt-get install -y --no-install-recommends "$p" >/dev/null 2>&1; then \
        echo "installed: $p"; \
      else \
        echo "SKIPPED (not in this archive): $p"; \
        skipped="$skipped $p"; \
      fi; \
    done; \
    rm -rf /var/lib/apt/lists/*; \
    echo "optional tools skipped:${skipped:- none}"

# --- python security stack ----------------------------------------------------
# Weighted to the TSecBench v1 question mix: web (18/63), evasion (14), binary (13),
# exploitation (9), cloud (6), multi-stage (3).
#   web      : requests/httpx/bs4/lxml/dirsearch/wafw00f
#   evasion  : isolated mitmproxy 11.0.2 (its pinned deps conflict with httpx), PySocks
#   binary   : pwntools/capstone/unicorn/ROPGadget/ropper (+ lief/z3; angr opt-in)
#   cloud    : awscli (simulated metadata/IAM challenges)
# --break-system-packages: Debian marks the system python as externally managed.
RUN set -eux; \
    extra=""; \
    if [ "${WITH_SYMBEX}" = "1" ]; then extra="angr"; fi; \
    pip3 install --no-cache-dir --break-system-packages \
      --index-url "${PIP_INDEX}" \
      requests[socks] httpx pwntools scapy pycryptodome cryptography \
      beautifulsoup4 lxml PySocks paramiko dnspython pyOpenSSL \
      websockets aiohttp impacket sympy gmpy2 lief z3-solver \
      dirsearch wafw00f capstone unicorn ROPGadget ropper awscli $extra; \
    python3 -m venv /opt/mitmproxy; \
    /opt/mitmproxy/bin/pip install --no-cache-dir --index-url "${PIP_INDEX}" "mitmproxy==11.0.2"; \
    for tool in mitmproxy mitmdump mitmweb; do \
      ln -sf "/opt/mitmproxy/bin/${tool}" "/usr/local/bin/${tool}"; \
    done

# --- the harness, pinned ------------------------------------------------------
# Pinned, not latest: the grading run must be reproducible and the platform audits
# what ran. The npm package ships the native binary as a platform dependency, so a
# CN registry serves the whole thing.
# chrome-devtools-mcp is vendored (never npx): the sandbox has no registry access,
# so the entrypoint invokes the installed path with node directly.
RUN npm config set registry "${NPM_REGISTRY}" \
 && npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
 && npm install -g "chrome-devtools-mcp@${CHROME_DEVTOOLS_MCP_VERSION}" \
 && npm cache clean --force

# --- binary tools from the bin-tools stage ------------------------------------
# Ghidra 12.1.4 (headless decompiler) + JADX 1.5.6 (Dex/Java) + the JDK 25 runtime
# they need. Absent release packages simply mean an empty folder here.
COPY --from=bin-tools /opt/java-tools /opt/java-tools
COPY --from=bin-tools /opt/nikto /opt/nikto
COPY --from=jre /opt/java/openjdk /opt/jdk25
RUN set -eux; \
    ln -sf /opt/java-tools/ghidra/support/analyzeHeadless /usr/local/bin/ghidra-headless 2>/dev/null || true; \
    if [ -x /opt/java-tools/jadx/bin/jadx ]; then ln -sf /opt/java-tools/jadx/bin/jadx /usr/local/bin/jadx; fi; \
    test -x /opt/nikto/program/nikto.pl; \
    ln -sf /opt/nikto/program/nikto.pl /usr/local/bin/nikto; \
    chmod +x /opt/nikto/program/nikto.pl; \
    perl -c /opt/nikto/program/nikto.pl; \
    nikto -Version -nocheck
ENV JAVA_HOME=/opt/jdk25 \
    PATH="/opt/jdk25/bin:/opt/java-tools/ghidra/support:/opt/java-tools/jadx/bin:${PATH}"

# --- offline behaviour + tool budgets -----------------------------------------
# The DISABLE_* family removes every code path that would phone home at start-up
# (updates, telemetry, error reporting, feature-flag fetches, feedback commands);
# in a sandbox with no internet each one is a timeout waiting to happen.
# IS_SANDBOX is what lets --dangerously-skip-permissions be honoured as root.
# MCP/BASH budgets are generous because solving runs long commands and MCP
# wait_for_ready can legitimately block for minutes.
ENV CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    DISABLE_TELEMETRY=1 \
    DISABLE_ERROR_REPORTING=1 \
    DISABLE_AUTOUPDATER=1 \
    DISABLE_UPDATES=1 \
    DISABLE_INSTALLATION_CHECKS=1 \
    DISABLE_GROWTHBOOK=1 \
    DISABLE_COST_WARNINGS=1 \
    DISABLE_BUG_COMMAND=1 \
    DISABLE_DOCTOR_COMMAND=1 \
    DISABLE_FEEDBACK_COMMAND=1 \
    DISABLE_LOGIN_COMMAND=1 \
    DISABLE_LOGOUT_COMMAND=1 \
    DISABLE_UPGRADE_COMMAND=1 \
    DISABLE_INSTALL_GITHUB_APP_COMMAND=1 \
    DISABLE_EXTRA_USAGE_COMMAND=1 \
    IS_SANDBOX=1 \
    NO_COLOR=1 \
    CLAUDE_CODE_AUTO_MODE_SERVER=0 \
    CLAUDE_AFK_TIMEOUT_MS=60000 \
    MCP_TIMEOUT=120000 \
    MCP_TOOL_TIMEOUT=600000 \
    BASH_DEFAULT_TIMEOUT_MS=600000 \
    BASH_MAX_TIMEOUT_MS=1800000 \
    BASH_MAX_OUTPUT_LENGTH=200000

# --- writable state + userspace config ---------------------------------------
# All Claude Code configuration lives in ONE userspace folder, rendered at boot
# from the read-only templates below. Secrets are NOT part of it: the platform
# injects BENCHMARK_TOKEN / LLM_API_KEY as env vars (评测须知第 3 条).
ENV TSEC_WORK_DIR=/work \
    TSEC_STATE_DIR=/work/state \
    TSEC_LOG_DIR=/work/logs \
    TSEC_MCP_DIR=/opt/tsecbench \
    TSEC_WORKERS=1 \
    TSEC_KEEPALIVE_INTERVAL=300 \
    CLAUDE_CONFIG_DIR=/work/.claude \
    PYTHONUNBUFFERED=1

WORKDIR /work

# --- the toolbelt + configuration --------------------------------------------
COPY mcp/tsecbench_mcp.py /opt/tsecbench/tsecbench_mcp.py
COPY docs/ /opt/tsecbench/docs/
# The collected skill library lands as a plain on-disk library: NOT auto-loaded into
# the model's context (hundreds of skill descriptions would eat the solving budget).
# A single navigation skill points the agent at its INDEX.md; see docker/claude/skills/.
COPY skills/ /opt/tsecbench/skills-library/
COPY docker/claude/ /opt/tsecbench/claude/
COPY plugin/tsecbench-agent/ /opt/tsecbench/plugin/tsecbench-agent/
COPY plugin/mods/ /opt/tsecbench/plugin/mods/
COPY docker/fleet.py docker/tsec_gw.py docker/mcp_preflight.py docker/keepalive.py /opt/tsecbench/
COPY docker/entrypoint.sh /usr/local/bin/tsecbench-entrypoint
# chromium-container: the flags Chromium needs when it runs as root in a container
# (chrome-devtools-mcp cannot pass browser arguments of its own). See the script.
COPY docker/chromium-container.sh /usr/local/bin/chromium-container

RUN sed -i 's/\r$//' /usr/local/bin/tsecbench-entrypoint /usr/local/bin/chromium-container \
 && chmod +x /usr/local/bin/tsecbench-entrypoint /usr/local/bin/chromium-container \
 && mkdir -p /work/state /work/logs /work/tmp /work/.claude \
 && python3 /opt/tsecbench/tsecbench_mcp.py --selftest >/dev/null \
 && claude --version \
 && echo "image selftest ok: claude + python3 + mcp server present"

# Auto-start: the entrypoint seeds the config, prefights, then launches Claude Code
# on the runbook with no human in the loop.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/tsecbench-entrypoint"]
