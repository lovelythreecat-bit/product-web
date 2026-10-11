"""Reserved integration boundary.

T02 intentionally mounts no policy-management HTTP routes. T04 must inject a
current-session verifier with explicit policy-confirmation permission and write
its audit event in the same shared Session transaction before caller commit.
PolicyService alone must never be exposed as an unauthenticated route.
"""
