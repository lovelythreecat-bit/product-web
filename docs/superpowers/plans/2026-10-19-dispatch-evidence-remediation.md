# Dispatch and Evidence Remediation Implementation Plan

> **For agentic workers:** Execute the approved work through task-orchestrator with three independent implementers and an independent integrated review. Preserve the existing working tree.

**Goal:** Stop ineffective recovery loops and repeated conflict evidence creation; prepare an exact development-data deletion scope for separate confirmation.

**Architecture:** Database-authorized dispatch generations fence duplicate wakeups independently of periodic task recovery deadlines. Durable observation dispositions and explicit validation revisions prevent history replay from becoming new evidence. Stable manual-action outcomes stop automatic remote queries while preserving original identities and settlement rules.

**Tech Stack:** Windows/PowerShell, Python 3.12, FastAPI, SQLAlchemy, MySQL 8.4, Redis Streams.

**Spec:** User-approved investigation findings in this chat, 2026-10-19; ledger `.agent-runs/dispatch-evidence-20261019/plan.json`.

## Global constraints

- Preserve pre-existing tracked and untracked edits; baseline hashes and source ZIP are stored in the run evidence directory. Do not reset, revert, stage unrelated files, or commit.
- No UI changes, new generation requests, inferred failure/refunds, development business-data writes, or service restarts by implementers.
- SQL tests use only the allowlisted isolated test schema and `ecommerce_test`; Redis tests use database 15 and unique owned keys.
- Original evidence and decisions remain immutable. Physical deletion is a separate maintenance operation requiring the user's confirmation of concrete scope and trigger-policy exception.
- No credentials, cookies, product bodies, generated text, or arbitrary exception strings in diagnostic evidence.

## Review focus

- An explicit future event must not be made immediately runnable by the recovery watchdog.
- An old event must not authorize a current-stage remote operation; a periodic same-version new generation must remain runnable.
- Conflict reuse must preserve changed identities, changed validation rules, transaction rollback and concurrent delivery semantics.
- Warnings-only metadata evolution must not permit changed original artifact identities or text hashes.
- Stable needs-input and validation conflicts must stop automatic queries; transient outages must remain recoverable without new generation or automatic settlement.

## T1: Dispatch eligibility

Files: `backend/app/dispatch/{consumer,recovery,outbox,models}.py`, migration `0034_dispatch_generations.py`, targeted unit and fault tests.

- [ ] Reproduce stale-version, premature and repeated-generation execution failures.
- [ ] Add durable dispatch/claim generation and generation-aware `rearm_outbox(session, task_id, operation, *, ready_at=None)`.
- [ ] Atomically validate task version, stage, event generation and event ready time when acquiring automatic execution authority.
- [ ] Exclude `UPSTREAM_NEEDS_INPUT` and `CALLBACK_EVENT_CONFLICT` from automatic recovery while preserving explicit administrative claims.
- [ ] Verify periodic recovery, delayed delivery, duplicate XADD and crash recovery.

## T2: Observation dispositions and historical validation

Files: `backend/app/agents/{callbacks,models,observation_imports}.py`, `backend/app/results/recovery.py`, migration `0035_observation_imports.py`, observation/callback/text-pipeline tests.

- [ ] Reproduce repeated conflict creation, rollback/restart and changed-identity cases.
- [ ] Persist bounded, atomic dispositions keyed by immutable source and validation context; make same-variant conflict evidence idempotent.
- [ ] Preserve short account transactions and eliminate repeated processing of completed history.
- [ ] Route blocking validation conflicts to existing investigation behavior and stop automatic remote polling.
- [ ] Preserve explicit, auditable revalidation of an original result, with strict artifact checks and normal publication/settlement.

## T3: Business wait states and diagnostics

Files: `backend/app/agents/{contracts,image,upstream}.py`, `backend/app/investigations/service.py`, telemetry, worker and targeted tests.

- [ ] Reproduce completed/needs_input being collapsed to UNAVAILABLE.
- [ ] Represent NEEDS_INPUT distinctly and preserve the original task in an explicit investigation wait.
- [ ] Keep transient transport outages recoverable and prevent implicit resubmission or settlement.
- [ ] Add allowlisted diagnostics and inspect no-progress RUNNING coverage using existing policy deadlines.
- [ ] Remove account-lock-spanning unbounded historical recovery reads where applicable.

## Integration and physical deletion proposal

- [ ] Parent runs isolated MySQL/Redis regressions after both additive migrations exist; compare source snapshots before and after verification.
- [ ] Independent reviewer checks the integrated implementation and deletion proposal; repair concrete findings and rerun affected checks.
- [ ] Parent inventories the three abnormal development tasks, foreign keys, JSON references, frozen credits, works, files and stream entries using read-only queries.
- [ ] Deliver a deletion manifest distinguishing redundant conflict evidence from complete task deletion. Do not delete or alter immutable triggers before the user confirms the exact maintenance scope.
- [ ] Record verification evidence and remaining deployment/maintenance steps without claiming live acceptance prematurely.
