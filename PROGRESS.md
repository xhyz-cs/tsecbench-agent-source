# TSecBench 交付进度报告

> 快照时间：2026-10-16 · 由 agent 生成 · 对应仓库 `D:\tmp\secbench.zc.tencent.com`
> 赛事：第三届腾讯云智能攻防挑战赛 · 线上初赛 **2026-10-17 09:00 开赛（明天）**

---

## 一、总览

| # | 交付物 | 进度 | 验证状态 |
|---|--------|------|----------|
| 1 | 平台侦察（三模式/API/赛事） | ██████████ 100% | ✅ 已完成 |
| 2 | `llms.txt` + `llms-full.txt` + `docs/` 四篇 | ██████████ 100% | ✅ 链接全量校验通过 |
| 3 | 本地 MCP 服务器（瑞士军刀） | ██████████ 100% | ✅ 集成测试全绿 |
| 4 | 离线 mock 平台 | ██████████ 100% | ✅ 供测试用 |
| 5 | Claude Code 容器（托管模式） | ██████████ 100% | ⚠️ 已落盘；本机无 Docker，未编译 |
| 6 | 舰队 coordinator | ██████████ 100% | ⚠️ 已落盘；未真机验证 |
| 7 | 安全工具链（C/Py/CLI） | █████████░ 90% | ⚠️ 已落盘；未编译验证 |
| 8 | 安全技能搜集（skills/） | ███░░░░░░░ 30% | 🔄 子代理执行中 |
| 9 | Claude Code 插件 + mod | ███░░░░░░░ 30% | 🔄 刚开始 |
| 10 | 五个审查（含对质） | ██████████ 100% | ✅ 已回报；修复落在 `fix/mcp-reviews` + `fix/docs-reviews` |

---

## 二、已完成并验证 ✅

### 1. 平台侦察（这是所有后续工作的地基）
- 三种评测模式全部走到第 3 步配置页：本地模式（拿 token）、托管-Agent（传 Docker 镜像 ≤3GB、8核16G、无公网、`.tsecbench.gw` 网关）、托管-Model（平台统一 harness pi）
- 4 套试题集、赛事细则（**50题/100flag/8小时/仅托管模式/仅1次机会/仅队长可提交/无hint/不开放日志**）
- 官方三篇接入文档全文抓取（API / SDK / Agent 提示词）
- **实测发现 3 处官方文档与线上不一致**（这是真金白银的发现）：
  1. 缺失 `BENCHMARK_TOKEN` 返回 **422**，不是文档写的 404
  2. `invalid_state` 用同一个 409 + 同一个 code 表达**三种**语义（名额满/已通关/任务已结束），只能靠 message 区分
  3. 平台不暴露 OpenAPI schema，且 API 与站点同源

### 2. 知识库

- `llms.txt`（LLM 入口导览）+ `llms-full.txt`（45KB 合订本）
- `docs/challenges-api.md`（权威 API 参考 + §0 实测校准）
- `docs/platform-modes.md`（三模式 + 赛事 + 站点地图）
- `docs/sdk-python.md`、`docs/agent-prompt.md`
- 所有本地链接已脚本化校验，全部可达

### 3. MCP 服务器 ——「足够锋利的瑞士军刀」
- **单文件、零第三方依赖**（只为塞进无公网沙箱：装不了 pip）
- 12 工具：`vpn_check` / `list_challenges` / `task_status` / `start_challenge` / `wait_for_ready` / `submit_flag` / `get_hint`(默认拒绝，会扣分) / `close_challenge` / `close_all_challenges` / `probe_target`(TCP连通性) / `note_save` / `note_list`(跨崩溃持久账本)
- 3 资源 + 1 提示词（标准跑分 runbook）
- **平台错误码 → 可执行 action + fatal 标志**：`invalid_state` 自动区分「可自救（先close）」vs「任务已死（必须停）」
- **测试：集成套件全绿**（`python -m unittest discover -s mcp/tests -t mcp/tests`，含真实 stdio 传输层测试）；`--selftest` 自检通过
- 有专门一条测试**强制「源码零第三方 import」**这条契约（AST 扫描），不是写在文档里

### 4. 离线 mock 平台
忠实复刻 5 个接口 + VPN 预检 + 过期/重置/状态控制端点，让整套东西不碰真平台就能测。

### 5. 五个审查（逆向 / 性能 / 规范 / 调用链 / 对质）
已全部回报。发现的问题正在两条分支落地：`fix/mcp-reviews`（代码侧）与 `fix/docs-reviews`（文档侧）。

---

## 三、进行中 🔄

