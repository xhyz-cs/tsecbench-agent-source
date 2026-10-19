#!/usr/bin/env bash
# =============================================================================
# TSecBench hosted-mode entrypoint (harness: Claude Code).
#
#   1. seed a writable CLAUDE_CONFIG_DIR from the read-only copy in the image
#   2. validate the injected benchmark credentials
#   3. validate and use the official HTTPS model URL directly by default (gateway is opt-in)
#   4. export the Anthropic env Claude Code needs — including pointing the SMALL
#      fast model at the same gateway, which is the classic way an offline run
#      silently dies (the main model works, the background model 404s)
#   5. preflight: claude present, MCP config actually connects
#   6. run Claude Code headless (single agent, or the fleet when TSEC_WORKERS > 1)
#
# THE PROCESS NEVER EXITS.
#
# Claude Code is the component that does the work; this script is only its keeper. So
# the loop at the bottom neither breaks nor dies: a session that ends starts another,
# a crash is retried with backoff, and a condition that cannot be solved — no
# credentials, the platform refusing every call — parks the container in an idle loop
# instead of ending it. The platform gives ONE attempt and an exited PID 1 does not
# come back, so a container that is up and idle is strictly better than one that
# exited. Every park is logged, its reason is written to ${STATE_DIR}/PARKED, and the
# platform's own verdict is re-read on a timer — so a task that is reopened later is
# picked up without a restart.
#
# Everything that would normally phone home is disabled in the Dockerfile ENV block.
# =============================================================================

set -euo pipefail

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
RO_CONFIG_DIR="/opt/tsecbench/claude"
MCP_CONFIG="${RO_CONFIG_DIR}/mcp.json"
RUNBOOK="${RO_CONFIG_DIR}/RUNBOOK.md"
SYSTEM_APPEND="${RO_CONFIG_DIR}/SYSTEM_APPEND.md"

WORK_DIR="/work"
LOG_DIR="${TSEC_LOG_DIR:-${WORK_DIR}/logs}"
STATE_DIR="${TSEC_STATE_DIR:-${WORK_DIR}/state}"
if [[ -n "${TSEC_WORK_DIR:-}" && "${TSEC_WORK_DIR}" != "${WORK_DIR}" ]]; then
  printf '[tsecbench] ERROR TSEC_WORK_DIR must remain %s\n' "${WORK_DIR}" >&2
  exit 64
fi
if [[ -n "${CLAUDE_CONFIG_DIR:-}" && "${CLAUDE_CONFIG_DIR}" != "${WORK_DIR}/.claude" ]]; then
  printf '[tsecbench] ERROR CLAUDE_CONFIG_DIR must remain %s/.claude\n' "${WORK_DIR}" >&2
  exit 64
fi
export CLAUDE_CONFIG_DIR="${WORK_DIR}/.claude"
# Agent Teams are experimental in Claude Code and must be enabled before session start.
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

