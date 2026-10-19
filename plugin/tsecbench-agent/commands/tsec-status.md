---
description: 查看 TSecBench 评测任务的整体进度与剩余名额
allowed-tools: mcp__tsecbench__task_status, mcp__tsecbench__list_challenges, mcp__tsecbench__note_list
---

调用 tsecbench 的 `task_status` 与 `note_list`，然后向用户报告：

1. **进度**：已通关 X / 总题数 N；flag 进度 correct/total；满分与已得
2. **名额**：当前活跃容器列表、剩余名额（上限 3）
3. **下一步建议**：`next_candidates` 里按难度排序的前几题
4. **遗留线索**：笔记账本里最近 5 条（key + 内容摘要）

如果任何调用失败，原样给出返回体里的 `code` / `message` / `action`，
并明确说明这是平台返回的原因，不要猜测。
