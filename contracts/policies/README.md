# Policy version contract (T02)

D-01 through D-12 are unresolved production drafts, derived from requirement section 15.
Files use the JSON subset of YAML so no additional YAML parser is required. Null values,
empty target maps and `UNDECIDED` are intentional; they cannot enable a production feature.
No file in this directory is automatically imported, confirmed or activated at startup.

`DecisionVersion` is the validated snapshot schema in `backend/app/policies/schemas.py`.
Create an explicit new version with `PolicyService.add_draft`. Existing content, environment,
confirmation history and decision/version keys cannot be updated or deleted. The only allowed
update is the one-time draft-to-confirmed transition. The database enforces these rules.
Version keys are globally unique per decision; use different keys for each environment.

`PolicyService.require_feature(feature, mode, {decision_id: exact_version})` reads the database
without autoflush and returns the exact applicable version map in `GateReceipt` or raises
`PolicyGateError(status_code=403, code=FEATURE_NOT_ENABLED)`. It never commits or modifies data.
The module-level function accepts trusted `DecisionVersion` snapshots for pure validation;
it must not receive client-supplied approval objects. A receipt is a checked snapshot, not an
authorization token. Admission must call all applicable gates before any side effect, including
both `agent.<id>.generation` and `spec.<id>.published`. Agent/protocol and spec versions in
those policies must also match the selected Agent/catalog versions when T05/T07 integrate them.

| Feature | Applicable policy sections |
| --- | --- |
| registration | D-05 registration (strict integer credits >= 0) |
| prompt_assist | D-05 assist, explicit selected scheme, reviewed policy and implementation |
| spec.<id>.published | D-02 specs[id], D-05 prices[id]; D-04 specs[id] for multiple/detail_images |
| agent.<id>.generation | D-01 agents[id], D-03 agents[id] with matching protocol version; D-05 generation, D-08 generation, D-09 generation, D-10 generation |
| upload | D-10 upload; caller applies the applicable D-03 Agent input rules separately |
| delete | D-09 delete |
| account_disable | D-09 account_disable |
| actual_cost | D-06 cost; when unavailable the caller displays unavailable, never zero |
| account_recovery | D-07 recovery |
| public_site | D-07 login_help, D-11 site, D-12 deployment |
| case.<id>.published | Public site prerequisites plus D-11 cases[id], including authorization and real source |

Each section is checked with its corresponding named schema; schemas list the exact content
and attachment references to fill. References identify reviewed, versioned records and never
contain credentials. The future confirmation workflow must verify evidence references against its evidence source;
the T02 identity authorizer and service cannot verify external documents.
An arbitrary nonempty attachment reference is not proof that its external content is correct.

`confirm_decision(actor, id, version, evidence_refs)` is a method of `PolicyService`. It rejects
strings and unverified principals. The default authority denies every confirmation. T04 must
inject an authority callback that verifies the live principal/session, explicit decision
permission, then returns the authoritative user UUID. It must not
merely trust a supplied role. The service records that UUID and a server UTC timestamp, and
uses an atomic draft-only UPDATE; concurrent confirmations cannot replace each other.
Future HTTP routes must map the typed errors and append an audit record using the same Session.
This task deliberately does not mount routes or fabricate T04 authentication/audit entities.
Callers own the final commit/rollback and must propagate errors, not commit partial work.

Confirmation may cover only applicable sections of a decision. D-05 registration approval
does not approve assistance. Assistance starts UNDECIDED. INDEPENDENT_FREE_QUOTA additionally
requires count/decrement/reset; OTHER_CONFIRMED_SCHEME requires its own policy and implementation.
No quota table or scheme is selected automatically. A new choice requires a new version.

Mock policies must have `mode: mock` and `test_only: true`. Only in mock may a draft with complete
simulated content pass a gate; the receipt remains TEST_ONLY and claims no human confirmation.
The fixture supports simulated registration and deliberately leaves assistance unresolved.
Staging and production require confirmed records for their exact mode and reject TEST_ONLY.
The mode is server configuration, never a client-controlled switch. Initial production drafts
and test fixture data do not constitute production decisions or live acceptance evidence.

Migration prerequisite: with MySQL binary logging enabled, trigger creation requires
`log_bin_trust_function_creators=1` on the managed instance or an appropriately privileged
separate migration account. Do not grant SUPER to application/test accounts. Failed MySQL
DDL may leave a table before the Alembic revision advances; inspect and repair only that
verified migration residue before retrying, never reset business data.