log()  { printf '[tsecbench] %s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"; }
warn() { printf '[tsecbench] WARN  %s\n' "$*" >&2; }

mkdir -p "${LOG_DIR}" "${STATE_DIR}" "${WORK_DIR}/tmp" "${CLAUDE_CONFIG_DIR}"

# Park: what used to be a fatal exit. This container is never allowed to stop, so a
# condition that makes solving impossible idles here instead — logged on the way in,
# recorded in ${STATE_DIR}/PARKED, and re-stated on a timer so a long park is visible
# in the log rather than looking like a hang.
PARK_INTERVAL="${TSEC_PARK_SECONDS:-300}"
park() {
  local why="$*" waited=0
  printf '[tsecbench] PARKED %s\n' "${why}" >&2
  printf '%s\n' "${why}" >"${STATE_DIR}/PARKED" 2>/dev/null || true
  while :; do
    sleep "${PARK_INTERVAL}"
    waited=$(( waited + PARK_INTERVAL ))
    log "parked ${waited}s: ${why}"
  done
}

# -----------------------------------------------------------------------------
# 1. Seed a writable config dir. The image keeps a pristine copy so a restart
#    always begins from a known-good state, and so nothing under CLAUDE_CONFIG_DIR
#    can drift between the build and the run.
# -----------------------------------------------------------------------------
if [[ ! -f "${MCP_CONFIG}" ]]; then
  park "baked Claude Code config missing at ${RO_CONFIG_DIR} — broken image build"
fi
rm -rf "${CLAUDE_CONFIG_DIR}"
mkdir -p "${CLAUDE_CONFIG_DIR}"

# -----------------------------------------------------------------------------
# Everything Claude Code reads lives in ONE userspace config folder:
#   ${CLAUDE_CONFIG_DIR}/settings.json     env / permissions / hooks / model
#   ${CLAUDE_CONFIG_DIR}/mcp.json          user-level MCP servers
#   ${CLAUDE_CONFIG_DIR}/skills/           installed security skills
#   ${CLAUDE_CONFIG_DIR}/RUNBOOK.md        the kickoff prompt
#   ${CLAUDE_CONFIG_DIR}/SYSTEM_APPEND.md
# The image keeps read-only templates; they are rendered here at boot, so a
# restart always begins from a known-good, fully specified configuration.
#
# Deliberate exception: SECRETS are never written into it. LLM_API_KEY and
# BENCHMARK_TOKEN stay in the process environment only — the platform's own rule
# (评测须知第 3 条) is that credentials arrive as env vars and are never persisted.
# -----------------------------------------------------------------------------
SETTINGS_TEMPLATE="${RO_CONFIG_DIR}/settings.json.template"
[[ -f "${SETTINGS_TEMPLATE}" ]] || park "baked Claude Code settings template missing at ${RO_CONFIG_DIR} — broken image build"

python3 - "${SETTINGS_TEMPLATE}" "${CLAUDE_CONFIG_DIR}/settings.json" \
          "${LLM_API_BASE_URL}" "${LLM_DEFAULT_MODEL}" <<'PY'
import json
import sys

template_path, out, base_url, model = sys.argv[1:5]
with open(template_path, encoding="utf-8") as handle:
    template = handle.read()
rendered = (
    template.replace("@@LLM_API_BASE_URL@@", base_url)
            .replace("@@LLM_DEFAULT_MODEL@@", model)
)
if "@@" in rendered:
    sys.exit("unrendered placeholder remains in settings.json — refusing to start")
try:
    data = json.loads(rendered)
except ValueError as exc:
    sys.exit(f"rendered settings.json is not valid JSON: {exc}")
with open(out, "w", encoding="utf-8") as handle:
    json.dump(data, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY

cp "${RO_CONFIG_DIR}/mcp.json"         "${CLAUDE_CONFIG_DIR}/mcp.json"
cp "${RO_CONFIG_DIR}/RUNBOOK.md"       "${CLAUDE_CONFIG_DIR}/RUNBOOK.md"
cp "${RO_CONFIG_DIR}/SYSTEM_APPEND.md" "${CLAUDE_CONFIG_DIR}/SYSTEM_APPEND.md"
RUNBOOK="${CLAUDE_CONFIG_DIR}/RUNBOOK.md"
SYSTEM_APPEND="${CLAUDE_CONFIG_DIR}/SYSTEM_APPEND.md"
MCP_CONFIG="${CLAUDE_CONFIG_DIR}/mcp.json"

# Claude Code stores per-project trust in ~/.claude.json (separate from
# CLAUDE_CONFIG_DIR). Seed only the canonical container workspace entry before
# launching the unattended session, preserving all other global config fields.
python3 - "${HOME}/.claude.json" "${WORK_DIR}" <<'PY'
import json
import os
import sys
import tempfile

path, project = sys.argv[1:3]
data = {}
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except FileNotFoundError:
    pass
if not isinstance(data, dict):
    raise SystemExit("Claude Code global config must be a JSON object")
projects = data.setdefault("projects", {})
if not isinstance(projects, dict):
    raise SystemExit("Claude Code global config projects field must be an object")
entry = projects.setdefault(project, {})
if not isinstance(entry, dict):
    raise SystemExit("Claude Code project trust entry must be an object")
entry["hasTrustDialogAccepted"] = True
entry.setdefault("hasClaudeMdExternalIncludesApproved", False)
directory = os.path.dirname(path)
os.makedirs(directory, exist_ok=True)
fd, tmp = tempfile.mkstemp(prefix=".claude-trust-", dir=directory, text=True)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
PY
log "Claude Code workspace trust configured for ${WORK_DIR}; Agent Teams enabled"

# Exactly ONE skill is auto-loaded: the navigation skill that points the agent at
# /opt/tsecbench/skills-library/. The library itself is never registered — hundreds
# of skill descriptions would eat the model's solving budget.
LIBRARY_DIR="/opt/tsecbench/skills-library"
mkdir -p "${CLAUDE_CONFIG_DIR}/skills"
cp -a "${RO_CONFIG_DIR}/skills/." "${CLAUDE_CONFIG_DIR}/skills/"
loaded="$(find "${CLAUDE_CONFIG_DIR}/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)"
if [[ -f "${LIBRARY_DIR}/INDEX.md" ]]; then
  log "skill library ready: ${LIBRARY_DIR} ($(grep -c '^| \`' "${LIBRARY_DIR}/INDEX.md" 2>/dev/null || echo '?') entries); auto-loaded skills: ${loaded}"
else
  warn "skill library INDEX.md missing at ${LIBRARY_DIR} — the navigation skill will find nothing; agent falls back to its own methods"
fi

log "config dir: ${CLAUDE_CONFIG_DIR}"

# -----------------------------------------------------------------------------
# 2. Benchmark credentials. In hosted mode the platform injects these; if they are
#    absent the run is already doomed, so say so immediately.
# -----------------------------------------------------------------------------
if [[ "${TSEC_REQUIRE_BENCH_ENV:-1}" == "1" ]]; then
  [[ -n "${BENCHMARK_TOKEN:-}" ]]    || park "BENCHMARK_TOKEN is empty — the platform should inject it; nothing can be solved without it"
  [[ -n "${BENCHMARK_BASE_URL:-}" ]] || park "BENCHMARK_BASE_URL is empty — the platform should inject it; nothing can be solved without it"
  log "benchmark credentials present (base_url=${BENCHMARK_BASE_URL})"
else
  warn "TSEC_REQUIRE_BENCH_ENV=0 — continuing without benchmark credentials (local testing only)"
fi

# -----------------------------------------------------------------------------
# 3. Model endpoint: pass the caller-supplied URL through unchanged.
# -----------------------------------------------------------------------------
LLM_API_TYPE="${LLM_API_TYPE:-anthropic-messages}"
case "${LLM_API_TYPE}" in
  anthropic-messages) ;;
  openai-completions|openai-responses)
    warn "LLM_API_TYPE=${LLM_API_TYPE}: Claude Code speaks the Anthropic Messages wire format. Only choose these if the gateway really translates." ;;
  # Not a reason to stop. This value never changes how Claude Code talks, only how
  # the operator expected the gateway to — say so and carry on.
  *) warn "LLM_API_TYPE='${LLM_API_TYPE}' is not one the platform documents; continuing with the Anthropic Messages format" ;;
