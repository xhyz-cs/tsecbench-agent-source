#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
"""Prove the MCP servers in a Claude Code `--mcp-config` file actually connect.

Runs the exact command Claude Code will run, speaks JSON-RPC to it over stdio, and
checks both the handshake and `tools/list`. This is the container's preflight: it
catches a broken toolbelt *before* the grading clock starts, because Claude Code
itself only surfaces MCP failures later and quietly.

    python3 mcp_preflight.py /opt/tsecbench/claude/mcp.json

    python3 mcp_preflight.py --required tsecbench --prune /work/.claude/mcp.effective.json \
        /opt/tsecbench/claude/mcp.json

Only the servers named by --required are load-bearing. Without --required every
declared server must connect (the strict form, for checking a config by hand).
With it, a server that fails is reported and left out of --prune's output while the
exit code still reports success — one unreachable optional tool must not cost the
whole run, and the pruned config is what Claude Code should be started with.

stdlib only, for the same reason the MCP server is.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HANDSHAKE_TIMEOUT_S = 60.0
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "tsecbench-preflight", "version": "1.0.0"},
    },
}


def check_server(name: str, config: dict[str, Any]) -> dict[str, Any]:
    """Start one stdio server, shake hands, list tools, shut it down."""
    command = config.get("command")
    if not command:
        return {"name": name, "ok": False, "reason": "no `command` (only stdio servers are checked here)"}

    env = dict(os.environ)
    env.update({str(k): str(v) for k, v in (config.get("env") or {}).items()})

    started = time.monotonic()
    try:
        proc = subprocess.Popen(
            [command, *config.get("args", [])],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=env,
            cwd=config.get("cwd") or None,
        )
    except OSError as exc:
        return {"name": name, "ok": False, "reason": f"failed to spawn {command!r}: {exc}"}

    try:
        assert proc.stdin and proc.stdout
        proc.stdin.write(json.dumps(INITIALIZE) + "\n")
        proc.stdin.flush()

        deadline = time.monotonic() + HANDSHAKE_TIMEOUT_S
        reply = None
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("id") == 1:
                reply = message
                break
        if reply is None:
            return {"name": name, "ok": False, "reason": "no initialize reply (or it timed out)"}
        if "error" in reply:
            return {"name": name, "ok": False, "reason": f"initialize error: {reply['error']}"}

        result = reply.get("result", {})
        server = result.get("serverInfo", {})

        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n")
        proc.stdin.flush()
        tools_reply = None
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("id") == 2:
                tools_reply = message
                break

        tool_count = 0
        if tools_reply and "result" in tools_reply:
            tool_count = len(tools_reply["result"].get("tools", []))

        return {
            "name": name,
            "ok": tool_count > 0,
            "server": f"{server.get('name')} {server.get('version', '')}".strip(),
            "protocol": result.get("protocolVersion"),
            "tools": tool_count,
            "elapsed_s": round(time.monotonic() - started, 2),
            "reason": None if tool_count else "connected but advertised no tools",
        }
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.wait(timeout=10)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            proc.kill()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Prove the MCP servers in a Claude Code --mcp-config file connect.",
    )
    parser.add_argument("config", help="the --mcp-config file to check")
    parser.add_argument(
        "--required",
        default="",
        help="comma-separated server names that MUST connect; "
             "without it, every declared server must",
    )
    parser.add_argument(
        "--prune",
        metavar="OUT",
        help="write a copy of the config holding only the servers that connected",
    )
    args = parser.parse_args(argv[1:])

    path = Path(args.config)
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return 1

    servers = config.get("mcpServers") or {}
    if not servers:
        print(f"{path} declares no mcpServers", file=sys.stderr)
        return 1

    results = [check_server(name, entry) for name, entry in servers.items()]
    for result in results:
        print(json.dumps(result, ensure_ascii=False))

    connected = [result["name"] for result in results if result["ok"]]
    failed = [result["name"] for result in results if not result["ok"]]

    if args.prune:
        # Claude Code starts whatever the config names, so a server that cannot
        # connect here is dropped rather than left to fail again on every tool call.
        out = Path(args.prune)
        out.write_text(
            json.dumps({"mcpServers": {name: servers[name] for name in connected}}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"preflight: wrote {out} with {connected or 'no servers'}")

    required = [name.strip() for name in args.required.split(",") if name.strip()]
    unusable = [name for name in required if name not in connected] if required else failed
    if unusable:
        print(
            f"preflight: FAILED — {'required' if required else 'declared'} "
            f"server(s) did not connect: {unusable}",
            file=sys.stderr,
        )
        return 1

    if failed:
        print(f"preflight: required servers connected; dropped: {failed}")
    else:
        print("preflight: all MCP servers connected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
