# TSecBench 接入知识库 + 本地 MCP

`https://tsecbench.zc.tencent.com/`（腾讯安全云鼎实验室 · 自主 Agent 评测与验证基础设施）
的接入资料与工具链。目标：让队友的 Agent 在评测环境里有一把**足够锋利的瑞士军刀**。

赛事入口：[第三届腾讯云智能攻防挑战赛](https://zc.tencent.com/hackathon)。
**线上初赛 2026-10-17 09:00 — 10-18 23:59，仅支持托管模式，全程只有 1 次评测机会，仅队长账号可提交。**

---

## 交付物

| 路径 | 是什么 | 给谁用 |
|------|--------|--------|
| **[llms.txt](llms.txt)** | 单文件平台导览：最短上手路径、五条铁律、模式选择、赛事约束 | 直接丢给 LLM / 作为仓库的 LLM 入口 |
| **[docs/challenges-api.md](docs/challenges-api.md)** | Challenges API **权威参考**（结构整理自官方文档 + **实测校准**；本仓库补充处以「增补」标注） | 任何要写接入代码的人 |
| **[docs/platform-modes.md](docs/platform-modes.md)** | 三种评测模式（本地 / 托管-Agent / 托管-Model）的完整配置要求、站点地图、赛事规则 | 决定「怎么跑、怎么交」 |
| **[docs/sdk-python.md](docs/sdk-python.md)** | 官方 Python SDK 文档整理 | 想用 `pip install tsec-benchmark` 的人 |
| **[docs/agent-prompt.md](docs/agent-prompt.md)** | 平台下发的官方 Agent 提示词原文 | 零开发接入：替换凭证即可跑 |
| **[mcp/](mcp/)** | **零依赖 MCP 服务器**：12 工具 + 3 资源 + 1 提示词，单文件可塞进评测镜像 | 队友的 Agent |
| **[mcp/tests/](mcp/tests/)** | 离线 mock（忠实复刻平台 API）+ 集成测试套件 | 改代码的人 |

---

## 60 秒了解这个平台

- **平台给什么**：跑分任务创建后下发 `BENCHMARK_BASE_URL` + `BENCHMARK_TOKEN` + 靶场 VPN 配置。
  之后通过 5 个 HTTP 接口答题：列题 → 启容器 → （可选）取提示 → 提交 flag → 关容器。
- **五条铁律**：
  1. 所有 `/openapi/v1/challenges/*` 请求带 `BENCHMARK_TOKEN` 头。**token 无效→404；token 缺失→422**（实测，官方文档写的是 404）。
  2. **同时最多 3 道题活跃**。超限报 `invalid_state`（message 含 `max active`）→ 先 close 再 start。**答完必须 close**。
  3. **一题可能多个 flag**，要多次 submit。重复提交已正确的 flag → `duplicate`（不加分，跳过）。
  4. **hint 会扣分**（按 `hint_cost_radio` 比例折减该题得分），已通关的题不能再取。
  5. **任务有总时限**。超时后**所有**接口返回 `invalid_state`，必须停止并报告。
- **判据**：响应里有 `code` → 业务异常；只有 `detail` 数组 → 框架级 422 校验错误。

---

## 快速开始

### 用 MCP（推荐给队友的 Agent）

零依赖，不需要 `pip install` 任何东西：

```bash
# 自检（不联网、不需要 token）
python mcp/tsecbench_mcp.py --selftest

# 注册进 Claude Code
claude mcp add tsecbench \
  --env BENCHMARK_BASE_URL=https://tsecbench.zc.tencent.com \
  --env BENCHMARK_TOKEN=<平台下发的 uuid> \
  -- python "$(pwd)/mcp/tsecbench_mcp.py"
```

工具：`vpn_check`、`list_challenges`、`task_status`、`start_challenge`、`wait_for_ready`、
`submit_flag`、`get_hint`（默认拒绝，会扣分）、`close_challenge`、`close_all_challenges`、
`probe_target`（TCP 连通性探测）、`note_save` / `note_list`（跨崩溃的持久笔记）。

详见 [mcp/README.md](mcp/README.md)。

### 用 HTTP / SDK

见 [docs/challenges-api.md](docs/challenges-api.md) 与 [docs/sdk-python.md](docs/sdk-python.md)。

---

## 三种评测模式（别选错）

| 模式 | 用途 | 运行位置 | 成绩效力 |
|------|------|----------|----------|
| **本地模式** | 开发调试、评测他人程序 | 你的环境 + VPN | 仅供自己参考，无防作弊 |
| **托管模式-Agent** | **正式打榜 / 本次参赛** | 平台沙箱（8核16G） | 官方认证 |
| **托管模式-Model** | 横评大模型能力 | 平台统一 Harness | 进首页 Model 榜 |

托管模式两个硬约束（[详见](docs/platform-modes.md)）：

1. **模型 API URL 原样传递**。entrypoint 不识别、校验或改写 `LLM_API_BASE_URL`；托管沙箱按平台要求
   配置可访问的网关 URL（例如 DeepSeek Anthropic 格式 `http://api.deepseek.com.tsecbench.gw/anthropic`）。
2. **交付物是 Docker 镜像**：`.tar`/`.tar.gz`/`.tgz`，≤3GB，`docker save` 导出，
   **容器启动后自行开始解题**；`BENCHMARK_TOKEN` / `BENCHMARK_BASE_URL` 由平台自动注入，
   敏感配置走环境变量录入，**不要写进镜像**。

官方明确要求：**务必先完成本地模式评测（Agent 已接入平台答题 API），再进行托管模式评测。**
本轮 MCP 就是为这一步服务的。

---

## 放进评测镜像

服务器是单文件零依赖，接入成本就是一次 `COPY`：

```dockerfile
COPY tsecbench_mcp.py /opt/tsecbench/tsecbench_mcp.py
COPY docs/ /opt/tsecbench/docs/          # 可选：让 MCP 资源带上完整文档
# 无需 pip install —— 只用标准库
```

细节与三条沙箱注意事项见 [mcp/README.md](mcp/README.md) 的「放进评测沙箱」一节。

---

## 验证

```bash
python mcp/tsecbench_mcp.py --selftest                      # 协议装配 + 纯逻辑自检（不联网、不需 token）
python -m unittest discover -s mcp/tests -t mcp/tests -v    # 全部集成测试（自动拉起 mock 平台）
```

集成测试覆盖：MCP 握手与 JSON-RPC 分发、12 个工具的正常路径、**活跃名额上限及自救路径**、
`duplicate` 幂等、错误 flag 返回 200、`invalid_state` 三种语义分流、任务过期后全接口 fatal、
未知 code 可跳过、hint 双重门禁、`probe_target` 可达性、笔记跨进程存活，
以及**「源码里不存在第三方 import」这条被测试强制的契约**。

---

## 仓库布局

```
.
├── llms.txt                     # LLM 入口导览
├── README.md                    # 本文件
├── docs/                        # 权威参考（人工整理自平台官方文档）
│   ├── challenges-api.md        #   Challenges API + 实测校准
│   ├── platform-modes.md        #   三种模式 / 站点地图 / 赛事规则
│   ├── sdk-python.md            #   官方 Python SDK
│   └── agent-prompt.md          #   官方 Agent 提示词原文
├── mcp/
│   ├── tsecbench_mcp.py         # 零依赖 MCP 服务器（单文件）
│   ├── README.md                # 工具参考 / 配置 / 沙箱部署
│   └── tests/
│       ├── mock_tsec_api.py         # 离线 mock：忠实复刻平台 API + VPN 预检
│       ├── test_tsecbench_mcp.py    # 工具与错误分流集成测试（unittest）
│       ├── test_stdio_transport.py  # stdio 传输层集成测试（unittest）
│       └── README.md                # mock 端口布局、夹具、_test 控制端点
├── build/                       # 一次性侦察脚本
└── recon/                       # 平台前端 bundle 原始副本（.gitignore，未跟踪）
```

---

## 资料出处与可信度

严格区分「官方说的」与「我们实测的」：

| 来源 | 可信度 | 位置 |
|------|--------|------|
| 平台官方文档（API / SDK / Agent 提示词 / 三种模式页面） | 权威，但**有已知偏差** | `docs/`，结构整理；本仓库补充处标注「增补」 |
| **线上实测探测**（2026-10-16） | 高，可复现 | `docs/challenges-api.md` §0 |
| 站点侦察（路由、试题集、赛事规则） | 中，平台改版会失效 | `docs/platform-modes.md` |
| `recon/` 下的前端 bundle | 原始未加工 | 未跟踪，仅供追溯 |

**已实测校准的三处**（详见 [§0](docs/challenges-api.md)）：

1. **缺失** `BENCHMARK_TOKEN` 头返回 **422**（框架校验），不是官方文档写的 404 `task_not_found`。
   实现时必须把「缺失」和「无效」分开处理。
2. `invalid_state` 用**同一个 HTTP 409 + 同一个 code** 表达了三种语义
   （名额满 / 已通关 / 任务已结束），**只能靠 `message` 区分**，其中只有「任务已结束」是致命的。
3. 平台不暴露 OpenAPI schema（`/openapi/openapi.json`、`/openapi/docs` 均 404），
   且 API 与站点**同源**。

**未验证的部分**（诚实说明）：我们没有真实 `BENCHMARK_TOKEN`，因此**没有跑过一次真实跑分**。
上述接口字段、错误码、状态机语义均来自平台官方文档；错误行为的**触发与分流逻辑**已用
`mcp/tests/mock_tsec_api.py` 离线验证，但**未经真实平台端到端确认**。
拿到 token 后，第一件事应该是 `vpn_check` + `list_challenges` 做一次真机联通验证。

---

## 待办 / 下一步

- [ ] 拿到 `BENCHMARK_TOKEN` 后做一次真机端到端验证（`vpn_check` → `list_challenges`）。
- [ ] 用真机响应校对 `docs/challenges-api.md` §0 的实测结论。
- [ ] 探明其余试题集的 `suiteId`（目前只确认 Tsecbench v1 = 4）。
- [ ] 把 MCP 打进 Agent 镜像，在**其他题集的托管模式**下跑通全链路（正式赛只有一次机会）。

---

<sub>本仓库资料由 agent 抓取与整理（2026-10-16），非腾讯官方发布。平台内容版权归腾讯所有；
如对外分享，请保留本出处说明。</sub>


## 许可证

本项目原创内容——`mcp/`、`docker/`、`build/`、`plugin/`、`docs/`、`skills/kit/` 下的自研技能与方法论文档，以及项目文档——由 James 与 minc 版权所有（2026），采用 **Apache License 2.0**（根目录 `LICENSE`），署名声明见 `NOTICE`。

第三方内容保留其上游许可证：

- `skills/` 技能库汇集了 9 个公开仓库与 PayloadsAllTheThings 快照。各来源的许可证、固定 commit 与逐目录证据见 `THIRD_PARTY_NOTICES.md`（英文）；自带 `LICENSE` 的目录以该文件为准。
- 固定版本工具包（`docker/tools/releases/`）：Nikto 2.6.1 按上游条款原样再分发（代码为 GPL-3.0-only 并附附加条款；数据库文件不适用 GPL，仅限随官方包分发；内置 LibWhisker 为 BSD-2-Clause，均见包内 `COPYING`/`COPYING.LibWhisker`）；Ghidra（Apache-2.0）与 JADX（Apache-2.0）为可选包，未纳入本仓库。`docker/tools/LICENSES-and-NOTICES.md` 保留队友工具包的来源记录。
- 构建期依赖（Debian 系统包、Python 包、npm 包）由 `docker/Dockerfile` 安装，各自遵循其许可证。
- 许可信息可机器读取：`REUSE.toml` 为每个路径映射 SPDX 许可与版权人，`LICENSES/` 收录许可全文，仓库通过 `reuse lint`（REUSE Specification 3.3）。

**合规提示：** 本仓库不包含任何专有许可的技能内容。原先 vendor 的 Anthropic `pdf` 技能因许可禁止在 Anthropic 服务之外保留与再分发，已于 2026-10-20 移除。详见 `THIRD_PARTY_NOTICES.md` 的 "Compliance flags" 章节。

> English: see the "License" section of `README.md` and the full inventory in `THIRD_PARTY_NOTICES.md`.