esac

for required in LLM_API_BASE_URL LLM_API_KEY LLM_DEFAULT_MODEL; do
  [[ -n "${!required:-}" ]] || park "${required} is empty — set it as a runtime env var (评测须知第 3 条: secrets never go in the image)"
done

log "model API base URL: using the configured value unchanged (${LLM_API_BASE_URL})"

# -----------------------------------------------------------------------------
# 4. Auth + model env.
#
# Auth precedence in Claude Code (docs/en/iam): cloud providers, then
# ANTHROPIC_AUTH_TOKEN (Authorization: Bearer — DeepSeek's documented Claude Code
# setting), then ANTHROPIC_API_KEY (X-Api-Key), then apiKeyHelper, then OAuth.
#
# Caveat: --bare mode reads ONLY ANTHROPIC_API_KEY / apiKeyHelper, so bearer auth
# forces bare mode off. Default to bearer (what a gateway wants) and let
# TSEC_AUTH_MODE=api-key opt into bare mode.
# -----------------------------------------------------------------------------
TSEC_AUTH_MODE="${TSEC_AUTH_MODE:-bearer}"
if [[ "${TSEC_AUTH_MODE}" != "bearer" && "${TSEC_AUTH_MODE}" != "api-key" ]]; then
  # A typo, not a reason to stop: bearer is what an LLM gateway wants, and a wrong
  # choice shows up in the first model call either way.
  warn "TSEC_AUTH_MODE='${TSEC_AUTH_MODE}' is not 'bearer' or 'api-key'; using bearer"
  TSEC_AUTH_MODE="bearer"
