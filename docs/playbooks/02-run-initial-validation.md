# Playbook 02: Run Initial Validation

## Objective
Validate imports, tests, and ARDS/SDD structure without making external API calls.

## Preconditions
- Dependencies are installed.
- `.env` exists locally if runtime validation is needed.
- Unit tests must use mocks or local configuration only.

## Commands
```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\ards_check.py
.\.venv\Scripts\python.exe scripts\check.py
```

## Expected Result
All tests pass and the ARDS/SDD check reports success.

## Common Problems
- Missing `PyYAML` breaks `scripts/ards_check.py`.
- Missing `src` on the Python path breaks imports; pytest is configured in `pyproject.toml`.
- Real provider credentials are not required for unit tests.

## Success Validation
`scripts/check.py` prints `Repository check passed.`
