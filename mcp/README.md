# tsecbench-mcp

一个零依赖（纯标准库）的本地 MCP 服务器，将 TSecBench 的 Challenges API 封装为 Agent 可直接调用的工具。

```
mcp/
├── tsecbench_mcp.py            # 服务器本体（单文件，无第三方依赖）
├── README.md                   # 本文件
└── tests/
    ├── mock_tsec_api.py        # 离线 mock：忠实复刻平台 API 与 VPN 预检
    ├── test_tsecbench_mcp.py   # 集成测试（unittest，逐条打真实 HTTP）
    └── README.md               # mock 的端口布局、夹具与 _test 控制端点
```

---

## 设计约束：单文件与纯标准库

该服务器面向评测沙箱环境。托管模式（`mode=hosted`）的沙箱没有任何公网访问，
只能使用平台的大模型网关，且无法执行 `pip install`。因此：

- 服务器本体零第三方依赖（仅使用 `urllib` / `socket` / `json`），全部实现位于单个文件，`COPY` 进镜像即可使用；
- 测试同样使用 `unittest`，理由相同：沙箱中无法安装 pytest；
- MCP 的 stdio 传输（换行分隔的 JSON-RPC 2.0）由本服务器自行实现，不依赖 `mcp` SDK；
- `tests/test_tsecbench_mcp.py::TestStdlibOnlyContract` 会用 AST 解析源码、断言不存在任何第三方 import；
  该契约由测试强制执行，而非仅记录于文档。

该服务器在本机开发环境中同样可以运行（本地模式调试），不需要虚拟环境。

---

## 快速开始

无需安装任何依赖：

```bash
# 自检：验证协议装配与纯逻辑，不联网、不需要 token
python mcp/tsecbench_mcp.py --selftest
```

配置以下两个环境变量后，即可作为 stdio MCP 服务器运行：

```bash
export BENCHMARK_BASE_URL="https://tsecbench.zc.tencent.com"   # 平台下发的 Base URL
export BENCHMARK_TOKEN="<平台下发的 UUID>"                      # 托管模式下由平台自动注入
python mcp/tsecbench_mcp.py
```

### 注册到 Claude Code

```bash
claude mcp add tsecbench \
  --env BENCHMARK_BASE_URL=https://tsecbench.zc.tencent.com \
  --env BENCHMARK_TOKEN=<uuid> \
  -- python /abs/path/to/mcp/tsecbench_mcp.py
```

### 注册到其它 MCP 客户端（Claude Desktop / Cursor / 自研 harness）

```json
{
  "mcpServers": {
    "tsecbench": {
      "command": "python",
      "args": ["/abs/path/to/mcp/tsecbench_mcp.py"],
      "env": {
        "BENCHMARK_BASE_URL": "https://tsecbench.zc.tencent.com",
        "BENCHMARK_TOKEN": "<uuid>"
      }
    }
  }
}
```

---

## 工具一览

共 12 个工具。`annotations` 中的 `readOnlyHint` / `destructiveHint` 是面向客户端的提示，
本表“副作用”一列以直白表述描述同一信息。

| 工具 | 参数 | 副作用 | 说明 |
|------|------|--------|------|
| `vpn_check` | — | 无 | 请求 `TSEC_VPN_CHECK_URL`（默认 `http://10.0.100.58`，HTTP 且仅在 VPN 内可达），`status=="ok"` 才算通过。该检查是跑分前的强制第一步。该请求不会携带 token；预检端点位于靶场网内，不属于平台域。 |
| `list_challenges` | `only_incomplete`、`difficulty`、`sort_by` | 无 | 列出题目及每题进度。默认按 `level` 升序（由易到难）。 |
| `task_status` | — | 无 | 总览：通关/部分/未开始题数、flag 进度、满分、活跃容器、剩余名额、下一批候选题。 |
| `start_challenge` | `unique_code` | 占用 1 个活跃名额 | 启动容器。超限报 `invalid_state`，此时返回体中附带当前活跃题目列表，便于直接确定需要关闭的题目。 |
| `wait_for_ready` | `unique_code`、`timeout_s`、`interval_s` | 无 | 指数退避轮询到 `available`（`timeout_s` / `interval_s` 自动限制到安全范围）。容器从 `pending` 拉起需要时间，启动后不应立即开始解题；容器已停止则直接返回本地错误码 `container_not_running`。 |
| `submit_flag` | `unique_code`、`flag` | 写分数 | 逐个提交 flag。错误 flag 返回正常的 200（`correct:false`），不作为异常。 |
| `close_challenge` | `unique_code` | 释放资源 | 通关后或放弃时必须调用，否则活跃名额会一直被占用。 |
| `close_all_challenges` | `confirm` | 释放资源 | 批量释放。默认只列出将关闭的题目；`confirm=true` 才执行。 |
| `get_hint` | `unique_code`、`confirm_deduction` | 扣分 | 默认拒绝执行，`confirm_deduction=true` 才发起实际请求。 |
| `probe_target` | `host`、`port`、`timeout_s` | 无 | TCP 连通性探测。沙箱内没有 `nc`/`curl` 时，用该工具区分 VPN 中断与目标服务未启动。 |
| `note_save` | `key`、`value` | 写本地文件 | 追加写入纯文本 JSONL 账本（`TSEC_STATE_DIR`）。 |
| `note_list` | `key`、`limit` | 无 | 读回账本，支持按 key 过滤。 |

