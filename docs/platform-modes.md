# TSecBench 平台使用方式（三种评测模式）

> 本文件是**实测侦察笔记**，记录 `https://tsecbench.zc.tencent.com/` 的实际使用路径与三种评测模式。
> 抓取时间：2026-10-16。平台改版可能导致路径变化，以站内为准。

平台定位：腾讯安全云鼎实验室推出的**自主 Agent 评测与验证基础设施**。
在真实任务、真实工具与可控的动态环境中，让结果可验证、过程可追溯、能力可比较。

---

## 1. 站点地图

| 路径 | 内容 |
|------|------|
| `/` | 首页：评测理念、**Agent/Model 榜单**、评测动态、公开评测研究、**接入指引**（含 3 篇接入文档弹窗）、Challenges API 文档面板 |
| `/benchmark` | 开始评测：第 1 步「选择试题集」 |
| `/benchmark/mode/{suiteId}` | 第 2 步「选择评测方式」（三种模式） |
| `/benchmark/prepare/{suiteId}?mode={mode}&evaluation_type={type}` | 第 3 步「配置 & 接入」：填 Agent 信息 / 上传镜像 / 配模型 API，并**签发凭证** |
| `/benchmark/run/...` | 第 4 步「运行评测」：部署与运行日志（需先创建任务） |
| `/events` | 赛事活动：限时赛事、积分走势、战队榜、赛事细则 |
| `/resources` | 学习资源：实时同步 GitHub 仓库 `Yeti-791/Awesome-Offensive-AI-Agentic-Landscape`（前端走 `/api/v1/learning-resources/readme`） |
| `/agent/{id}` | 单个 Agent 的评测详情 |
| `/#leaderboard` | 首页榜单锚点 |

鉴权：站点用登录态 Cookie（腾讯云账号）。开放 API 用 `BENCHMARK_TOKEN` 请求头，**与站点 Cookie 无关**。

---

## 2. 试题集（截至 2026-10-16 可选的 4 套）

| 试题集 | 题目/flag | 单次限时 | 开闭卷 | 来源 |
|--------|-----------|----------|--------|------|
| **Tsecbench v1** | 63 / 74（列表面板另示 63 题、23000 总积分） | 6h | 闭卷 | 云鼎实验室自研旗舰集，覆盖 Web 漏洞挖掘、二进制漏洞挖掘、漏洞利用、多阶段渗透、云攻击、对抗规避 6 大能力域 |
| **bctf-2026** | 37 / 37 | 6h | 闭卷 | 百度 2026「Agent+」攻防能力挑战赛题集，已全面开放 |
| **XBOW Validation Benchmarks** | 104 / 104 | 6h | **开卷** | XBOW 联合多家渗透厂商研发的 Web 安全基准，104 个原创 Web CTF，覆盖 20+ 类漏洞 |
| **Cybench** | 40 / 40 | 6h | 开卷 | 斯坦福 RegLab 与 CRFM 的 AI 网络安全评估框架，论文入选 ICLR 2025 |

> 实测 `Tsecbench v1` 的 `suiteId = 4`（`/benchmark/mode/4`）。其余 id 未探明，从界面点击进入即可。

---

## 3. 三种评测模式（第 2 步的选择）

三种模式**共用同一套试题集与排行榜体系**。路由以 `mode` 与 `evaluation_type` 两个 query 参数区分。

### 3.1 本地模式（`mode=local`，`evaluation_type=agent`）

> 定位：**开发 / 调试 Agent、评测他人程序、结果仅供自己参考。**

- 在你自己的环境运行 Agent，通过 VPN 访问题目，与平台 API 交互完成评测。
- 特点：**零成本接入、可本地实时调试**；**无防作弊机制，成绩仅供自己参考**。
- 接入步骤：选 Agent → 勾选评测协议 → 点「**获取接入配置，开始评测**」→ 平台签发**唯一凭证 Token 与 Base URL** 并跳转评测页。
- 拿到 `BENCHMARK_TOKEN` + `BENCHMARK_BASE_URL` + 靶场 VPN 后，即可走 [Challenges API](challenges-api.md)。
- **这是托管模式的前置步骤**：官方明确要求「务必先完成本地模式评测（Agent 已接入平台答题 API），再进行托管模式评测」。

### 3.2 托管模式 - Agent 评测（`mode=hosted`，`evaluation_type=agent`）

> 定位：**正式打榜**。已在本地模式完成评测、想拿官方认证成绩时使用。

