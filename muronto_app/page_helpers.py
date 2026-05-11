"""Shared rendering helpers for secondary Streamlit pages."""

from __future__ import annotations

from typing import Any

import streamlit as st

from muronto_app.config import (
    ASP_KEY,
    INVESTIGATOR_KEY,
    LA_HOME_FOLDER_KEY,
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    SPECIES_KEY,
)
from muronto_app.state import (
    CONFIG_STATE_KEY,
    SELECTED_NOTEBOOK_NAME_STATE_KEY,
    USER_STATE_KEY,
)


def ready_context() -> tuple[Any, dict[str, Any]] | None:
    """Return the logged-in user and config, or render a Project-page guard."""
    user = st.session_state.get(USER_STATE_KEY)
    config = st.session_state.get(CONFIG_STATE_KEY)
    notebook_name = st.session_state.get(SELECTED_NOTEBOOK_NAME_STATE_KEY)

    if user is None:
        st.warning("Sign in to LabArchives from the Project page first.")
        st.page_link("Project.py", label="Open Project")
        return None

    if config is None or notebook_name is None:
        st.warning("Select a notebook and complete muronto_config first.")
        st.page_link("Project.py", label="Open Project")
        return None

    return user, config


def render_project_context(page_title: str) -> bool:
    """Render common context for a secondary page.

    Returns ``True`` when the page can continue rendering page-specific UI.
    """
    context = ready_context()
    if context is None:
        return False

    user, config = context
    notebook_name = st.session_state[SELECTED_NOTEBOOK_NAME_STATE_KEY]

    st.title(page_title)
    st.caption(f"Signed in as {user.email}")
    st.subheader("Project")
    st.write(f"Notebook: {notebook_name}")
    st.write(f"Project: {config[PROJECT_ID_KEY]} - {config[PROJECT_NAME_KEY]}")
    st.write(f"Home folder: {config[LA_HOME_FOLDER_KEY]}")
    st.write(f"Investigator: {config[INVESTIGATOR_KEY]}")
    st.write(f"Species: {config[SPECIES_KEY]}")
    st.write(f"ASP: {config[ASP_KEY]}")
    return True
