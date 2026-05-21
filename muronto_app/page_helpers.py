"""Shared rendering helpers for secondary Streamlit pages."""

from __future__ import annotations

from typing import Any

import streamlit as st

from muronto_app.config import (
    ASP_KEY,
    LA_HOME_FOLDER_KEY,
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    SPECIES_KEY,
    active_project,
    investigator_for_user,
)
from muronto_app.state import (
    CONFIG_STATE_KEY,
    SELECTED_NOTEBOOK_NAME_STATE_KEY,
    SELECTED_PROJECT_ID_STATE_KEY,
    USER_STATE_KEY,
)


def ready_context() -> tuple[Any, dict[str, Any], dict[str, str]] | None:
    """Return the logged-in user, config, and active project."""
    user = st.session_state.get(USER_STATE_KEY)
    config = st.session_state.get(CONFIG_STATE_KEY)
    notebook_name = st.session_state.get(SELECTED_NOTEBOOK_NAME_STATE_KEY)

    if user is None:
        st.warning("Sign in to LabArchives from the Project page first.")
        st.page_link("Project.py", label="Open Project")
        return None

    if not isinstance(config, dict) or notebook_name is None:
        st.warning("Select a notebook and complete muronto_config first.")
        st.page_link("Project.py", label="Open Project")
        return None

    project = active_project(
        config,
        user.email,
        st.session_state.get(SELECTED_PROJECT_ID_STATE_KEY),
    )
    if project is None:
        st.warning("Select an active project from the Project page first.")
        st.page_link("Project.py", label="Open Project")
        return None

    st.session_state[SELECTED_PROJECT_ID_STATE_KEY] = project[PROJECT_ID_KEY]
    return user, config, project


def render_project_context(
    page_title: str,
) -> tuple[Any, dict[str, Any], dict[str, str]] | None:
    """Render common context for a secondary page.

    Returns context when the page can continue rendering page-specific UI.
    """
    context = ready_context()
    if context is None:
        return None

    user, config, project = context
    notebook_name = st.session_state[SELECTED_NOTEBOOK_NAME_STATE_KEY]
    investigator = investigator_for_user(config, user.email)

    st.title(page_title)
    st.caption(f"Signed in as {user.email}")
    st.subheader("Project")
    st.write(f"Notebook: {notebook_name}")
    st.write(
        f"Project: {project[PROJECT_ID_KEY]} - {project[PROJECT_NAME_KEY]}"
    )
    st.write(f"Home folder: {project[LA_HOME_FOLDER_KEY]}")
    st.write(f"Investigator: {investigator}")
    st.write(f"Species: {project[SPECIES_KEY]}")
    st.write(f"ASP: {project[ASP_KEY]}")
    return context
