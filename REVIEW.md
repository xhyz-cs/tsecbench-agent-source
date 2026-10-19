# 人工检查引导（第一次）

> 生成时间：2026-10-17 凌晨 · 对应 master 最新提交（本文档随仓库演进）
> 今天 09:00 线上初赛开赛。下面按「值不值得花你的时间」排序。

---

## 0. 先跑这三条（2 分钟，全部应当绿）

```powershell
cd D:\tmp\secbench.zc.tencent.com
python -m unittest discover -s mcp/tests -t mcp/tests     # 期望: Ran 125 tests ... OK
python mcp\tsecbench_mcp.py --selftest                    # 期望: SELFTEST OK
node build\check-links.mjs                                # 期望: All local links resolve.
```

当前状态：**树干净（0 未提交）、125/125 测试、selftest 通过、链接全通。**

---

## 1. 【最重要·只有你能做】容器编译 —— 赛前必须验证

本机没有 Docker，**镜像从未编译过**。这是全部交付物中唯一没被验证过的关键路径。

```powershell
cd D:\tmp\secbench.zc.tencent.com
.\docker\build.sh          # 一键编译 + 导出 agent.tar.gz + 3GB 强制校验
```

重点人工判断的四个点（机器测不了）：

| 检查点 | 在哪 | 什么算过 |
|--------|------|----------|
| apt 包名是否都存在 | `docker/Dockerfile` 的 apt 块 | 构建不报 `Unable to locate package` |
| 镜像体积 | build.sh 末尾 | `< 3 GB`；超了就把 `docker/tools/releases/ghidra-*.zip` 移走再重建 |
| Ghidra/JADX 发行包 | `docker/tools/releases/` | 缺 zip 时构建**仍然成功**，但镜像里没有 ghidra-headless/jadx（entrypoint 探测会报出来） |
| `chrome-devtools-mcp` 参数 | `docker/claude/mcp.json` | 编译后跑一次 preflight（下条）确认它真的连上 |

编译成功后的离线冒烟（不需要 token、不需要模型）：

```bash
docker run --rm -e TSEC_PREFLIGHT_ONLY=1 \
  -e LLM_API_BASE_URL=https://api.deepseek.com -e LLM_API_KEY=dummy -e LLM_DEFAULT_MODEL=x \
  tsecbench-agent:latest
```

期望输出：`preflight: all MCP servers connected` + `TSEC_PREFLIGHT_ONLY=1 ... not launching`。
（chrome 那个 MCP 起不来时会变成 `required servers connected; dropped: ['chrome']` 加一条 WARN
—— 这是设计内的降级，容器照常启动。只有 tsecbench 那个 server 是必需的。）

---

## 2. 【你的地盘】三个提示词文件等你写

- `docker/claude/RUNBOOK.md` —— **核心提示词**：`claude --bg` 启动时给 agent 的那一条
- `docker/claude/LOOP_PROMPT.md` —— **loop 提示词**：agent 想收工时，Stop hook
  （`docker/claude/hooks/keep_working.py`）把它作为「继续干」的理由还给 agent。
  每次 Stop 都重新读；`SessionStart` 时也作为附加上下文注入一次
- `docker/claude/SYSTEM_APPEND.md` —— 追加进系统提示词（`--append-system-prompt`）

两个 md 开头的 HTML 注释只给你看，不会进入模型。改完重建镜像即生效。

跑分时的自主性由三层保障，互不重叠：前两层保证它**能**干活，第三层保证它**不停**。

| 层 | 在哪 | 挡掉什么 |
|----|------|----------|
| `--dangerously-skip-permissions` + `--permission-mode bypassPermissions` | entrypoint 的 common_flags | 权限模式层面的拦截 |
| `auto_allow.py` | settings.json 的 PreToolUse / PermissionRequest / Notification | 外层漏下来的确认框、弹窗 |
| `keep_working.py` | settings.json 的 Stop / SessionStart | **agent 想收工** —— 无人值守下真正致命的那一步 |

技能内容同理归你：`skills/`（982 个网上收集的，已审计）与 `plugin/tsecbench-agent/skills/`。

### 「会向人提问」的开关全部关掉了

无人值守下，任何等人回答的东西都等于把会话挂死。以下每一项都有官方文档依据：