fi
if [[ "${TSEC_AUTH_MODE}" == "api-key" ]]; then
  export ANTHROPIC_API_KEY="${LLM_API_KEY}"
else
  export ANTHROPIC_AUTH_TOKEN="${LLM_API_KEY}"
  if [[ "${TSEC_CC_BARE:-0}" == "1" ]]; then
    warn "TSEC_CC_BARE=1 needs ANTHROPIC_API_KEY; disabling bare mode because TSEC_AUTH_MODE=bearer"
    TSEC_CC_BARE=0
  fi
fi

export ANTHROPIC_BASE_URL="${LLM_API_BASE_URL}"
export ANTHROPIC_MODEL="${LLM_DEFAULT_MODEL}"

# Point EVERY model slot at the same gateway model. Claude Code calls a small fast
# model in the background (topic detection, summarising, and the Haiku-class slot);
# if any of those still name api.anthropic.com models, the offline sandbox kills
# the run with errors that look nothing like a configuration problem.
export ANTHROPIC_SMALL_FAST_MODEL="${LLM_DEFAULT_MODEL}"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="${LLM_DEFAULT_MODEL}"
export ANTHROPIC_DEFAULT_SONNET_MODEL="${LLM_DEFAULT_MODEL}"
export ANTHROPIC_DEFAULT_OPUS_MODEL="${LLM_DEFAULT_MODEL}"
# Auto mode's classifier is a SECOND model call, and in an offline sandbox a call to a
# model the gateway does not serve is a stall, not an error the agent can recover from.
# Point it at the one model this environment has.
export CLAUDE_CODE_AUTO_MODE_MODEL="${LLM_DEFAULT_MODEL}"
export CLAUDE_CODE_BG_CLASSIFIER_MODEL="${LLM_DEFAULT_MODEL}"

# --- forced, deliberately NOT knobs -------------------------------------------
# Each of these is a correctness requirement of an unattended run rather than a
# preference: get one wrong and the session either stops working or stops entirely. So
# they are exported unconditionally, over anything the platform or a stray `docker run
# -e` put in the environment. The same story lives in docker/claude/settings.json
# (skipDangerousModePermissionPrompt, skipAutoPermissionPrompt,
# askUserQuestionTimeout) — see REVIEW.md §2 for what each one prevents.
#
#   AUTO_MODE_SERVER=0  do not ask the server to review auto mode actions: the sandbox
#                       gateway does not forward the safeguards fields, so asking is a
#                       hang rather than an answer.
#   AFK_TIMEOUT_MS      pairs with askUserQuestionTimeout, and only applies while that
#                       setting is a duration: an unanswered question continues after
#                       a minute instead of waiting forever (the built-in default).
#   IS_SANDBOX=1        the sandbox acknowledgement that lets --dangerously-skip-
#                       permissions be honoured here at all.
export CLAUDE_CODE_AUTO_MODE_SERVER=0
export CLAUDE_AFK_TIMEOUT_MS=60000
export IS_SANDBOX=1

