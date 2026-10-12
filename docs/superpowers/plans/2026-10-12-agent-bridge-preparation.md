# 独立 Agent 服务桥接实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development。沿用已选单开发者、冻结后一次限定评审与代码优先方式。

**Goal:** 交付独立启动、持久查原、受控成果读取的三个候选HTTP桥接服务，真实模型默认关闭。

**Architecture:** 共用持久任务/鉴权/成果核心，按 copy/image/video 独立启动并注入驱动。MySQL记录不变意图，硬盘存受控字节；调用开始后的不明状态不自动重跑。候选实现不默认启用平台生产registry。

**Tech Stack:** 现有Python/FastAPI/Pydantic/SQLAlchemy/Alembic/MySQL与硬盘，不加消息框架。

**Spec:** docs/superpowers/specs/2026-10-12-agent-bridge-preparation.md；用户明确回复“按这份设计实现”。

## Global Constraints

- 原三库、秘密、既有运行数据只读；真实驱动关闭，首轮仅替身/TEST_ONLY。
- 固定job ID/输入/摘要，唯一键隔离Agent、调用账户、external_submission_id；同键异参409，跨范围拒绝。
- 调用开始、超时、崩溃、partial、保存失败、普通NOT_FOUND不授权新生成/完整发布/安全重试。
- 完整文件落盘校验再发布，只经授权接口读取；请求不指定服务器路径或任意URL，日志不含正文/字节/秘密。
- HTTP素材字节落盘保存，MySQL不存整件base64/二进制；仅不变参数、受控引用、摘要与状态入库。
- 视频固定原任务和方案版本独立确认，不自动confirm；库内部SQLite不替代平台/桥接MySQL。
- 用户代码优先：最小关键检查、适用静态、一次限定diff；真实Agent/生产协议/完整联调待验。
- 主控独占index/commit/state/progress，开发者不递归；迁移承接派发时实际head。

## Review Focus

1. 跨调用范围查询/重放不得混用输入或泄露成果。
2. 已记录调用开始后重启不得再次调用原库。
3. blob存在但资产partial/审核不通过不得标完整。
4. 保存/DB发布结果不明不得删唯一成果或重新生成。
5. 视频确认异版本/异身份不得确认错任务或自动越过确认。

## T23a：服务核心、库接线与独立启动

**Files:** 创建 backend/app/bridges/{schemas,models,auth,storage,service,routes,server,worker,drivers,adapter}.py（drivers可按三库拆目录）；承接实际head的新迁移；contracts/bridges/bridge-v1.yaml与候选OpenAPI；infra/compose.bridges.yaml和启动说明；backend/tests/integration/test_agent_bridges.py与必要小单元检查。仅必要模型接线，不启用生产registry。

**Interfaces:**
- create_bridge_app(settings, session_factory, drivers) -> FastAPI：按kind独立启动/显式注入，真实配置缺失不可接真实调用。
- submit_job(principal, request) -> BridgeJobView：先持久化，不在HTTP线程调用模型；external_submission_id、原平台task/user、协议/source版本及摘要固定。
- get_job(principal, job_id)、query_external(principal, external_submission_id)：只读原持久记录，限原范围。
- run_pending_once() -> result：CAS领取未调用记录、先提交调用开始，再事务外驱动；开始后不明不可自动再次领取。
- read_result/read_artifact：原完整成果/文件；partial与保存失败保持不完整，无私有路径回传。
- confirm_job(principal, job_id, plan_version, request_key)：视频原任务、固定方案版本独立确认，不默认确认。
- BridgeAgentAdapter对齐现有AgentAdapter.submit/query/retrieve；callback/缺席证明未实现时unsupported。

- [ ] 读取Spec/现有AgentAdapter/三库公共DTO与方法，不读秘密或实际运行原库。
- [ ] 最小关键检查覆盖同键/异参/跨范围、开始后重启不重复调用、完整/partial/保存失败、文件范围、视频固定版本确认。仅唯一TEST_ONLY记录/自有目录。
- [ ] 实现持久核心及接口；三真实驱动使用受控工厂配置、独立home，导入和调用显式关闭。字段依实际DTO观察，不将观察值当生产批准。
- [ ] 候选协议draft、独立启动配置/说明；原项目不改、生产registry不启用、不对外发布；明确视频确认与恢复限制。
- [ ] 仅本步定向检查及Ruff/契约等静态，冻结SHA/结果/日志/未验项；主控限定评审与本地提交，不将替身PASS记作真实联调。

## 自检

独立服务、持久性、三库接线、鉴权/素材/成果边界、受控启动由T23a覆盖；真实模型/协议审批留后续。无新增UI/付费政策/自动视频规划确认。原AgentAdapter与来源公共方法保持一致。执行方式沿用既有授权。
