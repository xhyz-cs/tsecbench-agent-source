# tsecbench-agent（Claude Code 插件）

给任何 Claude Code 会话装上 TSecBench 评测平台的工具带：MCP 服务器 + 跑分技能 + 斜杠命令。

## 安装到所有会话（所有代理可自主调用）

把本目录复制进用户级 skills 目录，下次会话起自动加载为 `tsecbench-agent@skills-dir`：

```powershell
Copy-Item -Recurse -Force <repo>\plugin\tsecbench-agent "$env:USERPROFILE\.claude\skills\tsecbench-agent"
claude plugin list     # 应看到 tsecbench-agent@skills-dir
```

或在单次会话挂载：`claude --plugin-dir <repo>\plugin\tsecbench-agent`

## 内容

| 组件 | 说明 |
|------|------|
| `.mcp.json` | 注册 `tsecbench` MCP 服务器（12 工具 / 3 资源 / 1 提示词，纯标准库单文件） |
| `skills/tsecbench-runbook` | 跑分流程技能：预检→列题→启容器→解题→交旗→收尾 + 全部铁律 |
| `commands/tsec-status` | 查看任务进度、剩余名额、遗留线索 |
| `commands/tsec-run` | 开始/继续自主跑分（可带 `unique_code` 聚焦一题） |
| `commands/tsec-allow` | 诊断当前会话的三层权限放行状态 |

## 环境要求

MCP 服务器靠这两个环境变量工作（托管模式下由平台自动注入）：

```
BENCHMARK_BASE_URL=https://tsecbench.zc.tencent.com
BENCHMARK_TOKEN=<平台下发的 UUID>
TSEC_MCP_SCRIPT=<仓库>\mcp\tsecbench_mcp.py   # .mcp.json 引用
```

本机调试时可设 `TSEC_REQUIRE_BENCH_ENV=0`（服务器会返回带指引的配置错误而不是崩）。

## 配套 mod（更深层放行）

本插件负责「能力」，权限放行由独立 mod 负责：`tsecbench-allow-all`。
它在 `tool.check` 这一层直接返回 `allow` —— 该事件在 `tool.call`/PreToolUse 钩子之后、
权限模式定夺**之前**触发，是引擎判定链里最深的一层。见仓库 `plugin/mods/`。

## 安全说明

技能与命令只是**提示词内容**；MCP 服务器是纯标准库 Python（无第三方依赖，可审计）。
`get_hint` 工具默认拒绝执行（会扣分），需显式确认。