log "model: base_url=${ANTHROPIC_BASE_URL} model=${ANTHROPIC_MODEL} auth=${TSEC_AUTH_MODE} bare=${TSEC_CC_BARE:-0}"

# -----------------------------------------------------------------------------
# Toolchain check. Warn-only: a missing binary costs points but should not stop
# the run, and the agent can often work around one. It must be visible, though,
# because it is much cheaper to notice here than after 8 hours.
# -----------------------------------------------------------------------------
missing_tools=""
for tool in gcc g++ make gdb python3 pip3 nmap netcat socat curl wget openssl \
            jq rg file binwalk sqlmap john tcpdump dig nikto \
            jadx ghidra-headless angr; do
  command -v "${tool}" >/dev/null 2>&1 || missing_tools+="${tool} "
done
if [[ -n "${missing_tools}" ]]; then
  warn "toolchain incomplete, missing: ${missing_tools}  (jadx/ghidra/angr are optional heavies)"
else
  log "toolchain complete (24 probes passed)"
fi

# -----------------------------------------------------------------------------
# 5. Preflight. Cheapest possible proof that the toolbelt is alive before the
#    grading clock starts.
# -----------------------------------------------------------------------------
# Give the platform API a short burst of read-only traffic before MCP's
# initialize handshake.  This is configurable for hosted runtimes that reap an
# idle container during startup; failures are warn-only so a transient network
# issue does not consume the single solving attempt.
PREINIT_API_CALLS="${TSEC_PREINIT_API_CALLS:-3}"
if [[ ! "${PREINIT_API_CALLS}" =~ ^(0|[1-9]|1[0-9]|20)$ ]]; then
  warn "TSEC_PREINIT_API_CALLS must be an integer from 0 to 20 (got: ${PREINIT_API_CALLS}); using 3"
  PREINIT_API_CALLS=3
fi
if [[ -n "${BENCHMARK_TOKEN:-}" && -n "${BENCHMARK_BASE_URL:-}" ]]; then
  for (( preinit_api_try=1; preinit_api_try<=PREINIT_API_CALLS; preinit_api_try++ )); do
    code="$(curl -s -o /dev/null -w '%{http_code}' -m 5 \
              -H "BENCHMARK_TOKEN: ${BENCHMARK_TOKEN}" \
              "${BENCHMARK_BASE_URL}/openapi/v1/challenges" || true)"
    code="${code:-000}"
    log "pre-init platform API call ${preinit_api_try}/${PREINIT_API_CALLS}: HTTP ${code}"
  done
else
  log "pre-init platform API calls skipped: benchmark credentials are not configured"
fi

log "preflight: $(${CLAUDE_BIN} --version 2>&1)"
python3 /opt/tsecbench/tsecbench_mcp.py --selftest >/dev/null || park "tsecbench MCP server failed its selftest — the shipped image is broken"
log "preflight: tsecbench MCP server selftest ok"

# The tsecbench server is the one that matters; any other server that cannot connect
# is dropped from the config Claude Code is handed — a broken optional tool must never
# cost the run, least of all on a single-attempt task.
#
# A failure here does NOT stop anything. It is our own handshake; Claude Code spawns
# its own instance of the server later, so a transient failure now says nothing about
# the run. Retry a few times, then say so and launch anyway.
MCP_CONFIG_EFFECTIVE="${CLAUDE_CONFIG_DIR}/mcp.effective.json"
preflight_ok=0
for preflight_try in 1 2 3; do
  if python3 /opt/tsecbench/mcp_preflight.py \
          --required tsecbench --prune "${MCP_CONFIG_EFFECTIVE}" "${MCP_CONFIG}" \
          >"${LOG_DIR}/mcp-preflight.log" 2>&1; then
    preflight_ok=1
    break
  fi
  warn "MCP preflight attempt ${preflight_try}/3 failed; retrying in 5s"
  sleep 5
