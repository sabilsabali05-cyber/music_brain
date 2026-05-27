# Branchless Cursor Migration Policy

Canonical active branch policy for this repository.

## Policy Target
- Canonical active branch: `cursor/music-brain-active`
- Stop new branch/worktree creation unless explicitly requested.

## Hard Constraints
- Do not delete branches or worktrees.
- Do not discard uncommitted work.
- Do not force-push.
- Do not commit raw audio, private paths, local configs, or model caches.
- Keep old branches as read-only historical references.

## Migration Operating Rules
- Before branch switches, capture `git status`, active branch, worktree root, and linked worktrees.
- If the current branch is dirty during migration, stash with exact name `pre-branchless-migration`.
- Prefer source branch `cursor/activate-model-witnesses-and-reroll-source-loops-v1`; fallback to `cursor/real-midi-source-witness-integration-v1`.
- Reapply only safe, relevant changes after switching to canonical branch.
- Run lightweight validation only (`git branch --show-current`, `git status`, and `scripts\\dev.cmd check-privacy-leaks` when available).
