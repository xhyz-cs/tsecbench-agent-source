# Contributing

This repository is maintained by students at Jiangmen Xinhui No. 1 Middle School.
We accept contributions **only as pull requests**. Issues and Discussions are
disabled on this repository.

## Why there are no issues or discussions

The maintainers are students and do not have time to run a triage queue: reading,
labeling, replying to, and chasing issues costs more time than reviewing a pull
request that already contains the change. A pull request keeps the whole proposal in
one place — the diff, the rationale, the test evidence, and the licensing
information — so it can be reviewed in a single pass. Questions about a change belong
in the pull-request description or in review threads, not in a separate tracker.

PRs may be reviewed with delay or declined without a detailed response; this is a
school project, not a supported product. Please do not open issues to ask for status
or to request features — open a pull request instead.

## Before you open a pull request

1. **Keep it focused.** One concern per pull request. Avoid mixing refactors with
   behavior changes.
2. **Run the tests.**
   ```bash
   python mcp/tsecbench_mcp.py --selftest
   python -m unittest discover -s mcp/tests -v
   python -m unittest discover -s docker -p 'test_*.py' -v
   ```
3. **Respect the licensing rules.**
   <!-- REUSE-IgnoreStart -->
   - Original code is Apache-2.0. New first-party source files must start with
     `SPDX-FileCopyrightText` and `SPDX-License-Identifier: Apache-2.0` headers.
   <!-- REUSE-IgnoreEnd -->
   - Do not add proprietary or non-redistributable material. The repository must not
     carry content whose license forbids retention or redistribution.
   - Vendored third-party content must keep its upstream license files. Record every
     addition or update in `THIRD_PARTY_NOTICES.md` and in `REUSE.toml`, and make sure
     the compliance check passes:
     ```bash
     uvx --from "reuse[charset-normalizer]" reuse lint
     ```
4. **Never commit secrets.** Use `.env.example` placeholders; real tokens, keys, and
   `.env` files stay out of Git.
5. **Declare authorship.** By opening a pull request you confirm that you have the
   right to submit the contribution and that it may be distributed under this
   repository's Apache-2.0 license.
6. **Follow the documentation style guide.** Prose changes MUST follow
   `docs/style-guide.md` (terminology, punctuation, normative language, and the
   document-class rules).

## Pull-request process

1. Fork the repository (external contributors) or create a branch (maintainers).
2. Fill in the pull-request template. Draft pull requests are welcome for early
   feedback.
3. A maintainer reviews the change. External contributions require a review before
   merging; maintainers may push small maintenance commits directly.
4. After merge, the pull request is the permanent record of the change and its
   justification.

## Competitive use

Except for the project's maintainers and members they authorize in writing, no third
party may **directly use this repository** to participate in competitions or evaluations
of the same kind as the competition this project targets (autonomous-agent
offensive-security, penetration-testing, or security-agent capability). **Derivative
works created by third parties are not restricted.** The full terms are in
`DISCLAIMER.md` (Chinese text is authoritative); the restriction is a condition of use,
and obtaining, copying, deploying, or using this repository constitutes acceptance.

---

## Enforcement

GitHub branch protection and repository rulesets are **not available on this
repository's current plan**: the API answers `Upgrade to GitHub Pro or make this
repository public to enable this feature` for a private repository. Until the
repository moves to a plan that supports them (or is made public), PR-only is
enforced by the tracked `pre-push` hook in `.githooks/`. Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

The hook rejects any push that updates `main` and prints the branch/PR workflow.
Maintainers may bypass it deliberately for an emergency with:

```bash
TSEC_ALLOW_DIRECT_PUSH=1 git push
```

If the repository is later upgraded to GitHub Pro/Team, enable server-side branch
protection (require pull requests before merging) and keep this hook as a local
fallback.

---

## 中文摘要

本仓库**只接受 Pull Request**，Issues 与 Discussions 均已关闭。

**原因：**维护者是在校学生，没有时间管理 issue：分类、标注、回复、追问的成本高于
直接审阅一个已经包含改动与说明的 PR。把所有信息放在一个 PR 里——diff、动机、测试
证据、许可信息——可以一次性完成评审。关于某个改动的疑问请写在 PR 描述或评审讨论中。
评审可能延迟，也可能不附详细理由即拒绝；这是学校项目，不是有支持承诺的产品。请勿
用 issue 询问进度或提需求。

**提交前：**

1. 一个 PR 只做一件事，不要混入无关重构。
2. 运行 `python mcp/tsecbench_mcp.py --selftest` 与两个 unittest 发现命令，确保通过。
3. 遵守许可规则：原创代码为 Apache-2.0，新源文件加 SPDX 头；禁止加入专有或不可再
   分发内容；第三方内容保留上游许可，并同步更新 `THIRD_PARTY_NOTICES.md` 与
   `REUSE.toml`，且 `reuse lint` 必须通过。
4. 不得提交密钥或真实 `.env`。
5. 提交 PR 即表示你有权贡献该内容，并同意其按本仓库 Apache-2.0 许可分发。
6. 文档改动必须遵循 `docs/style-guide.md`（术语、标点、规范性用语与文档分类规则）。

**竞赛使用限制：** 除维护团队及其书面授权的成员外，任何第三方不得**直接使用本仓库**参加与本项目目标赛事同类的比赛或评测。第三方自行创作的**衍生物不受此限**。完整条款见 `DISCLAIMER.md`（中文为正式文本）；该限制为使用条件，获取、复制、部署或使用本仓库即视为接受。

**执行机制：**当前私有仓库套餐不支持 GitHub 分支保护与 Rulesets（API 返回需要升级
Pro/Team 或公开仓库），因此暂以仓库内 `.githooks/pre-push` 钩子执行。每个克隆执行
`git config core.hooksPath .githooks` 后，直推 `main` 会被拒绝；维护者可临时用
`TSEC_ALLOW_DIRECT_PUSH=1 git push` 绕过。升级套餐后应改为服务端分支保护。