done
if [[ "${preflight_ok}" != "1" ]]; then
  cat "${LOG_DIR}/mcp-preflight.log" >&2
  warn "the tsecbench MCP server did not answer our handshake — launching anyway; Claude Code starts its own instance, and a real failure will surface there"
  # The preflight prunes before it judges, so its output can legitimately hold zero
  # servers. Fall back to the declared config rather than hand Claude Code a config
  # with no platform access at all.
  if ! grep -q '"tsecbench"' "${MCP_CONFIG_EFFECTIVE}" 2>/dev/null; then
    MCP_CONFIG_EFFECTIVE="${MCP_CONFIG}"
  fi
fi
if grep -q '"ok": false' "${LOG_DIR}/mcp-preflight.log"; then
  warn "an optional MCP server did not connect and was dropped from this run:"
  grep '"ok": false' "${LOG_DIR}/mcp-preflight.log" >&2
fi
MCP_CONFIG="${MCP_CONFIG_EFFECTIVE}"
log "preflight: $(sed -n 's/^preflight: //p' "${LOG_DIR}/mcp-preflight.log" | tr '\n' ' ' | sed 's/ $//')"
# Optional reachability probe of the platform API. Warn-only: a false negative must
# not burn the single attempt, but it must be visible.
if [[ -n "${BENCHMARK_TOKEN:-}" && -n "${BENCHMARK_BASE_URL:-}" ]]; then
  code="$(curl -s -o /dev/null -w '%{http_code}' -m 15 \
            -H "BENCHMARK_TOKEN: ${BENCHMARK_TOKEN}" \
            "${BENCHMARK_BASE_URL}/openapi/v1/challenges" || echo 000)"
  case "${code}" in
    200) log "preflight: platform API reachable, token accepted" ;;
    000) warn "preflight: could not reach ${BENCHMARK_BASE_URL} — continuing, the agent will retry via MCP" ;;
    *)   warn "preflight: platform API returned HTTP ${code} (404 => bad token, 409 => task already ended)" ;;
  esac
fi

if [[ "${TSEC_PREFLIGHT_ONLY:-0}" == "1" ]]; then
  log "TSEC_PREFLIGHT_ONLY=1 — configuration and MCP connectivity verified, not launching the agent"
  exit 0
fi

# -----------------------------------------------------------------------------
# 6. Run.
# -----------------------------------------------------------------------------
MAX_ATTEMPTS="${TSEC_MAX_ATTEMPTS:-5}"
BACKOFF="${TSEC_BACKOFF_SECONDS:-10}"
DEADLINE_MIN="${TSEC_DEADLINE_MINUTES:-0}"
started_at="$(date +%s)"

# Flags for the session. --dangerously-skip-permissions is the documented choice for
# sandboxes with no internet access; --strict-mcp-config makes --mcp-config the ONLY
# source of MCP servers, so nothing can be injected.
# The hooks block in settings.json carries the other two layers: auto_allow.py
# force-approves the permission and notification paths that survive the outer layers,
# and keep_working.py answers Stop with docker/claude/LOOP_PROMPT.md. Without that
# second one an unattended session simply ends after its first turn.
# The plugin brings skills + commands; the mod allow-approves at tool.check — the
# layer BELOW the permission mode. Both load from the image, not from $HOME.
common_flags=(
  --dangerously-skip-permissions
  --permission-mode bypassPermissions
  # The one tool that exists purely to ask the human something. There is no human, so
  # it can only stall the run; the settings file also caps it at 60s as a backstop.
  --disallowedTools AskUserQuestion
  --mcp-config "${MCP_CONFIG}"
  --strict-mcp-config
  --plugin-dir /opt/tsecbench/plugin/tsecbench-agent
  --plugin-dir /opt/tsecbench/plugin/mods/tsecbench-allow-all
  --append-system-prompt "$(cat "${SYSTEM_APPEND}")"
)
if [[ "${TSEC_CC_BARE:-0}" == "1" ]]; then
  # --bare skips plugin/skill discovery entirely, which would silently drop both
  # --plugin-dir targets above. Say so instead of failing quietly.
  warn "TSEC_CC_BARE=1: plugins and the deep-allow mod will NOT load (bare mode skips them)"
  common_flags+=(--bare)
