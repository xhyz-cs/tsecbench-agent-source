# TSecBench 托管模式容器（Claude Code）

为第三届腾讯云智能攻防挑战赛（王座协议主赛）准备的**比赛版 Claude Code 容器**：
一键编译、CN 镜像、离线自足、开机即自主工作。

> 分工：**提示词工程归用户** —— `docker/claude/RUNBOOK.md` 与 `docker/claude/SYSTEM_APPEND.md`
> 两个文件完全归你改写，容器启动时自动读取注入。**技能只用网上现有的**
> （由 `skills/` 收集管线落地），不手工编写。

---

## 一键编译

```bash
docker build -f docker/Dockerfile -t tsecbench-agent:latest .
# 或（编译 + 导出 agent.tar.gz + 3GB 校验）：
./docker/build.sh
```

默认全部走 CN 镜像；Nikto 2.6.1 已随源码包本地固定并在镜像构建时离线安装。满血版默认启用 angr/z3（`WITH_SYMBEX=1`），可用 `WITH_SYMBEX=0` 生成瘦身版。其他参数可用 `--build-arg` 覆盖：

| ARG | 默认 | 说明 |
|-----|------|------|
| `NODE_IMAGE` | `docker.m.daocloud.io/library/node:22-bookworm-slim` | 基础镜像（CN 代理） |
| `DEBIAN_MIRROR` / `DEBIAN_SECURITY_MIRROR` | TUNA | apt 源 |
| `NPM_REGISTRY` | `https://registry.npmmirror.com` | npm 源 |
| `PIP_INDEX` | TUNA pypi | pip 源 |
| `CLAUDE_CODE_VERSION` | `2.1.301` | 钉死，保证可复现 |
| `CHROME_DEVTOOLS_MCP_VERSION` | `0.6.0` | CDP 工具，构建期 vendored（沙箱无网，**绝不 npx**） |
| `JRE_IMAGE` | CN 代理的 `eclipse-temurin:25-jre-noble` | Ghidra 12 / JADX 需要 JDK 21+（bookworm 只有 17），用 JRE 镜像阶段拷入 |
| `WITH_SYMBEX` | `1` | 满血版默认安装 angr 符号执行栈（约 0.4GB）；空间受限时可设为 `0` |

---

## 里面有什么

按 **TSecBench v1 题型分布加权**（Web 18 / 对抗规避 14 / 二进制 13 / 漏洞利用 9 / 云 6 / 多阶段 3，共 63 题）：

| 题型 | 工具面 |
|------|--------|
| Web 18 | chromium + chromedriver + **chrome-devtools-mcp（CDP）**、dirsearch、wafw00f、whatweb、dirb、wfuzz、requests/httpx/bs4/lxml |
| 对抗规避 14 | **mitmproxy**（拦截/改写）、PySocks、proxychains4、upx-ucl、openssl |
| 二进制 13 | **Ghidra 12.1.4 + JADX 1.5.6**（队友精选发行包，离线安装）、JDK25、radare2、gdb、binutils、pwntools、capstone、unicorn、ROPGadget、ropper、lief、z3、angr（默认启用） |
| 漏洞利用 9 | sqlmap、**Nikto 2.6.1（随包离线安装）**、nmap、john、binwalk、netcat/socat、metasploit 式手工链（pwntools） |
| 云 6 | awscli（模拟元数据/IAM 题）、openssl |
| 多阶段 3 | impacket、paramiko、proxychains4、ssh 工具链 |
| 通用 | C 构建链（gcc/g++/make/cmake）、python3 全家桶、jq/ripgrep/fd、strace/ltrace、7z/zstd/xz |

---

## 运行时环境变量（平台注入 + 你要补的）

完整清单与注释见 **[`.env.example`](../.env.example)**（可直接复制为 `.env` 后
`docker run --env-file .env ...`，或用平台第 3 步的「从 .env 导入」）。

平台注入（无需手填）：

```
BENCHMARK_TOKEN       # 托管模式由平台自动注入容器
BENCHMARK_BASE_URL    # 同上
```