页面标题：「环境配置，上传程序」。三步：

**① 接入大模型网关**
托管环境**无法访问任何公网地址**，必须把程序里所有大模型 API 地址改走平台网关：

0. 先确认所用大模型 API 在《大模型 API 白名单》内（页面列 22 项）；
1. 把**原域名加上 `.tsecbench.gw` 后缀**；
2. 原 URL 是 `https` 的，**改成 `http`**。

```
转换前：https://api.deepseek.com/v1
转换后：http://api.deepseek.com.tsecbench.gw/v1

转换前：https://api.moonshot.cn/v1
转换后：http://api.moonshot.cn.tsecbench.gw/v1
```

白名单（22 项，`*` 为通配）：
`api.hunyuan.cloud.tencent.com` / `api.lkeap.cloud.tencent.com` / `tokenhub.tencentmaas.com` / `api.deepseek.com` /
`dashscope.aliyuncs.com/compatible-mode` / `*.maas.aliyuncs.com/compatible-mode` / `*.maas.aliyuncs.com/apps/anthropic` /
`qianfan.baidubce.com` / `ark.cn-beijing.volces.com` / `open.bigmodel.cn` / `api.moonshot.cn` / `api.siliconflow.cn` /
`spark-api-open.xf-yun.com` / `api.minimaxi.com` / `api.stepfun.com` / `api.lingyiwanwu.com` / `api.baichuan-ai.com` /
`api.xiaomimimo.com` / `api.kimi.com` / `token.sensenova.cn` / `modelservice.jdcloud.com` / `console.cloudrouter.com.cn/v1`

**② 制作并上传 Docker 镜像**
- 上传格式：**`.tar` / `.tar.gz` / `.tgz`**，**最大 3GB**（`<input type=file accept=".tar,.gz,.tgz,.xz">`）。
- 导出命令：`docker save your-agent:latest | gzip > agent.tar.gz`
- **容器启动后必须自行开始解题**（无外部触发）。
- 可先选择已有 Agent，查看其「最近使用版本」的历次上传记录。

**③ 配置动态环境变量**
- **`BENCHMARK_TOKEN` 与 `BENCHMARK_BASE_URL` 由平台在任务创建后自动生成并注入容器**，无需手填；
  你的程序内部仍通过它们调用答题 API（与本地模式一致）。
- 其他密钥 / 大模型 API 等敏感配置**必须从程序包中剔除**，改为在此页以环境变量录入（支持「从 .env 导入」）。

**评测须知（原文要点）**
1. 平台为程序运行提供 **8 核 16G** 资源。
2. **务必先完成本地模式评测**（Agent 已接入平台 API），再进行托管模式评测。
3. 程序包内剔除动态、敏感配置，以环境变量读取并在此页配置。
4. 托管运行期间全程数据将被**审计与部分公开**（含网络流量、大模型对话记录）。
5. 程序运行在独立、一次性沙箱中，结束后立即销毁，平台不留存你的程序。
6. **Agent 不可内置针对题目的历史答题记忆或解题方法，一旦发现按作弊处置。**
- 提交后平台拉取镜像并自动部署沙箱，可在第 4 步实时查看部署 / 运行日志。

### 3.3 托管模式 - Model 基准评测（`mode=hosted`，`evaluation_type=model`）

> 定位：**模型能力评测**。用平台统一 Harness，排除用户 Harness 差异，横评不同模型。

「Model 基准评测配置」，需填：

| 字段 | 说明 |
|------|------|
| 基准 Harness * | 平台统一的 Harness，实测可选 `pi · 0.85.1`（Pi is a minimal agent harness, https://pi.dev/） |
| 大模型 API | 需在**白名单地址**内（与 3.2 同一份 22 项白名单） |
| `LLM_API_TYPE` * | `openai-completions` / `anthropic-messages` / `openai-responses` |
| `LLM_API_BASE_URL` * | 如 `https://api.deepseek.com`，须在白名单范围内 |
| `LLM_API_KEY` * | 模型 API KEY |
| `LLM_DEFAULT_MODEL` * | 模型名 |

评测须知：
1. 程序在独立、一次性沙箱运行，结束即销毁，**平台不留存你的大模型 API 信息**。
2. Model 基准评测过程（含 Agent trace、得分记录）**只有评测人自己能看到**。
3. 首页 Model 榜单经智能清洗与加权校准后综合计算，**单人单次结果不一定影响排行榜**。

---

## 4. 首页公开评测研究（对比数据）