fi

# -----------------------------------------------------------------------------
# Keep-alive: a heartbeat + platform-watch loop started at boot, alongside the
# agent. It stops a SESSION when the platform says the task has ended; it never
# stops the container — nothing here does.
# -----------------------------------------------------------------------------
KEEPALIVE_PID=""
if [[ "${TSEC_KEEPALIVE:-1}" == "1" ]]; then
  python3 /opt/tsecbench/keepalive.py >>"${LOG_DIR}/heartbeat.jsonl" 2>&1 &
  KEEPALIVE_PID=$!
  trap '[ -n "${KEEPALIVE_PID}" ] && kill "${KEEPALIVE_PID}" 2>/dev/null' EXIT
  log "keepalive loop started (pid ${KEEPALIVE_PID}, interval ${TSEC_KEEPALIVE_INTERVAL:-300}s)"
fi

# -----------------------------------------------------------------------------
# 6. Run — one background session, supervised for as long as the container lives.
#
# The agent is started ONCE, with `claude --bg`: that detaches, prints the session
# handle and returns straight away, and the session then carries on by itself.
# Nothing is ever typed into it — nobody is watching, and a message pushed in by a
# wrapper would be indistinguishable from a real user turn. "Keep going" is enforced
# from INSIDE the session, by the Stop hook (docker/claude/hooks/keep_working.py),
# which answers the agent's attempt to stop with docker/claude/LOOP_PROMPT.md.
#
# So this loop only has to answer two questions: is a session running, and is there
# still work?
#   * running, work left  -> leave it alone
#   * gone, work left     -> start another (the Stop hook keeps a healthy session
#                            alive, so one that vanished vanished for a reason)
#   * no work left        -> drop ${STATE_DIR}/STOP, which is what tells the Stop hook
#                            to let the agent finish, and idle
# It has no exit path: the platform gives ONE attempt and an exited container does
# not come back.
# -----------------------------------------------------------------------------
IDLE_INTERVAL="${TSEC_IDLE_SECONDS:-300}"
CHECK_INTERVAL="${TSEC_AGENT_CHECK_SECONDS:-60}"
BASE_BACKOFF="${TSEC_BACKOFF_SECONDS:-10}"
BACKOFF="${BASE_BACKOFF}"
runs=0
failures=0

# Liveness is a process check, deliberately: `claude agents` output is written for
# humans, and a wording change there must not be able to fool the supervisor into
# starting a second session alongside a live one.
AGENT_PROC_PATTERN="${TSEC_AGENT_PROC_PATTERN:-claude}"
agent_running() {
  pgrep -f "${AGENT_PROC_PATTERN}" >/dev/null 2>&1
}

