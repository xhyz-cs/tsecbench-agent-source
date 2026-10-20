# TSecBench Agent 接入文档与本地 MCP 服务器

本仓库提供 `https://tsecbench.zc.tencent.com/`（腾讯安全云鼎实验室自主 Agent 评测与验证基础设施）的接入资料与工具链，用于支撑团队成员在评测环境中完成题目。

赛事入口：[第三届腾讯云智能攻防挑战赛](https://zc.tencent.com/hackathon)。线上初赛时间为 2026-10-17 09:00 至 10-18 23:59，仅支持托管模式；全程仅有 1 次评测机会，且仅队长账号可提交。

---

## 交付物

| 路径 | 说明 | 适用对象 |
|------|------|----------|
| [llms.txt](llms.txt) | 单文件平台导览：最短接入路径、核心约束、模式选择与赛事规则 | 需要 LLM 入口的读者 |
| [docs/challenges-api.md](docs/challenges-api.md) | Challenges API 参考文档（结构整理自官方文档并附实测校准；本仓库补充处以“增补”标注） | 编写接入代码的开发者 |
| [docs/platform-modes.md](docs/platform-modes.md) | 三种评测模式的配置要求、站点地图与赛事规则 | 负责选择与执行评测模式的成员 |
| [docs/sdk-python.md](docs/sdk-python.md) | 官方 Python SDK 文档整理 | 使用 `pip install tsec-benchmark` 的开发者 |
| [docs/agent-prompt.md](docs/agent-prompt.md) | 平台下发的官方 Agent 提示词原文 | 需零开发接入的成员 |
| [mcp/](mcp/) | 零依赖 MCP 服务器：12 个工具、3 个资源、1 个提示词，单文件可部署至评测镜像 | 接入平台的 Agent |
| [mcp/tests/](mcp/tests/) | 离线 mock（复刻平台 API）与集成测试套件 | 修改接入代码的开发者 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献流程与许可要求 | 贡献者 |
| [DISCLAIMER.md](DISCLAIMER.md) | 使用范围、责任免除与适用法律 | 全体使用者 |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | 第三方组件许可清单 | 分发与合规审查人员 |
| [docs/style-guide.md](docs/style-guide.md) | 文档写作规范与术语表 | 文档维护者 |

---

## 平台概述

- **平台提供的内容**：创建跑分任务后，平台下发 `BENCHMARK_BASE_URL`、`BENCHMARK_TOKEN` 与靶场 VPN 配置。接入方随后通过 5 个 HTTP 接口完成答题：列出题目、启动容器、获取提示（可选）、提交 flag、关闭容器。
- **核心运行约束**：
  1. 所有 `/openapi/v1/challenges/*` 请求必须携带 `BENCHMARK_TOKEN` 头。实测结果为：token 无效返回 404，token 缺失返回 422（官方文档记载均为 404）。
  2. 同时最多允许 3 道题处于活跃状态。超限时返回 `invalid_state`（`message` 含 `max active`），应先关闭已有容器再启动新容器；答题完成后必须关闭容器。
  3. 单题可能存在多个 flag，需多次提交。重复提交已正确的 flag 返回 `duplicate`，不计分，应跳过。
  4. 获取提示会扣分（按 `hint_cost_radio` 比例折减该题得分），已通关的题目不能再次获取提示。
  5. 任务存在总时限。超时后所有接口返回 `invalid_state`，此时必须停止操作并报告结果。
- **响应判据**：响应中包含 `code` 字段表示业务异常；仅包含 `detail` 数组表示框架级 422 校验错误。

---

## 快速开始

### 使用 MCP（推荐）

MCP 服务器仅依赖 Python 标准库，无需执行 `pip install`：

```bash
# 自检（不联网，不需要 token）
python mcp/tsecbench_mcp.py --selftest

# 注册到 Claude Code
claude mcp add tsecbench \
  --env BENCHMARK_BASE_URL=https://tsecbench.zc.tencent.com \
  --env BENCHMARK_TOKEN=<平台下发的 uuid> \
  -- python "$(pwd)/mcp/tsecbench_mcp.py"
```

工具集：`vpn_check`、`list_challenges`、`task_status`、`start_challenge`、`wait_for_ready`、`submit_flag`、`get_hint`（默认拒绝，调用会扣分）、`close_challenge`、`close_all_challenges`、`probe_target`（TCP 连通性探测）、`note_save` 与 `note_list`（跨进程持久笔记）。

详细说明见 [mcp/README.md](mcp/README.md)。

### 使用 HTTP 或 SDK

参见 [docs/challenges-api.md](docs/challenges-api.md) 与 [docs/sdk-python.md](docs/sdk-python.md)。

---

## 评测模式

| 模式 | 用途 | 运行位置 | 成绩效力 |
|------|------|----------|----------|
| 本地模式 | 开发调试、评测他人程序 | 自有环境 + VPN | 仅供本人参考，无防作弊机制 |
| 托管模式 - Agent 评测 | 正式评测与本次参赛 | 平台沙箱（8 核 16 GB） | 官方认证 |
| 托管模式 - Model 评测 | 横向比较大模型能力 | 平台统一 Harness | 计入首页 Model 榜 |

托管模式的两项硬性约束（详见 [docs/platform-modes.md](docs/platform-modes.md)）：

1. **模型 API URL 原样传递**。entrypoint 不识别、不校验、不改写 `LLM_API_BASE_URL`；托管沙箱按平台要求配置可访问的网关 URL（例如 DeepSeek Anthropic 格式 `http://api.deepseek.com.tsecbench.gw/anthropic`）。
2. **交付物为 Docker 镜像**：`.tar`、`.tar.gz` 或 `.tgz` 格式，不超过 3 GB，使用 `docker save` 导出；容器启动后须自行开始解题。`BENCHMARK_TOKEN` 与 `BENCHMARK_BASE_URL` 由平台自动注入，敏感配置通过环境变量录入，不得写入镜像。

官方明确要求：**必须先完成本地模式评测（Agent 已接入平台答题 API），再进行托管模式评测。** 本轮 MCP 即为满足该前置步骤而开发。

---

## 部署至评测镜像

MCP 服务器为单文件、零依赖实现，接入成本仅为一次 `COPY`：

```dockerfile
COPY tsecbench_mcp.py /opt/tsecbench/tsecbench_mcp.py
COPY docs/ /opt/tsecbench/docs/          # 可选：为 MCP 资源提供完整文档
# 无需 pip install，仅使用标准库
```

部署细节与三项沙箱注意事项见 [mcp/README.md](mcp/README.md) 的“部署至评测沙箱”一节。

---

## 验证

```bash
python mcp/tsecbench_mcp.py --selftest                    # 协议装配与纯逻辑自检（不联网、不需要 token）
python -m unittest discover -s mcp/tests -v               # 全部集成测试（自动启动 mock 平台）
```

集成测试覆盖以下内容：MCP 握手与 JSON-RPC 分发、12 个工具的正常路径、活跃名额上限及恢复路径、`duplicate` 幂等、错误 flag 返回 200、`invalid_state` 的三种语义分流、任务过期后全部接口返回致命错误、未知 code 可跳过、hint 双重门禁、`probe_target` 可达性、笔记跨进程存活，以及“源码中不存在第三方 import”这一由测试强制执行的契约。

---

## 仓库布局

```text
.
├── LICENSE / NOTICE                # Apache-2.0 与署名声明
├── README.md / README_CN.md        # 中英文仓库说明
├── CONTRIBUTING.md                 # 贡献流程
├── DISCLAIMER.md                   # 免责声明（中文为正式文本）
├── THIRD_PARTY_NOTICES.md          # 第三方许可清单
├── REUSE.toml / LICENSES/          # 机器可读许可元数据与许可全文
├── llms.txt                        # LLM 入口导览
├── docs/                           # 权威参考（整理自平台官方文档）
│   ├── challenges-api.md           #   Challenges API 与实测校准
│   ├── platform-modes.md           #   三种模式、站点地图与赛事规则
│   ├── sdk-python.md               #   官方 Python SDK
│   ├── agent-prompt.md             #   官方 Agent 提示词原文
│   └── style-guide.md              #   文档写作规范与术语表
├── mcp/
│   ├── tsecbench_mcp.py            # 零依赖 MCP 服务器（单文件）
│   ├── README.md                   # 工具参考、配置与沙箱部署
│   └── tests/                      # 离线 mock 与集成测试
├── docker/                         # 镜像构建、启动编排与网关
├── plugin/                         # Claude Code 插件与权限钩子
├── skills/                         # 技能库与导航索引
├── build/                          # 文档整理与配置扫描辅助脚本
└── .githooks/                      # 本地预推钩子（禁止直推 main）
```

---

## 资料出处与可信度

本仓库严格区分“平台官方声明”与“本仓库实测结论”：

| 来源 | 可信度 | 位置 |
|------|--------|------|
| 平台官方文档（API、SDK、Agent 提示词与三种模式页面） | 权威，但存在已知偏差 | `docs/`；本仓库补充处标注“增补” |
| 线上实测探测（2026-10-16） | 高，可复现 | `docs/challenges-api.md` §0 |
| 站点侦察（路由、试题集与赛事规则） | 中，平台改版后可能失效 | `docs/platform-modes.md` |
| `recon/` 下的前端 bundle | 原始未加工 | 未跟踪，仅供追溯 |

**已实测校准的三处结论**（详见 [§0](docs/challenges-api.md)）：

1. 缺失 `BENCHMARK_TOKEN` 头返回 **422**（框架校验），而非官方文档记载的 404 `task_not_found`。实现时必须区分“缺失”与“无效”两种情况。
2. `invalid_state` 以同一个 HTTP 409 与同一个 code 表达三种语义（名额已满、题目已通关、任务已结束），只能通过 `message` 区分；其中仅“任务已结束”为致命错误。
3. 平台不暴露 OpenAPI schema（`/openapi/openapi.json` 与 `/openapi/docs` 均返回 404），且 API 与站点同源。

**验证状态**：本仓库未取得真实 `BENCHMARK_TOKEN`，因此尚未执行过真实跑分。上述接口字段、错误码与状态机语义均来自平台官方文档；错误行为的触发与分流逻辑已通过 `mcp/tests/mock_tsec_api.py` 离线验证，但未经真实平台端到端确认。取得 token 后，应首先执行 `vpn_check` 与 `list_challenges` 完成真机连通性验证。

---

## 后续工作

- [ ] 取得 `BENCHMARK_TOKEN` 后执行一次真机端到端验证（`vpn_check` → `list_challenges`）。
- [ ] 使用真机响应校对 `docs/challenges-api.md` §0 的实测结论。
- [ ] 确认其余试题集的 `suiteId`（目前仅确认 TSecBench v1 = 4）。
- [ ] 将 MCP 打包进 Agent 镜像，在其他题集的托管模式下完成全链路验证（正式赛仅有一次机会）。

---

<sub>本仓库资料由 Agent 于 2026-10-16 抓取与整理，非腾讯官方发布。平台内容版权归腾讯所有；对外分享时请保留本出处说明。</sub>

## 贡献

本仓库只接受 Pull Request，Issues 与 Discussions 已关闭；提交前请阅读 `CONTRIBUTING.md`（英文，含中文摘要）。

## 许可证

本项目原创内容——`mcp/`、`docker/`、`build/`、`plugin/`、`docs/`、`skills/kit/` 下的自研技能与方法论文档，以及项目文档——由 James 与 minc 版权所有（2026），采用 **Apache License 2.0**（根目录 `LICENSE`），署名声明见 `NOTICE`。

第三方内容保留其上游许可证：

- `skills/` 技能库汇集了 9 个公开仓库与 PayloadsAllTheThings 快照。各来源的许可证、固定 commit 与逐目录证据见 `THIRD_PARTY_NOTICES.md`（英文）；自带 `LICENSE` 的目录以该文件为准。
- 固定版本工具包（`docker/tools/releases/`）：Nikto 2.6.1 按上游条款原样再分发（代码为 GPL-3.0-only 并附附加条款；数据库文件不适用 GPL，仅限随官方包分发；内置 LibWhisker 为 BSD-2-Clause，均见包内 `COPYING` 与 `COPYING.LibWhisker`）；Ghidra（Apache-2.0）与 JADX（Apache-2.0）为可选包，未纳入本仓库。`docker/tools/LICENSES-and-NOTICES.md` 保留团队工具包的来源记录。
- 构建期依赖（Debian 系统包、Python 包、npm 包）由 `docker/Dockerfile` 安装，各自遵循其许可证。
- 许可信息可机器读取：`REUSE.toml` 为每个路径映射 SPDX 许可与版权人，`LICENSES/` 收录许可全文，仓库通过 `reuse lint`（REUSE Specification 3.3）。

**合规提示：** 本仓库不包含任何专有许可的技能内容。原先引入的 Anthropic `pdf` 技能因许可禁止在 Anthropic 服务之外保留与再分发，已于 2026-10-20 移除。详见 `THIRD_PARTY_NOTICES.md` 的 “Compliance flags” 章节。

> English: see the “License” section of `README.md` and the full inventory in `THIRD_PARTY_NOTICES.md`.

## 免责声明

本项目仅用于**教学、研究、CTF 竞赛与授权安全测试**。未经事先书面授权，不得将本仓库的技能、脚本或载荷用于任何系统，否则可能违反《中华人民共和国网络安全法》《数据安全法》《刑法》等法律法规。维护者**与任何第三方将本项目用于非合规用途无关**，不构成同意、授权、协助或背书，亦不承担相关责任；该等行为由行为人独立承担全部责任。本项目适用**中华人民共和国法律**，争议提交维护者住所地（广东省江门市）有管辖权的人民法院解决。详见 `DISCLAIMER.md`（中文版本为正式文本）。

**竞赛使用限制：** 除维护团队及其书面授权的成员外，任何第三方**不得直接使用本仓库**参加与本项目目标赛事同类的比赛或评测（以自主 Agent 攻防能力、渗透测试能力或安全智能体能力为评测对象）。第三方自行创作的**衍生物不受此限**。

> English: this project is for education, research, CTF, and authorized security testing only; the maintainers are not responsible for non-compliant third-party use. Except for the maintainers and their authorized members, no third party may **directly use** this repository in competitions of the same kind; derivative works created by third parties are not restricted. Governed by the laws of the People's Republic of China. See `DISCLAIMER.md`.