首页提供「智能渗透 Agent 能力测评报告」的交互表格，字段：评测单位、评测轮次、**成功率**、答题总时间、总 Token 消耗。
覆盖 Agent：BreachWeave、CHYing、Cairn、Claude Code、CyberStrikeAI、LuaN1ao、Pentagi、PentestAgent、T3MP3ST、cai、ctfSolver、pi、shannon。
覆盖模型：deepseek-v4-pro-202606、glm-5.2、kimi-k3、minimax-m3。共 156 条记录。

评测说明（原文要点）：单题依次评测、每题独立运行；**每题最长运行 1 小时，超时视为未通过**；
统一评测环境、统一配置、统一评分规则，排除调度策略与答题顺序影响；后续逐步公开完整评测日志与大模型对话记录。

---

## 5. 赛事：第三届腾讯云智能攻防挑战赛（王座协议主赛场）

来源：`https://zc.tencent.com/hackathon` 与平台 `/events` 页。**这是本仓库队友当前要打的比赛。**

### 5.1 赛程

| 时间 | 环节 |
|------|------|
| 10 月 15 日 00:00 | 主赛报名截止 |
| **10 月 17 日 09:00 — 10 月 18 日 23:59** | **王座协议主赛 · 线上初赛**（TSecBench 平台托管运行，选拔 10 支战队） |
| 10 月 18 日 23:59 | 安全智子赛道报名截止 |
| 10 月 30 日 | 安全智子专项挑战赛 + 王座协议 AI-KOH 线下决赛 |

线下地点：深圳国际会展中心·北登录大厅 2F 媒体中心。
主赛总奖金 32 万元（一等奖 7 万 ×1、二等奖 5 万 ×2、三等奖 3 万 ×3、优秀奖 1 万 ×6）。

### 5.2 线上初赛规则（**决定实现方式，务必遵守**）

- **仅支持「托管模式 - Agent 评测」**，创建评测任务时选择本活动题集参赛。
- 活动期间**只有 1 次评测机会**，且**仅报名队伍的队长账号**可提交评测。
- 比赛期间若因 Agent 程序异常导致未能正常解题，**没有重试机会**——所以必须提前用其他题集跑通托管模式。
- 题目 **50 题 / 100 flag**，评测任务**限时 8 小时**，**题目无 hint**（hint 接口返回 `null`，且查看无惩罚）。
- 排名按 **得分 → 有效耗时 → token 量** 优先顺序。
- 活动截止后不可创建新任务；截止前已创建的任务（排队中/部署中/运行中）可继续运行至结束并计入成绩。
- **本活动不开放运行细节**：不可查看运行日志和 AgentTrace。
- 各评测任务独立计分（无一血、无得分递减机制）。
- 评测期间所选模型服务若出现限流、超时、中断或第三方故障，**不视为平台异常，不补发评测机会**。
- **严禁主观攻击平台，或预设引导 AI 攻击评测平台的提示词。违规取消成绩及参赛资格。**

### 5.3 对我们的直接含义

1. 交付物是**一个 Docker 镜像**（`.tar.gz` ≤3GB，`docker save` 导出），容器启动即自动解题。
2. 镜像内**不能有公网访问**；所有大模型调用必须走 `http://<域名>.tsecbench.gw`。
3. `BENCHMARK_TOKEN` / `BENCHMARK_BASE_URL` 由平台注入，程序从环境变量读取。
4. 敏感信息以环境变量录入，不写进镜像。
5. 不能内置题目记忆/解题方法库。
6. **必须在赛前用本地模式 + 其他题集的托管模式验证整条链路**——正式赛只有一次机会。
7. 无 hint，所以 hint 逻辑在赛中无用；但本地调试时可能有用（会扣分）。

---

## 6. 其他赛道（同一赛事，非主赛）

- **安全智子专项挑战赛**：本地模型离线运行，检验 Agent 在 NVIDIA DGX Spark 上的自主渗透能力。
  不调用云端大模型；通过材料评审遴选 8 支战队，每队配 2 台 DGX Spark；报名截止 2026-10-18 23:59。
- **智能漏洞挖掘挑战赛**：面向授权真实业务资产，以有效漏洞与过程记录证明 AI 实战贡献。
  需腾讯安全众测平台实名认证 → 申请获准 → 按要求接入。项目开放 10/10–10/26，测试及报告提交 10/12–10/26。
  有效漏洞赏金 + 符合规则的 AI 贡献额外 **30%** 加成，附加赏金池 30 万元。
