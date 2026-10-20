# tsecbench-agent（Claude Code 插件）

本插件为任意 Claude Code 会话提供 TSecBench 评测平台的工具集，包括 MCP 服务器、跑分技能与斜杠命令。

## 安装到所有会话（所有 Agent 可自主调用）

将本目录复制到用户级 skills 目录，下次会话启动时自动加载为 `tsecbench-agent@skills-dir`：

```powershell
Copy-Item -Recurse -Force <repo>\plugin\tsecbench-agent "$env:USERPROFILE\.claude\skills\tsecbench-agent"
claude plugin list     # 应看到 tsecbench-agent@skills-dir
```

也可在单次会话中挂载：`claude --plugin-dir <repo>\plugin\tsecbench-agent`

## 组件

| 组件 | 说明 |
|------|------|
| `.mcp.json` | 注册 `tsecbench` MCP 服务器（12 工具 / 3 资源 / 1 提示词，纯标准库单文件） |
| `skills/tsecbench-runbook` | 跑分流程技能：预检→列题→启动容器→解题→提交 flag→收尾，并包含全部强制规则 |
| `commands/tsec-status` | 查看任务进度、剩余名额、遗留线索 |
| `commands/tsec-run` | 开始/继续自主跑分（可通过 `unique_code` 聚焦单道题目） |
| `commands/tsec-allow` | 诊断当前会话的三层权限放行状态 |

## 环境要求

MCP 服务器依赖 `BENCHMARK_BASE_URL` 与 `BENCHMARK_TOKEN` 两个环境变量（托管模式下由平台自动注入）：

```
BENCHMARK_BASE_URL=https://tsecbench.zc.tencent.com
BENCHMARK_TOKEN=<平台下发的 UUID>
TSEC_MCP_SCRIPT=<仓库>\mcp\tsecbench_mcp.py   # .mcp.json 引用
```

本机调试时可设置 `TSEC_REQUIRE_BENCH_ENV=0`，此时服务器返回带指引的配置错误，而不是崩溃。

## 配套 mod

本插件提供工具能力；权限放行由独立 mod `tsecbench-allow-all` 负责。
该 mod 在 `tool.check` 层直接返回 `allow`。该事件在 `tool.call`/PreToolUse 钩子之后、
权限模式判定之前触发，位于引擎判定链的最深层。见仓库 `plugin/mods/`。

## 安全说明

技能与命令仅为提示词内容；MCP 服务器为纯标准库 Python 实现（无第三方依赖，可审计）。
`get_hint` 工具默认拒绝执行（该操作会扣分），需显式确认。
