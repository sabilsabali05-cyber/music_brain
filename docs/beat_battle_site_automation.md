# Beat Battle Ranked Site Automation

## 2 human actions only quickstart

1. **Manual submit on site**  
   Run `scripts\dev.cmd beat-battle-session-loop`, wait for `waiting_for_manual_submission`, then upload/submit on the site yourself.
2. **Manual result entry**  
   When results are posted, update `artifacts/beat_battle_site/manual_result_snapshot.json` with your round result, then rerun the launcher (or keep watcher mode running).

## Single launcher commands

- One-shot session launcher:  
  `scripts\dev.cmd beat-battle-session-loop`
- One-shot with bounded wait for manual result entry polling:  
  `scripts\dev.cmd beat-battle-session-loop --wait-for-result-entry --poll-seconds 15 --max-wait-seconds 1800`
- Continuous watcher (auto-detects new local round folders):  
  `scripts\dev.cmd beat-battle-session-loop-watch --poll-seconds 15`

## Status outputs and next actions

The launcher writes both:

- `reports/beat_battle_site_automation/session_loop_status.json`
- `reports/beat_battle_site_automation/session_loop_status.md`

Status values include:

- `processing_round`
- `waiting_for_manual_submission`
- `waiting_for_result_entry`
- `training_ready`
- `training_skipped`

## Safety defaults

- No captcha/login/MFA bypass logic is implemented.
- Submission automation defaults to manual confirmation and disabled auto-submit.
- Local auth/session state remains in ignored local config/session files.
