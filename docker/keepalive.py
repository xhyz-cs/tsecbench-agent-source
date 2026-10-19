#!/usr/bin/env python3
"""Keep-alive loop: one heartbeat every TSEC_KEEPALIVE_INTERVAL seconds (default 300).

Started by the entrypoint at container boot, alongside the agent. Four jobs, in
priority order:

1. **Heartbeat** — append one line per tick to the log, so a silent container is
   distinguishable from a busy one (the platform audits the run).
2. **Platform liveness** — call `task_status` every tick. That is a real API round
   trip, so it doubles as a connectivity probe, and it is how we learn the task has
   ended.
3. **Task ended → stop the AGENT, never the container.** Burning tokens on an ended
   task is the most expensive failure mode, so the agent is stopped here, from the
   platform's own answer rather than inferred from its behaviour. This loop keeps
   ticking afterwards: the container has to outlive the task, because the platform
   gives one attempt and an exited container does not come back. If the task is ever
   reopened, the heartbeat is already running to notice.
4. **Anti-deadlock rescue.** If the agent process is gone for several consecutive
   ticks while all container slots are still occupied, those are orphans — close
   them, or the restarted agent deadlocks at the 3-container cap.

Restarting a dead agent is deliberately NOT this loop's job: the entrypoint's
supervisor owns that, and two restarters would race.

    python3 keepalive.py

stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.environ.get("TSEC_MCP_DIR", "/opt/tsecbench"))
import tsecbench_mcp as tsec  # noqa: E402  (path set up above on purpose)

INTERVAL_S = max(1, int(os.environ.get("TSEC_KEEPALIVE_INTERVAL", "300") or 300))
# How many consecutive ticks with a dead agent before declaring it gone.
DEAD_TICKS = max(1, int(os.environ.get("TSEC_KEEPALIVE_DEAD_TICKS", "2") or 2))
STOP_FILE = Path(os.environ.get("TSEC_STOP_FILE", "/work/state/STOP"))
# The same process pattern the entrypoint supervises by. `claude --bg` detaches, so
# this loop owns no pid of its own; a process check is the format-free signal.
PROC_PATTERN = os.environ.get("TSEC_AGENT_PROC_PATTERN", "claude")


def log(event: str, **fields: Any) -> None:
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **fields}
    sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def agent_running() -> bool:
    """Is a session process alive?

    A process check rather than a pid file: `claude --bg` detaches, so there is no pid
    for this loop to own, and the entrypoint supervises by this same signal.
    """
    try:
        done = subprocess.run(
            ["pgrep", "-f", PROC_PATTERN],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def mark_task_over(reason: str) -> None:
    """Write the marker the Stop hook reads before it lets the agent finish.

    The session is not signalled — the hook is the supported place to end a turn, and
    with --bg there is no pid to signal anyway. Writing this file is what makes the
    hook answer the next Stop with "yes, you may finish".
    """
    log("task_over", reason=reason)
    try:
        STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
        STOP_FILE.write_text(f"{reason}\n", encoding="utf-8")
    except OSError:
        pass


def main(argv: list[str]) -> int:
    dead_ticks = 0
    tick = 0

    log("keepalive_start", interval_s=INTERVAL_S, agent_proc_pattern=PROC_PATTERN)

    while True:
        tick += 1
        agent_alive = agent_running()

        status: dict[str, Any] = {}
        try:
            status = tsec.tool_task_status()
        except tsec.TsecApiError as exc:
            status = exc.payload
        except Exception as exc:  # noqa: BLE001 - the loop must never die
            status = {"ok": False, "code": "keepalive_error", "message": str(exc)}

        if status.get("ok"):
            log(
                "heartbeat",
                tick=tick,
                agent_alive=agent_alive,
                completed=status.get("completed"),
                total=status.get("total_challenges"),
                flags_correct=(status.get("flags") or {}).get("correct"),
                flags_total=(status.get("flags") or {}).get("total"),
                active=status.get("active_containers"),
                free_slots=status.get("free_slots"),
            )
        else:
            log(
                "heartbeat_degraded",
                tick=tick,
                agent_alive=agent_alive,
                code=status.get("code"),
                message=(status.get("message") or "")[:200],
            )
            # invalid_state that is not the container cap means the task is over: stop
            # the agent so it stops spending tokens. This loop deliberately keeps
            # running — the container outlives the task, and a reopened task has to be
            # noticed without a restart. Re-sending the stop is harmless: by the next
            # tick the pid is normally already gone.
            if status.get("code") == "invalid_state" and status.get("fatal"):
                mark_task_over("platform reports the benchmark task has ended")
            elif status.get("code") == "missing_local_config":
                mark_task_over("benchmark credentials disappeared")

        if agent_alive:
            dead_ticks = 0
        else:
            dead_ticks += 1
            if dead_ticks == DEAD_TICKS:
                log("agent_not_running", ticks=dead_ticks,
                    note="the entrypoint supervisor owns restarts; this is advisory")
            if dead_ticks >= DEAD_TICKS and status.get("free_slots") == 0:
                # Agent gone + every slot held == orphans. Free them or the restarted
                # agent deadlocks at the cap and burns the run doing nothing.
                log("rescue_orphan_containers")
                result = tsec.tool_close_all_challenges(confirm=True)
                log("rescue_done", closed=result.get("closed"), failed=result.get("failed"))
                dead_ticks = 0

        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except KeyboardInterrupt:
        raise SystemExit(0)