### 资源与提示词

| 类型 | 名称 | 内容 |
|------|------|------|
| resource | `tsecbench://docs/challenges-api` | 平台 API 权威参考（含实测校准）。 |
| resource | `tsecbench://docs/agent-prompt` | 平台官方 Agent 提示词原文。 |
| resource | `tsecbench://task/state` | 实时任务进度 JSON。 |
| prompt | `tsecbench_solve_flow` | 标准跑分 runbook，可选 `focus` 聚焦某题。 |

资源文件不可读时，服务器退化为内置的精简版本，不会因缺少文件而失效。

---

## 统一响应契约

所有工具返回同一 JSON 形状，成功与失败时结构一致，Agent 只需编写一次解析逻辑：

```json
{
  "ok": true,
  "...": "各工具自己的字段"
}
```

```json
{
  "ok": false,
  "http_status": 409,
  "code": "invalid_state",
  "message": "max active challenge instances reached",
  "detail": {},
  "action": "活跃题目实例已达上限（3）。先 close_challenge 释放一道题再重试 start；任务状态可用 task_status 查看。",
  "fatal": false,
  "active_containers": ["web_sql_injection_01", "crypto_rsa_02", "pwn_heap_03"]
}
```

工具结果一律是紧凑 JSON（无 pretty-print）；stdio 传输层每行一个 JSON-RPC 响应。
关键字段为 `action`（可执行的下一步）与 `fatal`（是否必须停止整个跑分流程）。
这两项是本服务器的主要价值：平台只提供错误码，本服务器给出处置决策。

### 错误码与处置

| `code` | `fatal` | 处置 |
|--------|---------|------|
| `task_not_found` | true | token 无效/任务不存在。停止并报告。 |
| `invalid_state`（message 含 `max active`） | false | 名额满。先 close 再 start，可自行恢复。 |
| `invalid_state`（message 含 `completed`） | false | 该题已通关，取 hint 被拒绝。跳过 hint。 |
| `invalid_state`（其它） | true | 任务已结束（超时/停止）。立即停止全流程并报告。 |
| `duplicate` | false | 该 flag 已计分。跳过，不重试。 |
| `challenge_not_found` | false | code 拼写错误或不属于本任务。跳过。 |
| `resource_unavailable` | false | 靶场资源未就绪。稍后重试 start，或更换题目。 |
| `internal_error` | false | 重试一次；持续则报告。 |
| `missing_local_config` | true | 未配置 `BENCHMARK_TOKEN`。按 `action` 中的路径在平台领取。 |
| `confirmation_required` | false | 该操作有代价（hint 扣分 / 批量关闭），确认后添加 `confirm*=true` 重新执行。 |
| `unreachable` / `local_timeout` | false | 网络层问题。先执行 `vpn_check`，区分 VPN 与服务故障。 |
| `container_not_running`（本地代码） | false | 该题容器已停止（未启动或已关闭）。先 `start_challenge` 再 `wait_for_ready`。 |

> `invalid_state` 的三种语义只能通过 `message` 区分（`max active` / `completed` / 其它）。
> 平台使用同一个 HTTP 409 + 同一个 code 表示“可自行恢复”与“任务已结束”两种完全不同的情况，
> 这是接入时最易出错之处，本服务器已完成分类。

### 协议层错误（JSON-RPC）

协议版本仅支持 `2025-06-18`。以下错误发生在协议层、先于任何工具调用，直接以 JSON-RPC error 返回：

| 场景 | JSON-RPC code |
|------|---------------|
| 请求不是合法 JSON | `-32700` |
| 批量请求（数组）、`id` 为数组或 `null` | `-32600` |
| 未知的 resource URI | `-32002` |
| 未知的 tool / prompt 名称 | `-32602` |

