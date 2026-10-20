# TSecBench Agent — Source Repository

**Authors / 作者:** James, minc  
**School / 学校:** Jiangmen Xinhui No. 1 Middle School / 江门市新会第一中学  
**Repository purpose / 仓库用途:** Uncompiled source for the TSecBench hosted Agent image; this repository is private.

**License / 许可证:** Apache License 2.0 for the original project contributions (`LICENSE`, `NOTICE`); third-party files remain subject to their own licenses and notices (`THIRD-PARTY-NOTICES.md`).

## 中文

### 项目介绍

本项目是面向 TSecBench 托管式 Agent 评测的 Claude Code 容器镜像源码。它把平台接入 MCP、Claude Code 启动与舰队编排、API 网关适配、技能库、分析工具和测试集中在一个可复现的 Docker 构建上下文中。仓库保存源码、配置模板、文档和测试，不包含已构建的 Agent 镜像；运行凭证由评测平台或操作者在运行时注入。

### 架构

1. **容器构建层（`docker/Dockerfile`）**：固定 Claude Code 与 Chrome DevTools MCP 版本，安装系统/Python 工具链；复制 MCP、技能、插件和运行配置。Ghidra/JADX 是可选本地发行包，Nikto 为 Docker 构建所需的固定发行包；大型可选压缩包未纳入 Git，校验摘要见 `docker/tools/releases/SOURCES.sha256`。
2. **启动与运行编排（`docker/entrypoint.sh`、`docker/fleet.py`）**：启动时整理工作目录与 Claude 配置，运行预检与工具链检查，再启动单个 Agent 或按 `TSEC_WORKERS` 编排多个 Claude Code worker；收集进程和任务日志并处理生命周期。
3. **平台接入与状态（`mcp/tsecbench_mcp.py`）**：零第三方 Python 依赖的 MCP 服务，封装平台任务查询、启动/关闭、提示、Flag 提交、目标探测及持久笔记等工具，并提供离线自检和测试。
4. **模型 API 适配（`docker/tsec_gw.py`）**：处理 Claude Code 到兼容模型 API 的请求适配与运行日志；API 地址、模型和密钥由环境变量提供，不在镜像或仓库中固化。
5. **Agent 行为层（`docker/claude/`、`plugin/`、`skills/`、`docs/`）**：Runbook、循环提示词、系统补充提示、Claude Code 插件命令、技能导航/参考库以及平台 API 文档。
6. **验证层（`mcp/tests/`、`docker/test_*.py`）**：通过离线 mock 和运行时测试检查协议分发、平台流程、环境变量、网关及启动路径。

### 主要功能

- 将平台任务 API 暴露为 Claude Code 可调用的 MCP 工具。
- 支持单 Agent 与多 worker 编排；`TSEC_WORKERS` 表示 Claude Code worker 数，不等同于 Claude Code 内部 subagent/teammate 配额。
- 支持 Anthropic 兼容模型 API 的运行时 URL、模型名和密钥配置；不把实际密钥写入 Docker 层。
- 启动前执行 MCP 自检、工具链预检和平台 keepalive 请求，并保留可诊断日志。
- 将提示词、平台文档和技能库分层挂载，避免每轮把整个知识库塞进上下文。
- 提供离线单元/集成测试，便于修改接入逻辑后复核。

### 构建与验证

在仓库根目录：

```bash
python mcp/tsecbench_mcp.py --selftest
python -m unittest discover -s mcp/tests -v
python -m unittest discover -s docker -p 'test_*.py' -v

docker build -f docker/Dockerfile -t tsecbench-agent:latest .
```

`docker/tools/releases/` 中的 Nikto 包及校验文件已纳入仓库。Ghidra/JADX 包为可选项；如需启用，请从各自官方发行源获取对应版本并按 `SOURCES.sha256` 校验后放入该目录。镜像导出示例见 `docker/build.sh`。

### 凭证与配置

复制 `.env.example` 并在本地填入测试值；真实 `.env` 不应提交。正式评测中的 `BENCHMARK_BASE_URL`、`BENCHMARK_TOKEN`、模型 API Key 等敏感值应由运行时环境注入。`.env.example` 仅展示变量名、说明和空值/占位符。

### 目录索引

- `docker/`：Dockerfile、entrypoint、worker 编排、模型网关、keepalive 与预检。
- `mcp/`：平台 MCP server 及离线测试。
- `plugin/`：Claude Code 插件与权限/钩子组件。
- `skills/`：技能目录、分类索引和参考内容。
- `docs/`：平台 API、模式、SDK 与 Agent 提示词说明。
- `build/`：文档整理及配置扫描辅助脚本。

## English

### Overview

This repository contains the **uncompiled source** for a Claude Code container image intended for TSecBench hosted Agent evaluations. It brings together platform MCP integration, Claude Code startup and worker orchestration, model API adaptation, skills, analysis tools, documentation, and tests in a reproducible Docker build context. The repository contains source, templates, docs, and tests—not a prebuilt Agent image. Runtime credentials are injected by the platform or operator.

### Architecture

