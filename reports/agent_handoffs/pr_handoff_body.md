## summary
- Phase: github-pr-handoff-loop
- Goal: Implement GitHub-based checkpoint handoff loop for PR audits.

## test results
- 173 passed, 2 warnings (pytest -q)

## validation results
- No additional validators run

## artifact paths
- docs/AGENT_LOOP_PROTOCOL.md
- docs/PROJECT_NORTH_STAR.md
- docs/USER_DECISIONS.md
- reports/agent_handoffs/latest_handoff.json
- reports/agent_handoffs/latest_handoff.md
- scripts/write_agent_handoff.py
- scripts/prepare_pr_handoff.py
- scripts/dev.ps1

## metrics before/after
**before**
- pr_handoff_loop: absent

**after**
- pr_handoff_loop: present

## risks
- Handoff quality depends on manually supplied CLI details each phase.

## questions for Sabil
- Confirm minimum validator scope expected per major phase.
- Confirm preferred audit turnaround expectations.

## audit checklist for ChatGPT
- Confirm implementation diff matches stated goal.
- Confirm tests and validators are sufficient and passing.
- Confirm all constraints were respected.
- Identify remaining risks and edge cases.
- Recommend the exact next prompt for Cursor.

@ChatGPT audit request:
- verify diff matches goal
- verify tests/validators
- verify constraints
- identify risk
- recommend next prompt

_Source handoff:_ `reports\agent_handoffs\latest_handoff.json`
