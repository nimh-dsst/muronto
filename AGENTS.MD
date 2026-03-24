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
