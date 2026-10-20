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

## Pull-request process

1. Fork the repository (external contributors) or create a branch (maintainers).
2. Fill in the pull-request template. Draft pull requests are welcome for early
   feedback.
3. A maintainer reviews the change. External contributions require a review before
   merging; maintainers may push small maintenance commits directly.
4. After merge, the pull request is the permanent record of the change and its
   justification.

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
