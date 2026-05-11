# muronto

Streamlit app for connecting to LabArchives ELN and recording neuro-behavior experimental records

## Environment setup

This project uses `uv` and targets Python `3.12`.

1. Create or update the project virtual environment and install dependencies with `uv sync`.
2. Activate the virtual environment with `source .venv/bin/activate`.
3. Run project commands with `uv run ...` or from the activated environment directly.

Example:

```bash
uv sync
source .venv/bin/activate
uv run streamlit run Project.py
```

Note: `labapi` is installed from PyPI.

## Using the Project page

Run the page with `streamlit run Project.py`, then sign in to LabArchives from the browser UI.

1. Configure API access with `ACCESS_KEYID` and `ACCESS_PWD` in the environment. `API_URL` is optional and defaults to `https://api.labarchives.com`.
2. Authenticate with LabArchives. Click `Open LabArchives sign-in` to complete the browser-based flow and return to the page automatically.
3. After sign-in, choose a notebook and create or reuse the root-level `muronto_config` page.
4. If the config JSON attachment is missing or invalid, complete the project configuration form and select a LabArchives home folder.
5. Use `Sign out` to clear the current session and return to the login form.
