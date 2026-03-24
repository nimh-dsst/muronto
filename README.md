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
uv run streamlit run Login.py
```

Note: `labapi` is installed from a GitHub SSH URL, so `uv sync` requires GitHub SSH access to `nimh-dsst/labarchives-api`.

## Using the Login page

Run the page with `streamlit run Login.py`, then sign in to LabArchives from the browser UI.

1. Configure API access. If `API_URL`, `ACCESS_KEYID`, and `ACCESS_PWD` are set in the environment, the page will use them automatically. Otherwise, enter the API base URL, access key ID, and access key password in the form.
2. Authenticate with LabArchives. Click `Open LabArchives sign-in` to complete the browser-based flow and return to the page automatically, or enter your LabArchives email and a one-hour auth code manually and click the sign-in button.
3. After sign-in, choose a notebook, select whether you want to create a new surgery record or open an existing one, and use the notebook navigator to move through folders and pages.
4. Use `Sign out` to clear the current session and return to the login form.
