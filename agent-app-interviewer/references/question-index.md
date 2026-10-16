# 题卡索引

40道基础题来自2026-10-16调研；题卡的证据要求和追问由本技能设计。级别用于调节追问深度，不代表招聘公司的评级。

先在此选择问题，再只读对应JSON中的目标题卡。无需一次载入全部题卡或来源。

| ID | 主题 | 题型／级别 | 核心问题 | 题卡文件 | 来源 |
|---|---|---|---|---|---|
| Q01 | 项目与业务 | 项目／初级 | 选一条真实请求，讲清输入、路由、工具执行、存储到输出的全过程，以及你负责的部分。 | [projects.json](cards/projects.json) | I02 |
| Q02 | 项目与业务 | 项目／中级 | 项目价值如何验证？哪些瓶颈被解决，改善来自哪个环节？ | [projects.json](cards/projects.json) | I02、I13 |
| Q03 | 项目与业务 | 项目／中级 | 为什么自研Agent核心流程？使用现有框架的代价和收益是什么？ | [projects.json](cards/projects.json) | I06、I16 |
| Q04 | 项目与业务 | 项目／初级 | 项目是否部署、被谁使用？你遇到的具体困难和处理实例是什么？ | [projects.json](cards/projects.json) | I18 |
| Q05 | RAG | 基础／初级 | 讲清文档入库与在线问答两条链路。 | [rag.json](cards/rag.json) | I10、I11 |
| Q06 | RAG | 场景／中级 | 标题切分、父子块、重叠和剩余短块如何处理？ | [rag.json](cards/rag.json) | I11 |
| Q07 | RAG | 基础／初级 | BM25和稠密向量检索分别弥补什么不足？ | [rag.json](cards/rag.json) | I10 |
| Q08 | RAG | 场景／中级 | 混合召回、融合与重排怎样衔接，参数如何确定？ | [rag.json](cards/rag.json) | I03、I11 |
| Q09 | RAG | 场景／中级 | 查询改写或多子问题检索增加延迟时，怎样权衡？ | [rag.json](cards/rag.json) | I11 |
| Q10 | RAG | 场景／中级 | 图片解析和长耗时入库任务如何处理？ | [rag.json](cards/rag.json) | I11、I06 |
| Q11 | RAG | 场景／中级 | RAG检索不到资料时，怎样分阶段定位问题？ | [rag.json](cards/rag.json) | I16 |
| Q12 | 工具与编排 | 场景／中级 | 工具增长到一百多个时，如何注册、检索与选择？ | [agents.json](cards/agents.json) | I05 |
| Q13 | 工具与编排 | 场景／中级 | 现有工具无法解决任务时，系统怎样处理？ | [agents.json](cards/agents.json) | I05 |
| Q14 | 工具与编排 | 基础／中级 | Skill、MCP、Function Calling、Workflow、SubAgent各解决什么问题？ | [agents.json](cards/agents.json) | I02 |
| Q15 | 工具与编排 | 场景／中级 | 一个任务为什么适合固定Workflow，什么时候才需要模型自主决策？ | [agents.json](cards/agents.json) | I02、I01 |
| Q16 | 工具与编排 | 场景／初级 | Agent反复调用工具陷入循环，怎样约束与终止？ | [agents.json](cards/agents.json) | I16 |
| Q17 | 工具与编排 | 场景／初级 | 用户输入不完整或资源有歧义时，哪些参数需要澄清确认？ | [agents.json](cards/agents.json) | I02 |
| Q18 | 上下文与记忆 | 基础／初级 | 长期与短期记忆分别存什么，如何实现？ | [agents.json](cards/agents.json) | I12、I13 |
| Q19 | 上下文与记忆 | 场景／中级 | 运行容器迁移或重启后，会话上下文如何恢复？ | [agents.json](cards/agents.json) | I12 |
| Q20 | 上下文与记忆 | 场景／中级 | 长任务发生中断或忘记执行计划时，怎样继续？ | [agents.json](cards/agents.json) | I07 |
| Q21 | 上下文与记忆 | 场景／中级 | 旧记忆与当前需求冲突时，怎样判断是否沿用旧方案？ | [agents.json](cards/agents.json) | I15 |
| Q22 | 上下文与记忆 | 场景／中级 | 长文档分块后，汇总结果再次超出上下文时如何继续处理？ | [agents.json](cards/agents.json) | I01 |
| Q23 | 评测与可靠性 | 场景／中级 | 最终输出与中间节点怎样分别评估？评测样本和评分规则怎样构建？ | [evaluation.json](cards/evaluation.json) | J01、J04 |
| Q24 | 评测与可靠性 | 项目／中级 | 业务指标、Agent表现和你承担的模块之间如何对应？ | [evaluation.json](cards/evaluation.json) | I13 |
| Q25 | 评测与可靠性 | 场景／中级 | 模型输出结论如何得到事实依据？是否有确定性校验？ | [evaluation.json](cards/evaluation.json) | I01 |
| Q26 | 评测与可靠性 | 场景／中级 | 用另一个Agent检查输出时，如何处理检查者自身出错？ | [evaluation.json](cards/evaluation.json) | I01 |
| Q27 | 评测与可靠性 | 场景／初级 | 关键词规则和大模型判断如何分工，为什么某些边界选规则？ | [evaluation.json](cards/evaluation.json) | I17 |
| Q28 | 后端与基础 | 场景／中级 | 网络返回成功但服务端称未收到请求时，怎样排查？ | [backend.json](cards/backend.json) | I03 |
| Q29 | 后端与基础 | 场景／中级 | 数据量扩大十倍、耗时却扩大百倍时，怎样定位性能瓶颈？ | [backend.json](cards/backend.json) | I03 |
| Q30 | 后端与基础 | 基础／中级 | 联合索引如何设计？哪些WHERE条件会影响索引使用？ | [backend.json](cards/backend.json) | I03、I01 |
| Q31 | 后端与基础 | 基础／初级 | 进程、线程、协程有什么区别？进程切换的成本来自哪里？ | [backend.json](cards/backend.json) | I04、I10 |
| Q32 | 后端与基础 | 场景／中级 | Agent并发请求如何限流？多Agent同时运行有哪些性能问题？ | [backend.json](cards/backend.json) | I10、I13 |
| Q33 | 后端与基础 | 基础／中级 | Redis数据结构或Java类加载怎样与项目中的实际使用对应？ | [backend.json](cards/backend.json) | I13 |
| Q34 | AI Coding | 项目／中级 | 展示一次使用AI完成任务的过程，你修改过它的哪些技术决策？ | [projects.json](cards/projects.json) | I01 |
| Q35 | AI Coding | 场景／初级 | AI生成代码的质量如何保证？你用哪些测试或审查验证？ | [projects.json](cards/projects.json) | I14、I07 |
| Q36 | AI Coding | 场景／中级 | 面对长方案怎样抓重点审查，如何划分模型与普通代码的职责？ | [projects.json](cards/projects.json) | I01 |
| Q37 | 手写代码 | 编码／中级 | 实现LRU Cache，再讨论题目给出的变种要求。 | [projects.json](cards/projects.json) | I01、I03 |
| Q38 | 手写代码 | 编码／中级 | 实现K个一组反转链表。 | [projects.json](cards/projects.json) | I04 |
| Q39 | 手写代码 | 编码／中级 | 实现大数乘法；或实现无重复字符的最长子串。 | [projects.json](cards/projects.json) | I12、I05 |
| Q40 | 手写代码 | 编码／中级 | 两个协程依次交替打印奇偶数，保证输出顺序。 | [projects.json](cards/projects.json) | I10 |

## 选题约束

- 优先与简历、JD重合，随后补岗位硬要求；不把题目顺序当固定面试流程。
- 项目题可按缺失经历改写为明确假设的场景题，此时移除“个人实现”类证据要求；不据假设回答认定真实经验。
- Q33先选候选人熟悉的语言或组件；Q39在两道算法中选一道；Q40先明确语言和执行单元。每个可见回合只提出一个待回答问题。
- 训练、后训练和推理优化不在这40题的完整覆盖范围内。目标JD涉及时，只追加可核验的岗位题，并标为“JD生成题”，不冒用Q编号或公司来源。
- 追问、变体属于同一核心题分支，不占新核心题名额；实质切换考察目标时才计为新核心题。
