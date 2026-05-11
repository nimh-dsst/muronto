"""Streamlit session-state keys used across Muronto pages."""

from __future__ import annotations

from typing import Final

CLIENT_STATE_KEY: Final[str] = "labapi_client"
USER_STATE_KEY: Final[str] = "labapi_user"
LAST_CALLBACK_KEY: Final[str] = "labapi_last_callback"

BASE_URL_INPUT_KEY: Final[str] = "login_base_url"
ACCESS_KEY_ID_INPUT_KEY: Final[str] = "login_access_key_id"
ACCESS_KEY_PASSWORD_INPUT_KEY: Final[str] = "login_access_key_password"
USER_EMAIL_INPUT_KEY: Final[str] = "login_user_email"
AUTH_CODE_INPUT_KEY: Final[str] = "login_auth_code"

SELECTED_NOTEBOOK_ID_KEY: Final[str] = "selected_notebook_id"
SELECTED_NOTEBOOK_STATE_KEY: Final[str] = "selected_notebook"
SELECTED_NOTEBOOK_NAME_STATE_KEY: Final[str] = "selected_notebook_name"
SELECTED_PROJECT_ID_STATE_KEY: Final[str] = "selected_project_id"

CONFIG_PAGE_STATE_KEY: Final[str] = "muronto_config_page"
CONFIG_PAGE_ID_STATE_KEY: Final[str] = "muronto_config_page_id"
CONFIG_ATTACHMENT_STATE_KEY: Final[str] = "muronto_config_attachment"
CONFIG_STATE_KEY: Final[str] = "muronto_config"
CONFIG_ERROR_STATE_KEY: Final[str] = "muronto_config_error"

CONFIG_FOLDER_PATH_KEY: Final[str] = "muronto_config_folder_path"
CONFIG_SELECTED_HOME_FOLDER_KEY: Final[str] = "muronto_config_home_folder"
CONFIG_FOLDER_SELECT_KEY: Final[str] = "muronto_config_folder_select"

FOLDER_SELECTION_PLACEHOLDER: Final[str] = "__select_folder__"


def project_state_keys() -> tuple[str, ...]:
    """Return state keys that belong to the selected project/notebook."""
    return (
        SELECTED_NOTEBOOK_STATE_KEY,
        SELECTED_NOTEBOOK_NAME_STATE_KEY,
        SELECTED_PROJECT_ID_STATE_KEY,
        CONFIG_PAGE_STATE_KEY,
        CONFIG_PAGE_ID_STATE_KEY,
        CONFIG_ATTACHMENT_STATE_KEY,
        CONFIG_STATE_KEY,
        CONFIG_ERROR_STATE_KEY,
        CONFIG_FOLDER_PATH_KEY,
        CONFIG_SELECTED_HOME_FOLDER_KEY,
        CONFIG_FOLDER_SELECT_KEY,
    )
