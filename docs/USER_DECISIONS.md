# User Decisions

Track unresolved product and execution decisions here so every PR includes explicit asks.

## Open Decisions

- Owner: Sabil
- Updated: 2026-05-22

1. Confirm preferred cadence for PR audits (every major phase vs. finer checkpoints).
2. Confirm minimum test/validator bar expected before requesting audit.
3. Confirm whether handoff metrics should prioritize quality, performance, or both for each phase.

## Decision Logging Rules

- Add new decisions as numbered entries.
- Mark resolved decisions with `RESOLVED:` and date.
- Mirror unresolved items into handoff field `open_user_decisions`.
- Keep entries short and PR-actionable.

## Phase Exit Reminder

After every major phase, follow this exact sequence:

1. Run tests/validators.
2. Write latest handoff.
3. Commit checkpoint.
4. Push branch.
5. Open or update PR.
6. Paste PR body from `prepare-pr-handoff`.
7. Stop for audit before next major phase.