你需要在「运行时环境变量」里补（**密钥永不写进镜像**，评测须知第 3 条）：

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_API_BASE_URL` | ✅ | 按传入值原样使用；entrypoint 不识别、校验或改写 URL。托管沙箱应填写平台网关形态 |
| `LLM_API_KEY` | ✅ | 模型 API KEY（只进进程环境，不落盘） |
| `LLM_DEFAULT_MODEL` | ✅ | 模型名；**所有模型槽位（含后台小模型）都会指向它**，否则离线沙箱里后台调用静默失败 |
| `LLM_API_TYPE` | – | `anthropic-messages`（默认）/ `openai-completions` / `openai-responses` |
| `TSEC_AUTH_MODE` | – | `bearer`（默认，走 `ANTHROPIC_AUTH_TOKEN`）/ `api-key`（`ANTHROPIC_API_KEY`） |
| `TSEC_WORKERS` | – | `1`（默认，单 agent）/ `N`（舰队） |
| `TSEC_KEEPALIVE_INTERVAL` | – | 保活循环间隔，默认 300 秒，最小 1 秒 |
| `TSEC_FLEET_WORKERS` | – | `TSEC_WORKERS` 的兼容别名；显式设置 `TSEC_WORKERS` 时以后者为准 |
| `TSEC_PREINIT_API_CALLS` | – | MCP initialize 前的平台只读预热请求数，默认 3，范围 0–20 |
| `TSEC_CC_BARE` | – | `1` = bare 模式（**注意**：bare 跳过插件/skills，且只认 `ANTHROPIC_API_KEY`） |

---

## 容器内的用户级配置（一处收敛）

所有 Claude Code 配置在启动时渲染进 `CLAUDE_CONFIG_DIR=/work/.claude`：

```
/work/.claude/
├── settings.json      # env / permissions / hooks / model（由模板渲染）
├── mcp.json           # tsecbench + chrome（CDP）两个 MCP 服务器
├── skills/            # 安装的技能（见下）
├── RUNBOOK.md         # ← 提示词工程：你改这个
└── SYSTEM_APPEND.md   # ← 提示词工程：你改这个
```

**技能：库 + 单个导航技能（不批量注册）**

- `skills/`（仓库根）→ 镜像内 `/opt/tsecbench/skills-library/`：收集自开源社区的技能**库**，
  按六类题型归档，**不注册进模型上下文**（几百条技能描述会挤占解题预算）。
- 唯一自动加载的是 `docker/claude/skills/skills-library/SKILL.md` —— 一个小导航技能，
  引导 agent 读库的 `INDEX.md` → Grep 定位 → Read 对应 `SKILL.md`。
- `plugin/tsecbench-agent/skills/` ——插件级技能，经 `--plugin-dir` 加载（留给用户放自己的）。

> 本仓库不手工编写技能内容；提示词与技能内容归用户。技能库进入镜像前必须通过
> 安全审计（`skills/INDEX.md` 是审计产物；缺失时 build.sh 会大声警告）。

---

## 权限放行的三层结构

| 层 | 机制 | 位置 |
|----|------|------|
| 1 | `--dangerously-skip-permissions --permission-mode bypassPermissions` | entrypoint 启动参数 |
| 2 | `permissions.defaultMode: "bypassPermissions"` | 渲染出的 settings.json |
| 3（最深） | **`tool.check` 钩子直接返回 allow** —— 在权限模式定夺**之前** | `plugin/mods/tsecbench-allow-all`（经 `--plugin-dir` 加载，只存在于镜像内） |

另有 `PreToolUse` / `PermissionRequest` / `Notification` 三个 hook 自动放行/抑制。

---

## 自主运行与保活

- **开机即跑**：`ENTRYPOINT` → 预检（claude 版本 / MCP 连通 / 工具链 / 平台可达）→ 启动 Claude Code 跑 RUNBOOK
- **5 分钟保活循环**（`docker/keepalive.py`）：
  - 心跳写 `heartbeat.jsonl`（安静 ≠ 死亡，可区分）
  - 每轮真实调用 `task_status` → 同时是平台连通探活
  - **任务结束即停**（平台返回 fatal invalid_state 时 SIGTERM agent，不再烧 token）
  - **孤儿容器救援**：agent 死亡且名额占满时自动 close，防止 3 容器把重启后的 agent 卡死
- **舰队模式**（`TSEC_WORKERS>1`）：`docker/fleet.py` 按 `free_slots` 分发、1 worker = 1 题、共享笔记黑板、按题限次
- **崩溃重启**：supervisor 最多 `TSEC_MAX_ATTEMPTS` 次，指数退避；平台 409 则不重启

---

## 离线验证（不上传先自测）

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

上传到平台「开始评测 → 托管模式 → 制作并上传 Docker 镜像」。
容器启动即自动开始解题（平台要求），无需外部触发。

---

## 已知未验证项（诚实清单）

- 本仓库开发机 **没有 Docker**，镜像未编译过：apt 包名、3GB 体积、JRE 镜像阶段、Ghidra/JADX 发行包解压都需首次构建确认
- `chrome-devtools-mcp` 的 `--executablePath` 参数名以你安装版本为准，`TSEC_PREFLIGHT_ONLY=1` 会立即暴露问题
- `cumulative_score` 的任务级/单题级语义未在真平台确认（首次真机跑分时核对）
- 模型白名单 22 项之外的 API 会被网关拒绝，`LLM_API_BASE_URL` 必须来自白名单
