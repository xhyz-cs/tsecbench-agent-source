# GitHub 参考项目使用说明

1. `repositories/BLHX`、`Pozhen-Agent`、`Cruiser-Agent` 是 TSecBench 上的 Agent 参考案例，先读 README、入口/调度器、平台适配器、工具注册与 Dockerfile；把比赛 API 适配和通用思路拆开看，不要整仓复制后当作可直接运行的 Agent。
2. 三者共同可借鉴的设计：按题型/能力裁剪工具；平台适配器和求解器分层；O-H-V-D 或 ReAct 单步闭环；为各题写证据/记忆；限制重试与总耗时；平台响应作为最终提交确认。
3. BLHX 展示 Harness/插件 + 调度器组织；Pozhen-Agent 文档展示题型识别、工具 schema 裁剪、长程记忆/故障分流的取舍；Cruiser-Agent 展示分层调度、并发 worker、共享黑板与状态治理。每个项目 README 中的成绩、模型和平台接入细节都是上游作者陈述，应回到代码、提交记录及当前官方 API 验证。
4. 工具源码：JADX 看 APK/Dex；radare2 做 CLI 逆向；angr 做程序分析/符号执行；pwntools 编写可重复的 CTF 协议交互脚本；PayloadsAllTheThings 作为测试向量/检查清单索引，按具体上下文人工筛选，不整库盲目发送。
5. 先在本地模式用小样本端到端验证平台生命周期。把调用封装成窄接口（列任务、启动、读取题目、提交、结束），为每个接口写超时、重试上限、结构化日志、幂等性与回执断言。工具输出先转成事实/证据摘要，再让模型制定下一步。
6. 开源源码快照是离线阅读副本，不自动提供其运行依赖、子模块、API 密钥、模型网关、授权测试环境或平台账号配置。版本、提交号、许可见 `repositories/manifest.json`。
