# Playbook 01: Setup Python Environment

## Objective
Create or update the local Python environment for the agentic project base.

## Preconditions
- Python 3.10 or newer is available.
- Commands are run from the repository root.
- Secrets are not committed.

## Commands
```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

## Expected Result
Dependencies install successfully and a local `.env` file exists.

## Common Problems
- If `py -3.10` is unavailable, use the installed Python launcher or full Python path.
- If dependency installation fails, confirm the virtual environment is active and network access is available.
- If `.env` already exists, do not overwrite secrets.

## Success Validation
```powershell
.\.venv\Scripts\python.exe -m pytest
```
