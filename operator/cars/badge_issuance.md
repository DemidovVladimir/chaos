# NIP-58 badge issuance

This is an operator workflow, not an admin-agent workflow.

The operator may issue NIP-58 badges for `cars-pack@1` after manual
due diligence. Badges are one trust signal among several; they do not
gate relay access, MCP access, or listing visibility by themselves.

## Boundary

- The relay accepts badge events if they pass the kind allowlist, PoW,
  and rate limits.
- The operator decides whether to issue or revoke a badge.
- The admin-agent may publish kind 30430 decisions that inform a
  later badge review, but it does not issue, renew, or revoke badges.
- End-user agents decide locally how much badge weight to apply.

## Issuance checklist

- [ ] Applicant pubkey is controlled by the applicant.
- [ ] Requested badge type is valid for `cars-pack@1`
      (`verified-private-offering agent`, `verified-dealer`,
      `long-standing-member`, or a documented future badge).
- [ ] Due-diligence basis is recorded in the operator's private case
      file. Store only the minimum needed to explain issuance.
- [ ] Public badge content is sanitized, contains no PII, and fits
      NIP-58 expectations.
- [ ] Badge definition event exists or is published first.
- [ ] Badge award event is signed by the operator badge key, not the
      relay key and not the admin-agent key.
- [ ] Applicant receives the badge event id and can reference it from
      listings with `["badge", "30009:<issuer>:<badge-id>"]`.

## Revocation

Revocation policy lives in `../../reputation/operator_revocation.md`.
The short version: revocation is an operator decision, published as
NIP-09 deletion plus an auditable trust-signal event. Admin-agent
decisions may be inputs to the operator's review, but they are not
automatic badge actions.
