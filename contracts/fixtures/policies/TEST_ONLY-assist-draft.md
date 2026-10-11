# TEST_ONLY prompt-assist scheme

`TEST_ONLY-assist-draft.yaml` selects `OTHER_CONFIRMED_SCHEME` solely to exercise
controlled deterministic draft preparation in mock mode. Load it as a separate
D-05 snapshot and explicitly configure `assist_policy_version` plus
`assist_provider=deterministic_mock`. This is not a production policy decision,
free allowance, registration benefit, real AI integration, or provider contract.
The existing mock.yaml and production D-05 remain UNDECIDED.

The implemented simulation preserves the original, copies supplied product facts,
formats current Agent/spec capabilities, preserves parameters, and lists missing
facts. It does not infer facts from uploaded media. No generation task, outbox,
reservation, or credit entry is created. Formal generation still requires the
separate quote and confirmed task submission API.

`POST /api/v1/assist/prompts` requires session, Origin, CSRF, and Idempotency-Key.
`request_key = Idempotency-Key header`: send the key only in this required HTTP
header, not in the JSON body. Reuse it for the same request; changed input with
the same key returns 409.
Only completed successful receipts are stored in assist_requests. Completed
same-key/same-body retries return the original receipt before calling the provider;
a different body conflicts. Same-key concurrent first requests can execute the
side-effect-free mock provider multiple times, but serialize one completed receipt
under the current user's DB lock. Failed/time-out calls store no completed receipt
and can retry. This does not promise exactly-once provider execution or live billing.

The Redis per-user 60-second limit is abuse protection and counts provider attempts,
not a commercial allowance; completed receipt replays do not consume it. No reset
or quota policy is selected. All independent-free and other unimplemented schemes
are rejected. Production/staging stay closed even with a policy record; T23 must
confirm a real supplier, protocol, timeout/idempotency/cost semantics and factual
verification before any live implementation. T18 supplies adopt/edit/restore UI.