1. **Image build (`docker/Dockerfile`)** — Pins Claude Code and Chrome DevTools MCP versions, installs the system/Python toolchain, and copies the MCP server, skills, plugins, and runtime configuration. Ghidra/JADX are optional local release packages; the pinned Nikto package is required for the Docker build. Large optional archives are not committed; checksums are listed in `docker/tools/releases/SOURCES.sha256`.
2. **Bootstrap and orchestration (`docker/entrypoint.sh`, `docker/fleet.py`)** — Prepares the work directory and Claude configuration, runs preflight/tool checks, then launches either one Agent or multiple Claude Code workers controlled by `TSEC_WORKERS`; it manages lifecycle and diagnostics.
3. **Platform integration (`mcp/tsecbench_mcp.py`)** — A Python-standard-library MCP server exposing task status, challenge start/close, hint, flag submission, target probing, and persistent notes, with offline self-tests and test coverage.
4. **Model API adapter (`docker/tsec_gw.py`)** — Adapts Claude Code requests to a compatible model API and records runtime diagnostics. API URL, model name, and key are supplied through environment variables, not baked into the image or source.
5. **Agent behavior (`docker/claude/`, `plugin/`, `skills/`, `docs/`)** — Contains runbooks, loop/system prompts, Claude Code plugin commands, skill navigation/reference material, and platform API documentation.
6. **Verification (`mcp/tests/`, `docker/test_*.py`)** — Offline mocks and runtime tests exercise protocol dispatch, platform workflows, environment handling, gateway behavior, and startup paths.

### Features

- Exposes platform task APIs as MCP tools callable by Claude Code.
- Supports single-Agent and multi-worker orchestration. `TSEC_WORKERS` controls the number of Claude Code worker processes; it is separate from Claude Code's internal subagent/teammate quota.
- Configures an Anthropic-compatible model API URL, model name, and key at runtime without embedding real credentials in image layers.
- Runs MCP self-tests, toolchain preflight, and platform keepalive requests before Agent startup, with diagnostic logs.
- Keeps prompts, platform docs, and the skill library modular rather than loading the entire knowledge base into every context window.
- Includes offline unit/integration tests for changes to platform integration and startup behavior.

### Build and test

From the repository root:

```bash
python mcp/tsecbench_mcp.py --selftest
python -m unittest discover -s mcp/tests -v
python -m unittest discover -s docker -p 'test_*.py' -v

docker build -f docker/Dockerfile -t tsecbench-agent:latest .
```

The pinned Nikto archive and checksum file are included. Ghidra/JADX are optional; to enable them, obtain the matching releases from their official distribution sources, verify them against `SOURCES.sha256`, and place them in `docker/tools/releases/`. See `docker/build.sh` for image export.

### Credentials and configuration

Use `.env.example` as a template and keep any real local `.env` out of version control. Production values such as `BENCHMARK_BASE_URL`, `BENCHMARK_TOKEN`, and the model API key should be injected at runtime. `.env.example` contains variable names, explanations, and blank/placeholder values only.

### Repository map

- `docker/` — Dockerfile, entrypoint, worker orchestration, model gateway, keepalive, and preflight.
- `mcp/` — Platform MCP server and offline tests.
- `plugin/` — Claude Code plugins and hook/permission components.
- `skills/` — Skill catalog, indexes, and reference material.
- `docs/` — Platform API, modes, SDK, and Agent prompt documentation.
- `build/` — Documentation and configuration-scan helper scripts.

## License

The original project contributions — `mcp/`, `docker/`, `build/`, `plugin/`, `docs/`, the in-house skills under `skills/kit/` with their methodology notes, and the project documentation — are Copyright 2026 James and minc and licensed under the **Apache License 2.0** (`LICENSE`). Attribution notices are in `NOTICE`.

Everything vendored from third parties keeps its upstream license:

- The skill library under `skills/` aggregates nine public collections plus a PayloadsAllTheThings snapshot. Per-source licenses, pinned commits, and per-directory evidence are inventoried in `THIRD-PARTY-NOTICES.md`; any directory that ships its own `LICENSE` file is governed by that file.
- Pinned tool releases (`docker/tools/releases/`): Nikto 2.6.1 is redistributed unmodified under its upstream terms; Ghidra and JADX are Apache-2.0 and are not committed to this repository.
- Build-time dependencies (Debian packages, Python packages, npm packages) are installed by `docker/Dockerfile` and carry their own licenses.

**Compliance note:** The repository ships no proprietary skill content. The Anthropic `pdf` skill that was originally vendored was removed on 2026-10-20 because its license prohibits redistribution. See "Compliance flags" in `THIRD-PARTY-NOTICES.md`.

### 许可证（中文）

本项目原创内容——`mcp/`、`docker/`、`build/`、`plugin/`、`docs/`、`skills/kit/` 下的自研技能与方法论文档，以及项目文档——由 James 与 minc 版权所有（2026），采用 **Apache License 2.0**（`LICENSE`），署名声明见 `NOTICE`。

第三方内容保留其上游许可证：

- `skills/` 技能库汇集了 9 个公开仓库与 PayloadsAllTheThings 快照；各来源的许可证、固定 commit 与逐目录证据见 `THIRD-PARTY-NOTICES.md`（英文）；自带 `LICENSE` 的目录以该文件为准。
- 固定版本工具包（`docker/tools/releases/`）：Nikto 2.6.1 按上游条款原样再分发；Ghidra 与 JADX 为 Apache-2.0，且未纳入本仓库。
- 构建期依赖（Debian、Python、npm 包）由 `docker/Dockerfile` 安装，各自遵循其许可证。

**合规提示：** 本仓库不包含任何专有许可的技能内容。原先 vendor 的 Anthropic `pdf` 技能因许可禁止再分发,已于 2026-10-20 移除。详见 `THIRD-PARTY-NOTICES.md` 的合规章节。

---

**Authors / 作者:** James, minc · **School / 学校:** Jiangmen Xinhui No. 1 Middle School / 江门市新会第一中学