| 开关 | 落在哪 | 挡掉什么 |
|------|--------|----------|
| `skipDangerousModePermissionPrompt: true` | settings.json | **最关键**：`claude --bg` + `bypassPermissions` 时，用户设置里没有它，bypass 会被**静默忽略**，会话退回会弹权限框的模式 |
| `askUserQuestionTimeout: "60s"` + `CLAUDE_AFK_TIMEOUT_MS=60000` | settings.json / ENV | 没人回答的提问**默认 `"never"`（永远挂着）**，改成 60s 后自动继续 |
| `--disallowedTools AskUserQuestion` | entrypoint / fleet 启动参数 | 那个只为「问人」而存在的工具，直接禁用 |
| `CLAUDE_CODE_AUTO_MODE_SERVER=0` | Dockerfile ENV | 不再请服务器复核 auto mode 动作 —— 沙箱网关不透传 `safeguards` 字段，问不通就卡 |
| `CLAUDE_CODE_AUTO_MODE_MODEL`、`CLAUDE_CODE_BG_CLASSIFIER_MODEL` | entrypoint 导出 | 分类器那次额外模型调用，指向网关里唯一存在的模型 |
| `skipAutoPermissionPrompt: true` | settings.json | auto mode 的首次确认弹窗 |

---

## 3. MCP 服务器（已由五审 + 对质验证过，抽查即可）

- 代码：`mcp/tsecbench_mcp.py`（单文件，零第三方依赖——有 AST 测试强制这条契约）
- 12 工具 / 3 资源 / 1 提示词；工具描述与提示词已是**英文引导式**（按你的要求）
- 验证强度：五审（规范/反向/调用链/性能/对质）+ **变异测试闭环**：
  初版 64% → 补 31 条缺口测试 98% → **对当前 master 定向复测 45/45 = 100%**
  （仅剩 2 个结构性等价变异体，无需动作）。14/14 缺口击杀表由对质代理在
  125 条测试基线（0F/0E/0S）上独立出具。

想真机冒烟（需要 token）：

```powershell
$env:BENCHMARK_BASE_URL="https://tsecbench.zc.tencent.com"; $env:BENCHMARK_TOKEN="<uuid>"
python -c "import sys; sys.path.insert(0,'mcp'); import tsecbench_mcp as m; print(m.tool_list_challenges())"
```

---

## 4. 技能库（已审计，抽查 2-3 个即可）

- `skills/INDEX.md` —— 982 个技能按六类题型映射，含路径/一句话/是否带脚本
- `skills/SOURCES.md` —— 9 个 pinned commit、筛除清单、全量扫描结论（**0 拒绝**）
- 建议抽查：`skills/09-web-security/`、`skills/03-exploit-development/` 里随便挑两个 SKILL.md
  读一读，确认内容质量符合你的预期（这些是社区内容，质量参差是常态）

---

## 5. 文档（已过链接检查与事实核对）

- `llms.txt` → `llms-full.txt`（合订本）→ `docs/` 四篇
- `README.md` —— 仓库总览 + 出处与可信度表
- `PROGRESS.md` —— 进度快照
- 已知修正记录：官方文档 3 处与线上不一致（`docs/challenges-api.md` §0，含可复现命令）

---

## 6. 已知问题（诚实清单）

| 问题 | 影响 | 缓解 |
|------|------|------|
| 镜像未编译 | 高 | 本机无 Docker；`build.sh` 已把可预见的失败点做成显式报错 |
| 未跑过真实跑分 | 高 | 无 token；接口语义来自官方文档 + 离线 mock；拿到 token 后先 `vpn_check` + `list_challenges` |
| `cumulative_score` 语义（单题 vs 任务级） | 低 | 文档已标注"未验证"，首次真机核对 |
| 审计扫描器脚本被清理 | 低 | 结论已固化进 `skills/SOURCES.md`；扫描器内容在我的上下文里，需要可还原 |
| `--bare` 模式会跳过插件/skills | 低 | 默认不开 bare；开了会打 WARN |

---

## 7. 赛前 checklist（我的建议顺序）

- [ ] `.\docker\build.sh` 编译通过 + 3GB 内
- [ ] `TSEC_PREFLIGHT_ONLY=1` 冒烟通过
- [ ] 写 `RUNBOOK.md` / `SYSTEM_APPEND.md`（你的提示词工程）
- [ ] 用**其他题集**的托管模式跑一次全链路（正式赛只有 1 次机会）
- [ ] 上传镜像
