# Beat Battle Ranked Site Automation

## Local dependency notes

- Python package: `playwright` (included in `requirements.txt`)
- Browser binaries install step (manual, local):
  - `python -m playwright install chromium`

## Safety defaults

- No captcha/login/MFA bypass logic is implemented.
- Submission automation defaults to manual confirmation and disabled auto-submit.
- Local auth/session state remains in ignored local config/session files.
