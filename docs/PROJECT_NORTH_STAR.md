# Project North Star

## Objective

Build and ship `music_brain` in disciplined, auditable phases where each phase can be reviewed through a GitHub PR before the next phase begins.

## Success Criteria

- Each major phase produces a checkpoint commit and a PR-ready handoff.
- Handoff reports consistently document scope, tests, validations, risks, and open decisions.
- External audit feedback is incorporated before moving to the next major phase.

## Working Agreement

- Work in phase-sized increments.
- Use the handoff scripts to keep reporting consistent.
- Keep decision trails in `docs/USER_DECISIONS.md`.
- Follow the PR loop in `docs/AGENT_LOOP_PROTOCOL.md`.

## Required End-of-Phase Routine

After every major phase, always:

1. Run tests and validators.
2. Write latest handoff reports.
3. Commit checkpoint.
4. Push branch.
5. Open or update PR.
6. Paste PR handoff body.
7. Stop for audit before the next phase.
