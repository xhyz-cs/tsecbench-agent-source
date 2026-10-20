# TSecBench 托管模式容器（Claude Code）

本镜像面向第三届腾讯云智能攻防挑战赛（王座协议主赛），提供比赛用的 Claude Code 容器。
构建过程使用 CN 镜像，容器可离线运行，启动后自主执行解题流程。

> 职责划分：提示词工程由操作者负责。`docker/claude/RUNBOOK.md` 与
> `docker/claude/SYSTEM_APPEND.md` 由操作者改写，容器启动时自动读取并注入。
> 技能仅使用网络上现有的内容（由 `skills/` 收集管线落地），不手工编写。

---

## 构建

```bash
docker build -f docker/Dockerfile -t tsecbench-agent:latest .
# 或（编译 + 导出 agent.tar.gz + 3GB 校验）：
./docker/build.sh
```

构建过程默认使用 CN 镜像。Nikto 2.6.1 已随源码包本地固定，并在镜像构建时离线安装。默认启用 angr/z3（`WITH_SYMBEX=1`）；设置 `WITH_SYMBEX=0` 可构建不包含该符号执行栈的镜像。其他参数可通过 `--build-arg` 覆盖：

| ARG | 默认 | 说明 |
|-----|------|------|
| `NODE_IMAGE` | `docker.m.daocloud.io/library/node:22-bookworm-slim` | 基础镜像（CN 代理） |
| `DEBIAN_MIRROR` / `DEBIAN_SECURITY_MIRROR` | TUNA | apt 源 |
| `NPM_REGISTRY` | `https://registry.npmmirror.com` | npm 源 |
| `PIP_INDEX` | TUNA pypi | pip 源 |
| `CLAUDE_CODE_VERSION` | `2.1.301` | 固定版本，保证可复现 |
| `CHROME_DEVTOOLS_MCP_VERSION` | `0.6.0` | CDP 工具，构建期 vendored（沙箱无网络，不通过 `npx` 安装） |
| `JRE_IMAGE` | CN 代理的 `eclipse-temurin:25-jre-noble` | Ghidra 12 / JADX 需要 JDK 21+（bookworm 仅提供 17），通过 JRE 镜像阶段拷入 |
| `WITH_SYMBEX` | `1` | 默认安装 angr 符号执行栈（约 0.4GB）；空间受限时可设为 `0` |

---

## 镜像内容

镜像内容按 TSecBench v1 题型分布加权（Web 18 / 对抗规避 14 / 二进制 13 / 漏洞利用 9 / 云 6 / 多阶段 3，共 63 题）：

| 题型 | 工具面 |
|------|--------|
| Web 18 | chromium + chromedriver + chrome-devtools-mcp（CDP）、dirsearch、wafw00f、whatweb、dirb、wfuzz、requests/httpx/bs4/lxml |
| 对抗规避 14 | mitmproxy（拦截/改写）、PySocks、proxychains4、upx-ucl、openssl |
| 二进制 13 | Ghidra 12.1.4 + JADX 1.5.6（精选发行包，离线安装）、JDK25、radare2、gdb、binutils、pwntools、capstone、unicorn、ROPGadget、ropper、lief、z3、angr（默认启用） |
| 漏洞利用 9 | sqlmap、Nikto 2.6.1（随包离线安装）、nmap、john、binwalk、netcat/socat、metasploit 式手工链（pwntools） |
| 云 6 | awscli（模拟元数据/IAM 题）、openssl |
| 多阶段 3 | impacket、paramiko、proxychains4、ssh 工具链 |
| 通用 | C 构建链（gcc/g++/make/cmake）、python3 工具集、jq/ripgrep/fd、strace/ltrace、7z/zstd/xz |

---

## 运行时环境变量（平台注入与操作者配置）

完整清单与注释见 [`.env.example`](../.env.example)。该文件可直接复制为 `.env` 后通过
`docker run --env-file .env ...` 使用，也可使用平台第 3 步的“从 .env 导入”功能。

平台注入（无需手动填写）：

```
BENCHMARK_TOKEN       # 托管模式由平台自动注入容器
BENCHMARK_BASE_URL    # 同上
```