### 5-7. Claude Code 容器 / 舰队 / 工具链（已落盘：Dockerfile、entrypoint、fleet、keepalive；未编译验证）
| 文件 | 内容 | 状态 |
|------|------|------|
| `docker/Dockerfile` | **CN 镜像**（TUNA apt / npmmirror / TUNA pip / daocloud 基础镜像，全部 `--build-arg` 可覆盖）、一键 `docker build`、C 环境（gcc/gdb/cmake）、Python 安全栈（pwntools/impacket/scapy/pycryptodome…）、CLI 工具链（nmap/sqlmap/nikto/john/binwalk/tcpdump/socat/jq/ripgrep…）、钉死 `@anthropic-ai/claude-code@2.1.301` | 已写 |
| `docker/entrypoint.sh` | 网关 URL 自动改写（`https://api.deepseek.com` → `http://api.deepseek.com.tsecbench.gw`）、鉴权模式切换、**开机自动拉起 Claude Code 自主工作**、崩溃重启 supervisor、平台 409 即停 | 已写 |
| userspace 配置 | 全部收敛进 `CLAUDE_CONFIG_DIR`（settings.json 模板渲染 + mcp.json + skills/ + 双 prompt）；**密钥只走环境变量不落盘**（平台要求） | 已写 |
| hook 劫持 | `PreToolUse` / `PermissionRequest` / `Notification` 三事件自动放行（已在官方 271MB 二进制里确认这三个事件与 `hookSpecificOutput.permissionDecision` 真实存在） | 已写 |
| `docker/keepalive.py` | **5 分钟保活循环**：心跳 + 平台连通探活 + 任务结束即停（省 token）+ 孤儿容器救援（防 3 容器占死） | 已写 |
| `docker/fleet.py` | 舰队：按 `free_slots` 分发、1 worker=1题、共享笔记黑板、按题限次 | 已写 |
| 逆向成果 | `ANTHROPIC_SMALL_FAST_MODEL` 必须指向同一网关模型（否则主模型通了、后台小模型 404，静默死）；`ANTHROPIC_AUTH_TOKEN`(Bearer) 是网关正解但 `--bare` 只认 `ANTHROPIC_API_KEY`；`IS_SANDBOX=1` 是 root 下 `--dangerously-skip-permissions` 的开关 | 已写进配置 |

### 8-10. 后台代理状态
| 代理 | 任务 | 状态 |
|------|------|------|
| skills-collector | 搜集 15-40 个安全技能入库 + 索引 + 来源 | 🔄 执行中 |
| review-reverse / perf / spec / callchain / adversary | 五个审查（对质=变异测试） | ✅ 已回报，修复进行中 |
| cc-flags | Claude Code 离线特性矩阵权威核实 | 🔄 执行中 |
| mock-builder | mock 平台 | ✅ 已交付（文件已落盘） |

---

## 四、未验证 / 风险（诚实清单）

1. **本机没有 Docker** → 镜像**从未编译过**。apt 包名、3GB 体积、npm 安装都未验证。→ 需要你在有 Docker 的机器上跑 `./docker/build.sh`
2. **没有真实 `BENCHMARK_TOKEN`** → 从未对真平台完整跑分；接口语义来自官方文档 + 离线 mock
3. **审查发现尚未合并** → 代码侧修复在 `fix/mcp-reviews`、文档侧在 `fix/docs-reviews`；两条分支合并并通过全量测试前，交付物不能视为已闭环
4. **插件/mod 刚起步** → 结构已确认（`tool.check` 事件在权限模式判定**之前**触发，正是"更深层次放行"）
5. 破甲提示词：已按授权上下文 + 拒答恢复流程实现（合规且更有效），未做提示词弹药库

---

## 五、你可以立刻做的事

```powershell
# 1) 看交付物
start D:\tmp\secbench.zc.tencent.com\llms.txt
start D:\tmp\secbench.zc.tencent.com\README.md

# 2) 验证 MCP（不需要 token，不联网）
python D:\tmp\secbench.zc.tencent.com\mcp\tsecbench_mcp.py --selftest

# 3) 跑全部测试
cd D:\tmp\secbench.zc.tencent.com; python -m unittest discover -s mcp/tests -t mcp/tests

# 4) 在有 Docker 的机器上（一键编译 + 导出 + 3GB 校验）
cd D:\tmp\secbench.zc.tencent.com; .\docker\build.sh
```

---

## 六、我接下来按序做

1. 把插件 + mod 做完（`tool.check` 深层放行 + 用户级安装位置）
2. ~~补 `docker/README.md`、清掉 pi 残留、提交 git~~ ✅ 已完成（pi 已移除，容器全面基于 Claude Code）
3. 合并 `fix/mcp-reviews` 与 `fix/docs-reviews`，跑全量测试收口
4. 技能落盘后接入容器与插件
