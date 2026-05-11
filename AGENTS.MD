# AGENTS.MD

## Repo-Specific Conventions

- Python version management and package management use `uv`.
- Install and sync dependencies with `uv sync`.
- Run project commands with `uv run ...`.
- Manage Python dependencies through `pyproject.toml` and `uv.lock`.

## Networking and Certificates

- This repo uses the `requests` library for SSH-related access.
- Certificate verification should use the `certifi` CA bundle.
- If code needs an explicit CA bundle path, use `certifi.where()`.

## LabArchives API

- This application uses the `labapi` package from PyPI for LabArchives access.
- `labapi` documentation is hosted at https://nimh-dsst.github.io/labapi/v1.0.3/index.html.
- Assume API credentials are provided through environment variables.
- Do not add or require a `.env` file for LabArchives credentials.
- Assume users log into LabArchives directly.
- Do not require users to provide an email address, username, or auth token in the application.

## Testing

- Tests use `pytest`.
- Add tests under `tests/` when introducing or changing behavior.
- Run tests with `uv run pytest`.

## Type Checking

- Type checking uses `mypy`.
- Run type checks with `uv run mypy`.
- `labapi` is treated as an untyped third-party dependency unless that package adds type information later.

## Formatting, Linting, and Imports

- Formatting uses `ruff format`.
- Linting and checks use `ruff check`.
- Import sorting is handled by Ruff; do not introduce a separate import-sorting tool.
- Run checks with `uv run ruff check .`.
- Run formatting with `uv run ruff format .`.
