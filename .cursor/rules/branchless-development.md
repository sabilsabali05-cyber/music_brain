# Branchless Development Guardrail

Apply this rule to all Cursor-assisted development in this repository.

- Use `cursor/music-brain-active` as the canonical working branch.
- Do not create new branches or worktrees unless the user explicitly asks.
- Do not delete existing branches or worktrees.
- If branch switching is required and the tree is dirty, stash with exact name `pre-branchless-migration`.
- Never discard uncommitted changes to force a clean checkout.
- Never force-push.
- Do not commit raw audio, private/local filesystem paths, local machine config files, or model cache artifacts.
- Treat old branches as read-only historical references.
- Keep migration/policy edits isolated from generated outputs and private artifacts.
