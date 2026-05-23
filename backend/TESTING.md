# Backend Testing

The backend test environment is fixed to Python 3.12 via `uv`.

## Setup

```powershell
uv venv --python 3.12 --seed .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

If `.venv` already exists but does not include `pip`, recreate it with:

```powershell
uv venv --python 3.12 --seed --clear .venv
```

## Acceptance Command

Run this from the repository root after activating `.venv`:

```powershell
python -m pytest backend/test_data_driven.py backend/test_unlocked_components.py -q
```

These tests use pytest fixtures from `backend/conftest.py`. Database-backed tests create
an isolated SQLite file under pytest's temporary directory and do not read or write
`data/automogul.db`, `data/template.db`, or `data/saves/*.db`.

## Test Categories

- `unit`: fast tests without database writes.
- `integration`: tests that exercise multiple backend modules.
- `db`: tests that use an isolated test database.
- `db_script`: standalone script-style tests that may modify a database.

`backend/test_scripts` is excluded from default pytest discovery. Treat those scripts as
manual database tests and run them only against a disposable test database or a backup copy.