操作者需要在“运行时环境变量”中补充以下变量（密钥 MUST NOT 写入镜像，见评测须知第 3 条）：

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_API_BASE_URL` | ✅ | 按传入值原样使用；entrypoint 不识别、校验或改写 URL。托管沙箱应填写平台网关形态 |
| `LLM_API_KEY` | ✅ | 模型 API KEY（只进进程环境，不落盘） |
| `LLM_DEFAULT_MODEL` | ✅ | 模型名；所有模型槽位（含后台小模型）都会指向该值，否则离线沙箱中后台调用会静默失败 |
| `LLM_API_TYPE` | – | `anthropic-messages`（默认）/ `openai-completions` / `openai-responses` |
| `TSEC_AUTH_MODE` | – | `bearer`（默认，走 `ANTHROPIC_AUTH_TOKEN`）/ `api-key`（`ANTHROPIC_API_KEY`） |
| `TSEC_WORKERS` | – | `1`（默认，单 agent）/ `N`（舰队） |
| `TSEC_KEEPALIVE_INTERVAL` | – | 保活循环间隔，默认 300 秒，最小 1 秒 |
| `TSEC_FLEET_WORKERS` | – | `TSEC_WORKERS` 的兼容别名；显式设置 `TSEC_WORKERS` 时以后者为准 |
| `TSEC_PREINIT_API_CALLS` | – | MCP initialize 前的平台只读预热请求数，默认 3，范围 0–20 |
| `TSEC_CC_BARE` | – | `1` = bare 模式（bare 跳过插件/skills，且仅识别 `ANTHROPIC_API_KEY`） |

---

## 容器内的用户级配置

所有 Claude Code 配置在启动时渲染到 `CLAUDE_CONFIG_DIR=/work/.claude`：

```
/work/.claude/
├── settings.json      # env / permissions / hooks / model（由模板渲染）
├── mcp.json           # tsecbench + chrome（CDP）两个 MCP 服务器
├── skills/            # 安装的技能（见下）
├── RUNBOOK.md         # ← 提示词工程：你改这个
└── SYSTEM_APPEND.md   # ← 提示词工程：你改这个
```

技能组织方式：技能库与单个导航技能，不批量注册。

- `skills/`（仓库根）→ 镜像内 `/opt/tsecbench/skills-library/`：收集自开源社区的技能库，
  按六类题型归档，不注册到模型上下文（数百条技能描述会占用解题预算）。
- 唯一自动加载的技能是 `docker/claude/skills/skills-library/SKILL.md`，即导航技能，
  引导 Agent 读取技能库的 `INDEX.md`，经 Grep 定位后 Read 对应的 `SKILL.md`。
- `plugin/tsecbench-agent/skills/`：插件级技能，经 `--plugin-dir` 加载，供操作者放置自有技能。

> 本仓库不手工编写技能内容；提示词与技能内容由操作者负责。技能库进入镜像前必须通过
> 安全审计（`skills/INDEX.md` 为审计产物；缺失时 `build.sh` 输出明显警告）。

---

## 权限放行的三层结构

| 层 | 机制 | 位置 |
|----|------|------|
| 1 | `--dangerously-skip-permissions --permission-mode bypassPermissions` | entrypoint 启动参数 |
| 2 | `permissions.defaultMode: "bypassPermissions"` | 渲染出的 settings.json |
| 3（最深） | `tool.check` 钩子直接返回 `allow`，先于权限模式判定 | `plugin/mods/tsecbench-allow-all`（经 `--plugin-dir` 加载，仅存在于镜像内） |

另有 `PreToolUse`、`PermissionRequest`、`Notification` 三个 hook 负责自动放行或抑制。

---

## 自主运行与保活

- 启动即运行：`ENTRYPOINT` 先执行预检（claude 版本 / MCP 连通性 / 工具链 / 平台可达性），随后启动 Claude Code 执行 RUNBOOK
- 保活循环（`docker/keepalive.py`，间隔 5 分钟）：
  - 心跳写入 `heartbeat.jsonl`，可据此区分无输出与已停止
  - 每轮实际调用 `task_status`，同时作为平台连通性探测
  - 任务结束即停止：平台返回 fatal invalid_state 时向 Agent 发送 SIGTERM，不再消耗 token
  - 孤儿容器处理：Agent 死亡且名额已满时自动 close，避免 3 个容器阻塞重启后的 Agent
- 舰队模式（`TSEC_WORKERS>1`）：`docker/fleet.py` 按 `free_slots` 分发任务，1 个 worker 对应 1 道题，共享笔记黑板，按题目限次
- 崩溃重启：supervisor 最多重启 `TSEC_MAX_ATTEMPTS` 次，采用指数退避；平台返回 409 时不重启

---

## 离线验证（上传前自测）

```bash
# 纯配置/MCP 连通性验证，不需要 token、不需要模型
docker run --rm -e TSEC_PREFLIGHT_ONLY=1 \
  -e LLM_API_BASE_URL=https://api.deepseek.com -e LLM_API_KEY=dummy -e LLM_DEFAULT_MODEL=deepseek-chat \
  tsecbench-agent:latest

# 用仓库自带的离线 mock 平台做端到端
python mcp/tests/mock_tsec_api.py --port 18099 --token test-token --vpn-port 18097 &
docker run --rm -e TSEC_PREFLIGHT_ONLY=1 \
  -e BENCHMARK_BASE_URL=http://host.docker.internal:18099 -e BENCHMARK_TOKEN=test-token \
  -e LLM_API_BASE_URL=https://api.deepseek.com -e LLM_API_KEY=dummy -e LLM_DEFAULT_MODEL=x \
  tsecbench-agent:latest
```

---

## 上传

```bash
./docker/build.sh          # 导出 agent.tar.gz 并强制校验 ≤3GB
```

在平台“开始评测 → 托管模式 → 制作并上传 Docker 镜像”页面上传镜像。
容器启动后自动开始解题（平台要求），无需外部触发。

---

## 已知未验证项

- 本仓库的开发机未安装 Docker，镜像尚未构建：apt 包名、3GB 体积、JRE 镜像阶段、Ghidra/JADX 发行包解压均需在首次构建时确认
- `chrome-devtools-mcp` 的 `--executablePath` 参数名以实际安装版本为准；设置 `TSEC_PREFLIGHT_ONLY=1` 可立即发现问题
- `cumulative_score` 的任务级/单题级语义尚未在真实平台确认，需在首次真机跑分时核对
- 模型白名单 22 项之外的 API 会被网关拒绝，`LLM_API_BASE_URL` 必须取自白名单
