---
status: draft
review_required: true
reviewed_on: 2026-11-03
---

# AI 客服知识库素材

本目录是依据当前本地需求与前后端源码整理的审核草稿。没有修改业务代码，没有连接数据库、创建索引、启动业务服务或调用付费模型；没有读取密钥、真实用户资料、聊天记录或生产业务数据。源码已实现不代表生产已部署，本次未做真实生成或上线核验。

| 资料 | 内容 |
| --- | --- |
| [articles/](articles/) | 30篇已实现功能及当前限制的主题草稿 |
| [planned/](planned/) | 3篇规划或待确认资料，与默认候选文章隔离 |
| [article-index.json](article-index.json) | 文章元数据与稳定ID索引 |
| [graph/nodes.jsonl](graph/nodes.jsonl) / [edges.jsonl](graph/edges.jsonl) | 仅快速生成的通用流程与有证据的故障关系 |
| [page-context-contract.md](page-context-contract.md) | 四阶段、汇总及弹层的最少上下文建议与定位现状 |
| [evaluation.jsonl](evaluation.jsonl) | 30条明确标注为虚构数据的评测题，未调用模型执行 |
| [review-checklist.md](review-checklist.md) | 冲突、待确认政策、图谱审核与首批导入建议 |
| [source-index.json](source-index.json) | 来源路径及一基行号，按主题分组 |
| [validation-report.json](validation-report.json) | 本轮静态结构检查结果与证据文件摘要 |

## 状态与来源约定

所有文章 `status=draft`、`review_required=true`。`implemented` 仅说明本地有实现；`planned` 是规划；`unknown` 是无法确认完整能力。`deployment_status=not_verified` 表示本轮未核验部署情况，不断言一定未部署。

来源统一为仓库相对路径，以及包含首尾的一基 `line_start/line_end`。正文面向普通用户；内部路径、状态枚举、引用及审核说明供维护人员使用，后续客服回答不直接暴露这些实现细节。依据发生变化时重新核对，不能只检查路径仍存在。

## 后续导入约束

当前正式导入清单为空：全部先人工审核。审核应记录审核人、日期、适用部署版本、规则版本与来源摘要，再由独立发布清单准入，不要递归扫描整个目录导入。

Chroma 候选仅取经审核的 `articles/*.md`；保留 article_id、title、route、implementation_status、来源及版本元数据。按单主题/完整步骤切分，必要前提、计费限制、人工帮助边界与对应回答一起保留。排除 planned/、契约、审核表、索引和验证报告；评测题也不是用户知识文章。

Neo4j 候选仅取审核通过的两份 graph JSONL。节点允许 Page、Step、Field、Action、Condition、Issue、Resolution；关系允许 HAS_STEP、HAS_FIELD、HAS_ACTION、REQUIRES、NEXT_STEP、MAY_CAUSE、RESOLVED_BY。`condition` 是必须保留的限制说明，不能去掉条件后执行跳转，也不能作为已实现的规则解释器。多条 REQUIRES 不默认解释为全部AND，尤其普通失败重试与停止图片重试是两个分支。

图谱表示通用依赖，绝不保存当前用户的任务、商品、余额或聊天。RESOLVED_BY 表示有依据的处理途径，不保证操作后一次成功；MAY_CAUSE 只描述代码明确的校验/阻塞关系，不推测网络、供应商或内容审核故障原因。

## 评测使用

每条包括 question、可选 page_context、expected_key_points、must_not_claim、source_article_ids。所有样例都是人工构造的虚构测试状态。缺少上下文不等于字段为空、没有任务或没有扣费。涉及 planned/ 的引用仅供“未实现能力”边界评测，不授予导入权限。

建议人工评分：必要要点覆盖、下一步有真实前置条件、费用与状态不越过实时接口、没有禁说承诺、信息不足时正确追问。任何一条 must_not_claim 被触发均应判失败；不得将本轮格式检查误写为客服回答质量通过。
