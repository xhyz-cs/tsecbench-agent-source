// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 James and minc
// tsecbench-allow-all — deep allow for every tool call, INSIDE THE COMPETITION CONTAINER ONLY.
//
// Layering, outermost to innermost:
//   1. launch flags  --dangerously-skip-permissions --permission-mode bypassPermissions
//   2. settings.json permissions.defaultMode
//   3. THIS mod: a `tool.check` hook returning { decision: "allow" }
//
// `tool.check` fires when the engine decides whether a tool call may run — after the
// `tool.call` and PreToolUse hooks, and BEFORE the permission mode settles an ask — so
// answering it here approves calls that every outer layer would still have asked about.
// $.tool.check runs the same chain without executing anything.
//
// Failure policy: fail OPEN. A guard that throws is skipped, leaving the verdict
// beneath it; here even an internal error answers `allow`, because in a sandbox with
// no internet and bypassPermissions on the outer layers, denying would only hang the
// run. This mod is deliberately NOT installed on a developer machine.

import type { Register } from "claude-code";

const allow = async () => ({ decision: "allow" as const });

export const register: Register = (on) => {
  // Make the state visible: nothing should ever wonder why nothing asks.
  on("session.start", ($) => {
    $.ui.toast("tsecbench-allow-all: every tool call pre-approved at tool.check (container sandbox)");
  });

  // No matcher: every tool, built-in and MCP.
  on("tool.check", () => allow().catch(() => ({ decision: "allow" as const })));
};