---

## 配置项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `BENCHMARK_TOKEN` / `TSEC_TOKEN` | — | 平台下发的跑分 token。托管模式下由平台自动注入容器，无需手动填写。 |
| `BENCHMARK_BASE_URL` / `TSEC_BASE_URL` | `https://tsecbench.zc.tencent.com` | 平台 API 根地址。 |
| `TSEC_VPN_CHECK_URL` | `http://10.0.100.58` | VPN 预检地址（靶场网内，非平台域）。 |
| `TSEC_MAX_ACTIVE` | `3` | 活跃题目上限。平台默认 3；修改该值仅影响提示文案与名额计算，不会改变平台真实限制。 |
| `TSEC_TIMEOUT` | `30` | 平台 API 单请求超时（秒）。VPN 预检另用 `min(该值, 10)`。 |
| `TSEC_STATE_DIR` | `<脚本目录>/.tsecbench-state` | 笔记账本目录（`notes.jsonl`）。 |

---

## 部署到评测沙箱（托管模式）

托管模式的镜像中通常只安装 Agent 自身的运行时。服务器为单文件零依赖，
接入成本为一次 `COPY`：

```dockerfile
# 你的 Agent 镜像
FROM python:3.12-slim            # 或任何自带 python3.9+ 的基座

COPY tsecbench_mcp.py /opt/tsecbench/tsecbench_mcp.py
COPY docs/ /opt/tsecbench/docs/          # 可选：让 MCP 资源带上完整文档

# 无需 pip install —— 服务器只用标准库

# 让你的 harness 把 /opt/tsecbench/tsecbench_mcp.py 注册为 stdio MCP server。
# BENCHMARK_TOKEN 与 BENCHMARK_BASE_URL 由平台自动注入，别再写进镜像。
ENV PYTHONUNBUFFERED=1
```

必须遵守以下三条沙箱约束：

1. 不得将 token、大模型 key 写入镜像；按平台要求通过环境变量录入（评测须知第 3 条）。
2. 不得依赖公网：镜像构建期可以联网安装依赖包，运行期不可以；所有大模型调用必须走
   `http://<原域名>.tsecbench.gw/...`（域名加 `.tsecbench.gw` 后缀、`https`→`http`）。
3. 容器必须在启动后自行开始解题，不存在外部触发。

---

## 测试

```bash
# 单元 + 协议层自检（不联网、不需要 token）
python mcp/tsecbench_mcp.py --selftest

# 集成测试：自动拉起 mock 平台，逐条打真实 HTTP
python -m unittest discover -s mcp/tests -t mcp/tests -v
```

集成测试覆盖：MCP 握手与 JSON-RPC 分发、12 个工具的正常路径、
活跃名额上限及其自救路径、`duplicate` 幂等、错误 flag 返回 200、
`invalid_state` 三种语义的分流、任务过期后全接口 fatal、未知 code 可跳过、
hint 的双重门禁（默认拒绝与已通关拒绝）、`probe_target` 可达/不可达、
笔记账本跨进程存活，以及“源码中不存在第三方 import”这条契约。

---

## 设计取舍

- 不在托管沙箱中直接使用 `pip install tsec-benchmark`（官方 SDK）的原因：
  官方 SDK 依赖 `httpx`，假定环境中可以安装第三方包——托管沙箱运行期没有公网、无法安装依赖包，SDK 在该环境不可用。
  MCP 的价值在于“让 Agent 自己决策”，不是“写一个跑分脚本”。
  两者不冲突：SDK 适合写死的解题流水线，MCP 适合让 Agent 边看进度边决定下一步。
- `get_hint` 默认拒绝执行的原因：该操作会不可逆地扣分。
  随意调用该工具的 Agent 会损失分数，因此代价明确的工具一律设置显式确认门禁。
- `task_status` 不报告“已得分”的原因：
  `/openapi/v1/challenges` 不返回 `cumulative_score`，因此 `task_status` 只报告平台确实提供的字段：`correct_flag_count` / `flag_count`。
  `submit_flag` 响应中虽包含 `cumulative_score`，但其口径——任务级总分还是单题累计得分——尚未对真实平台验证：
  官方 SDK 文档只写“累计已获得的总分数”（未说明范围），离线 mock 按任务级实现。第一次真机跑分时必须先核对这一字段，再决定是否依赖它。
- `TSEC_MAX_ACTIVE` 不会使人误以为可以调大限额：它只用于计算剩余名额与生成提示文案，
  真实上限由平台强制。文档中已写明。
