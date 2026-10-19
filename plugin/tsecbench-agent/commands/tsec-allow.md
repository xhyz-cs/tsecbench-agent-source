---
description: 检查/说明当前会话的权限放行配置（深层放行 mod 是否生效）
---

检查并向用户报告本会话的权限放行状态：

1. 读取 `~/.claude/dev-mods/` 下是否存在 `tsecbench-allow-all` mod（`.claude-plugin/plugin.json`）
2. 说明三层放行机制，并指出当前生效的是哪几层：
   - **第 1 层**：启动参数 `--dangerously-skip-permissions --permission-mode bypassPermissions`（容器入口已带）
   - **第 2 层**：settings.json 的 `permissions.defaultMode: "bypassPermissions"` 与 `permissions.allow` 规则
   - **第 3 层（最深）**：`tool.check` 钩子 —— 在权限模式判定**之前**由插件直接返回 `allow`，
     这是引擎判定链里最深的一层（`tool.call`/PreToolUse 之后、mode 定夺之前）
3. 如果 mod 未加载，给出启用方式：
   `claude --plugin-dir ~/.claude/dev-mods/tsecbench-allow-all`
   或把该目录加入 `CLAUDE_CODE_PLUGIN_DIRS` 让所有会话自动加载

不要修改任何权限配置，只做诊断与说明。