start_agent() {
  local out session_id
  local -a session_flags=()
  local -a prompt_flags=()

  # ONE conversation for the whole run. The first start pins the session id; every
  # later start RESUMES it, so a session that dies comes back knowing everything the
  # previous one had learned. Only the first start carries the runbook: from then on
  # the Stop hook is what keeps the session working, and a prompt on a resume would be
  # a message from nobody.
  if [[ -s "${STATE_DIR}/session.id" ]]; then
    session_id="$(cat "${STATE_DIR}/session.id")"
    session_flags=(--resume "${session_id}")
  else
    session_id="$(python3 -c 'import uuid; print(uuid.uuid4())')"
    printf '%s\n' "${session_id}" >"${STATE_DIR}/session.id"
    session_flags=(--session-id "${session_id}")
    prompt_flags=("$(cat "${RUNBOOK}")")
  fi

  if out="$("${CLAUDE_BIN}" --bg "${session_flags[@]}" "${common_flags[@]}" \
              --model "${ANTHROPIC_MODEL}" "${prompt_flags[@]}" 2>&1)"; then
    printf '%s\n' "${out}" | tee -a "${LOG_DIR}/agent-starts.log"
    if (( ${#prompt_flags[@]} )); then
      log "background session started (session ${session_id}, runbook sent)"
    else
      log "background session resumed (session ${session_id})"
    fi
    return 0
  fi
  warn "claude --bg could not start session ${session_id}: ${out}"
  return 1
}

while :; do
  # The keep-alive loop writes STOP the moment it sees the platform end the task;
  # clearing it means the check below decides, every time round.
  rm -f "${STATE_DIR}/STOP"

  state="$(python3 /opt/tsecbench/tsecbench_mcp.py --task-state 2>/dev/null || echo work)"
  if [[ "${state}" == "stop" ]]; then
    # Nothing left to solve: every API call would be refused and every nudge wasted.
    # Tell the Stop hook to let the session finish, then idle — the container stays up
    # and the answer is re-read, so a task that reopens needs no restart.
    printf '%s\n' "platform reports no work left" >"${STATE_DIR}/STOP"
    log "platform reports nothing left to solve — idling ${IDLE_INTERVAL}s; the container stays up"
    sleep "${IDLE_INTERVAL}"
    continue
  fi

  if [[ "${DEADLINE_MIN}" != "0" ]]; then
    now="$(date +%s)"
    if (( now - started_at >= DEADLINE_MIN * 60 )); then
      log "self-imposed deadline of ${DEADLINE_MIN} minutes reached — no new sessions; the container stays up"
      sleep "${IDLE_INTERVAL}"
      continue
    fi
  fi

  if [[ "${TSEC_WORKERS:-1}" != "1" ]]; then
    # Fleet mode: the coordinator owns its own one-shot workers, so it is run to
    # completion and restarted if it falls over.
    runs=$(( runs + 1 ))
    log "starting the fleet coordinator (run ${runs})"
    set +e
    python3 /opt/tsecbench/fleet.py > >(tee -a "${LOG_DIR}/fleet.jsonl") 2>&1
    status=$?
    set -e
    if [[ "${status}" -eq 0 ]]; then
      log "the fleet coordinator finished — starting another"
      failures=0
      sleep 5
      continue
    fi
    warn "the fleet coordinator exited with status ${status}"
    failures=$(( failures + 1 ))
    if (( failures >= MAX_ATTEMPTS )); then
      warn "${failures} failures in a row — pausing ${IDLE_INTERVAL}s; the container does not stop"
      sleep "${IDLE_INTERVAL}"
      failures=0
      BACKOFF="${BASE_BACKOFF}"
    else
      sleep "${BACKOFF}"
      BACKOFF=$(( BACKOFF * 2 > 120 ? 120 : BACKOFF * 2 ))
    fi
    continue
  fi

  if agent_running; then
    failures=0
    BACKOFF="${BASE_BACKOFF}"
    sleep "${CHECK_INTERVAL}"
    continue
  fi

  runs=$(( runs + 1 ))
  log "no agent session is running — starting one (run ${runs})"
  start_agent || true
  sleep "${BACKOFF}"
  if agent_running; then
    failures=0
    BACKOFF="${BASE_BACKOFF}"
    continue
  fi

  # There is no "give up" branch: the container does not stop. A growing pause is the
  # most this loop will do about a session that will not come up, because a container
  # that is still up is the only state from which the next attempt can happen at all.
  failures=$(( failures + 1 ))
  warn "no session came up (failure ${failures}/${MAX_ATTEMPTS})"
  if (( failures >= MAX_ATTEMPTS )); then
    warn "${failures} failed starts in a row — pausing ${IDLE_INTERVAL}s; the container does not stop"
    sleep "${IDLE_INTERVAL}"
    failures=0
    BACKOFF="${BASE_BACKOFF}"
  else
    BACKOFF=$(( BACKOFF * 2 > 120 ? 120 : BACKOFF * 2 ))
  fi
done
# Unreachable by design: the loop above has no exit path.
