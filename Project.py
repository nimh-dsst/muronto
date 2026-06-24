from __future__ import annotations

import html
import os
from typing import Any, Final
from urllib.parse import urlsplit, urlunsplit

import streamlit as st
from labapi import ApiError, AuthenticationError, Client, Notebook, User

from muronto_app.config import (
    ASP_KEY,
    DEFAULT_OPTIONS,
    DEFAULT_PROJECT_ID_KEY,
    DEFAULT_VALUES,
    INVESTIGATOR_KEY,
    LA_HOME_FOLDER_KEY,
    OPTIONS_KEY,
    OTHER_CHOICE,
    PI_KEY,
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    PROJECTS_KEY,
    SPECIES_KEY,
    choice_options,
    clean_string,
    get_project,
    investigator_for_user,
    normalize_options,
    project_ids,
    select_project_id,
    upsert_project_config,
)
from muronto_app.labarchives import (
    absolute_path,
    create_directory,
    create_root_config_page,
    find_root_config_page,
    read_config_attachment,
    save_config_attachment,
    sorted_directories,
)
from muronto_app.state import (
    ACCESS_KEY_ID_INPUT_KEY,
    ACCESS_KEY_PASSWORD_INPUT_KEY,
    AUTH_CODE_INPUT_KEY,
    BASE_URL_INPUT_KEY,
    CLIENT_STATE_KEY,
    CONFIG_ATTACHMENT_STATE_KEY,
    CONFIG_ERROR_STATE_KEY,
    CONFIG_FOLDER_PATH_KEY,
    CONFIG_FOLDER_SELECT_KEY,
    CONFIG_PAGE_ID_STATE_KEY,
    CONFIG_PAGE_STATE_KEY,
    CONFIG_SELECTED_HOME_FOLDER_KEY,
    CONFIG_STATE_KEY,
    FOLDER_SELECTION_PLACEHOLDER,
    LAST_CALLBACK_KEY,
    SELECTED_NOTEBOOK_ID_KEY,
    SELECTED_NOTEBOOK_NAME_STATE_KEY,
    SELECTED_NOTEBOOK_STATE_KEY,
    SELECTED_PROJECT_ID_STATE_KEY,
    SELECTED_PROJECT_WIDGET_KEY,
    USER_EMAIL_INPUT_KEY,
    USER_STATE_KEY,
    project_state_keys,
)

DEFAULT_API_URL: Final[str] = "https://api.labarchives.com"
CLIENT_ENV_VARS: Final[tuple[str, str]] = ("ACCESS_KEYID", "ACCESS_PWD")
LABARCHIVES_BUTTON_BLUE: Final[str] = "#0b66d4"
LABARCHIVES_BUTTON_BLUE_HOVER: Final[str] = "#0953ac"
PROJECT_FORM_CONTEXT_KEY: Final[str] = "muronto_project_form_context"


st.set_page_config(page_title="Muronto Project", layout="centered")


def init_state() -> None:
    st.session_state.setdefault(
        BASE_URL_INPUT_KEY,
        os.getenv("API_URL", DEFAULT_API_URL),
    )
    st.session_state.setdefault(ACCESS_KEY_ID_INPUT_KEY, "")
    st.session_state.setdefault(ACCESS_KEY_PASSWORD_INPUT_KEY, "")
    st.session_state.setdefault(USER_EMAIL_INPUT_KEY, "")
    st.session_state.setdefault(AUTH_CODE_INPUT_KEY, "")
    st.session_state.setdefault(CLIENT_STATE_KEY, None)
    st.session_state.setdefault(USER_STATE_KEY, None)
    st.session_state.setdefault(LAST_CALLBACK_KEY, "")
    st.session_state.setdefault(CONFIG_FOLDER_PATH_KEY, "")
    st.session_state.setdefault(CONFIG_SELECTED_HOME_FOLDER_KEY, "")
    st.session_state.setdefault(
        CONFIG_FOLDER_SELECT_KEY,
        FOLDER_SELECTION_PLACEHOLDER,
    )


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def missing_client_env_vars() -> list[str]:
    return [name for name in CLIENT_ENV_VARS if not clean(os.getenv(name))]


def build_client() -> Client:
    return Client(
        base_url=clean(st.session_state[BASE_URL_INPUT_KEY]),
        akid=clean(st.session_state[ACCESS_KEY_ID_INPUT_KEY]),
        akpass=clean(st.session_state[ACCESS_KEY_PASSWORD_INPUT_KEY]),
    )


def get_redirect_url() -> str | None:
    current_url = clean(getattr(st.context, "url", None))
    if current_url is None:
        return None

    parsed = urlsplit(current_url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def complete_login(user_email: str, auth_code: str) -> User:
    client = build_client()
    user = client.login(user_email.strip(), auth_code.strip())
    st.session_state[CLIENT_STATE_KEY] = client
    st.session_state[USER_STATE_KEY] = user
    return user


def reset_project_state() -> None:
    for key in project_state_keys():
        st.session_state.pop(key, None)
    st.session_state.pop(PROJECT_FORM_CONTEXT_KEY, None)
    st.session_state[CONFIG_FOLDER_PATH_KEY] = ""
    st.session_state[CONFIG_SELECTED_HOME_FOLDER_KEY] = ""
    st.session_state[CONFIG_FOLDER_SELECT_KEY] = FOLDER_SELECTION_PLACEHOLDER


def logout() -> None:
    client = st.session_state.get(CLIENT_STATE_KEY)
    if client is not None and hasattr(client, "close"):
        client.close()

    st.session_state[CLIENT_STATE_KEY] = None
    st.session_state[USER_STATE_KEY] = None
    st.session_state[AUTH_CODE_INPUT_KEY] = ""
    st.session_state[LAST_CALLBACK_KEY] = ""
    reset_project_state()
    st.query_params.clear()
    st.rerun()


def process_callback() -> None:
    callback_auth_code = st.query_params.get("auth_code")
    callback_email = st.query_params.get("email")
    callback_error = st.query_params.get("error")

    if callback_email:
        st.session_state[USER_EMAIL_INPUT_KEY] = callback_email
    if callback_auth_code:
        st.session_state[AUTH_CODE_INPUT_KEY] = callback_auth_code

    if callback_error:
        st.error(
            f"LabArchives returned an authentication error: {callback_error}"
        )
        return

    if not callback_auth_code or not callback_email:
        return

    callback_signature = f"{callback_email}:{callback_auth_code}"
    if callback_signature == st.session_state[LAST_CALLBACK_KEY]:
        return

    try:
        with st.spinner("Completing LabArchives sign-in..."):
            complete_login(callback_email, callback_auth_code)
    except AuthenticationError as exc:
        st.error(f"Authentication failed: {exc}")
        return
    except ApiError as exc:
        st.error(f"LabArchives rejected the callback: {exc}")
        return

    st.session_state[LAST_CALLBACK_KEY] = callback_signature
    st.query_params.clear()
    st.rerun()


def render_header() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(180deg, #f7fbff 0%, #eef5ef 100%);
        }}
        .hero {{
            padding: 1.5rem 1.6rem;
            border-radius: 0.6rem;
            color: white;
            background: linear-gradient(
                135deg,
                #11383f 0%,
                #1f6172 58%,
                #84b88c 100%
            );
            box-shadow: 0 18px 40px rgba(17, 56, 63, 0.16);
            margin-bottom: 1rem;
        }}
        .hero h1 {{
            margin: 0;
            font-size: 2.1rem;
            line-height: 1.1;
        }}
        .hero p {{
            margin: 0.65rem 0 0 0;
            max-width: 34rem;
            font-size: 1rem;
            line-height: 1.55;
        }}
        .labarchives-link-button {{
            display: flex;
            width: 100%;
            min-height: 2.5rem;
            align-items: center;
            justify-content: center;
            padding: 0.55rem 1rem;
            border-radius: 0.5rem;
            background: {LABARCHIVES_BUTTON_BLUE};
            color: white !important;
            font-weight: 600;
            text-decoration: none;
            box-sizing: border-box;
            transition: background-color 120ms ease-in-out;
        }}
        .labarchives-link-button:hover {{
            background: {LABARCHIVES_BUTTON_BLUE_HOVER};
        }}
        </style>
        <div class="hero">
            <h1>Muronto</h1>
            <p>
                Connect LabArchives, choose a project notebook, and prepare
                the shared muronto_config JSON.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_form() -> None:
    missing_env_vars = missing_client_env_vars()
    if missing_env_vars:
        st.error(
            "LabArchives API credentials are missing from the environment: "
            + ", ".join(f"`{name}`" for name in missing_env_vars)
            + "."
        )
        return

    redirect_url = get_redirect_url()
    if redirect_url is None:
        st.info("The LabArchives sign-in link is not ready yet.")
        return

    try:
        auth_url = build_client().generate_auth_url(redirect_url)
    except AuthenticationError as exc:
        st.error(f"Unable to configure LabArchives API access: {exc}")
        return
    except ApiError as exc:
        st.error(f"Unable to generate LabArchives sign-in URL: {exc}")
        return

    st.subheader("LabArchives sign-in")
    st.markdown(
        (
            '<a class="labarchives-link-button" '
            f'href="{html.escape(auth_url, quote=True)}" '
            'target="_self">'
            "Open LabArchives sign-in"
            "</a>"
        ),
        unsafe_allow_html=True,
    )


def sorted_notebooks(user: User) -> list[Any]:
    return sorted(
        user.notebooks.values(),
        key=lambda notebook: (not notebook.is_default, notebook.name.lower()),
    )


def render_notebook_selection(user: User) -> Notebook | None:
    notebooks = sorted_notebooks(user)
    left, right = st.columns(2)
    left.metric("Accessible notebooks", len(notebooks))

    default_notebook = next(
        (notebook for notebook in notebooks if notebook.is_default),
        None,
    )
    right.metric(
        "Default notebook",
        default_notebook.name if default_notebook else "Not set",
    )

    if not notebooks:
        st.warning("No LabArchives notebooks are available for this account.")
        return None

    notebook_options = [notebook.id for notebook in notebooks]
    default_notebook_id = (
        default_notebook.id
        if default_notebook is not None
        else notebook_options[0]
    )

    if st.session_state.get(SELECTED_NOTEBOOK_ID_KEY) not in notebook_options:
        st.session_state[SELECTED_NOTEBOOK_ID_KEY] = default_notebook_id

    notebooks_by_id = {notebook.id: notebook for notebook in notebooks}
    selected_notebook_id = st.selectbox(
        "Choose a notebook",
        options=notebook_options,
        key=SELECTED_NOTEBOOK_ID_KEY,
        on_change=reset_project_state,
        format_func=lambda notebook_id: (
            f"{notebooks_by_id[notebook_id].name} (Default)"
            if notebooks_by_id[notebook_id].is_default
            else notebooks_by_id[notebook_id].name
        ),
    )

    selected_notebook = notebooks_by_id[selected_notebook_id]
    st.session_state[SELECTED_NOTEBOOK_STATE_KEY] = selected_notebook
    st.session_state[SELECTED_NOTEBOOK_NAME_STATE_KEY] = selected_notebook.name
    return selected_notebook


def render_select_with_other(
    label: str,
    key: str,
    options: dict[str, list[str]],
    *,
    default_value: str,
    widget_prefix: str,
) -> str:
    choices = choice_options(options, key)
    selected_default = (
        default_value if default_value in choices else choices[0]
    )
    selected = st.selectbox(
        label,
        options=choices,
        index=choices.index(selected_default),
        key=f"{widget_prefix}_{key}",
    )

    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            f"New {label}",
            key=f"{widget_prefix}_{key}_other",
        )
    )


def relative_folder_path(notebook: Notebook, folder: Any) -> str:
    if folder is notebook:
        return ""
    return folder.path.relative_to(notebook).to_string()


def render_folder_breadcrumbs(notebook: Notebook) -> None:
    current_path = st.session_state[CONFIG_FOLDER_PATH_KEY]
    segments = [segment for segment in current_path.split("/") if segment]
    crumbs: list[tuple[str, str]] = [(notebook.name, "")]

    for index in range(len(segments)):
        crumbs.append((segments[index], "/".join(segments[: index + 1])))

    columns = st.columns((len(crumbs) * 2) - 1)
    for index, (label, path_value) in enumerate(crumbs):
        if columns[index * 2].button(
            label,
            key=f"home_folder_crumb_{index}_{path_value or 'root'}",
            use_container_width=True,
        ):
            st.session_state[CONFIG_FOLDER_PATH_KEY] = path_value
            st.session_state[CONFIG_FOLDER_SELECT_KEY] = (
                FOLDER_SELECTION_PLACEHOLDER
            )
            st.rerun()

        if index < len(crumbs) - 1:
            columns[(index * 2) + 1].markdown(
                "<div style='text-align:center;padding-top:0.45rem;'>/</div>",
                unsafe_allow_html=True,
            )


def current_folder(notebook: Notebook) -> Any:
    current_path = st.session_state[CONFIG_FOLDER_PATH_KEY]
    if not current_path:
        return notebook
    return notebook.traverse(current_path).as_dir()


def render_home_folder_picker(notebook: Notebook) -> str:
    st.subheader("LabArchives home folder")
    selected_home = st.session_state.get(CONFIG_SELECTED_HOME_FOLDER_KEY, "")

    try:
        folder = current_folder(notebook)
        directories = sorted_directories(folder)
    except Exception as exc:
        st.error("The current notebook folder could not be loaded.")
        st.caption(str(exc))
        st.session_state[CONFIG_FOLDER_PATH_KEY] = ""
        st.session_state[CONFIG_FOLDER_SELECT_KEY] = (
            FOLDER_SELECTION_PLACEHOLDER
        )
        return selected_home

    render_folder_breadcrumbs(notebook)
    current_path = absolute_path(folder)
    st.caption(f"Current folder: `{current_path}`")

    if st.button("Select this folder", use_container_width=True):
        st.session_state[CONFIG_SELECTED_HOME_FOLDER_KEY] = current_path
        selected_home = current_path

    if selected_home:
        st.success(f"Selected home folder: {selected_home}")

    if directories:
        directory_options = [FOLDER_SELECTION_PLACEHOLDER] + [
            directory.id for directory in directories
        ]
        directories_by_id = {
            directory.id: directory for directory in directories
        }
        if (
            st.session_state.get(CONFIG_FOLDER_SELECT_KEY)
            not in directory_options
        ):
            st.session_state[CONFIG_FOLDER_SELECT_KEY] = (
                FOLDER_SELECTION_PLACEHOLDER
            )

        selected_directory_id = st.selectbox(
            "Open folder",
            options=directory_options,
            key=CONFIG_FOLDER_SELECT_KEY,
            format_func=lambda directory_id: (
                "Choose a folder"
                if directory_id == FOLDER_SELECTION_PLACEHOLDER
                else directories_by_id[directory_id].name
            ),
        )
        if selected_directory_id != FOLDER_SELECTION_PLACEHOLDER:
            selected_directory = directories_by_id[selected_directory_id]
            st.session_state[CONFIG_FOLDER_PATH_KEY] = relative_folder_path(
                notebook,
                selected_directory,
            )
            st.session_state[CONFIG_FOLDER_SELECT_KEY] = (
                FOLDER_SELECTION_PLACEHOLDER
            )
            st.rerun()
    else:
        st.info("This folder has no child folders.")

    with st.form("create_home_folder_form", clear_on_submit=True):
        new_folder_name = st.text_input("New folder name")
        create_folder = st.form_submit_button(
            "Create and select folder",
            use_container_width=True,
        )

    if create_folder:
        try:
            created_folder = create_directory(folder, new_folder_name)
        except ValueError as exc:
            st.error(str(exc))
        except ApiError as exc:
            st.error(f"Unable to create the folder: {exc}")
        else:
            created_path = absolute_path(created_folder)
            st.session_state[CONFIG_SELECTED_HOME_FOLDER_KEY] = created_path
            st.session_state[CONFIG_FOLDER_PATH_KEY] = relative_folder_path(
                notebook,
                created_folder,
            )
            st.success(f"Created and selected `{created_path}`.")
            st.rerun()

    return st.session_state.get(CONFIG_SELECTED_HOME_FOLDER_KEY, "")


def reset_config_folder_state() -> None:
    st.session_state[CONFIG_FOLDER_PATH_KEY] = ""
    st.session_state[CONFIG_SELECTED_HOME_FOLDER_KEY] = ""
    st.session_state[CONFIG_FOLDER_SELECT_KEY] = FOLDER_SELECTION_PLACEHOLDER
    st.session_state.pop(PROJECT_FORM_CONTEXT_KEY, None)


def sync_active_project_selection() -> None:
    selected_project_id = st.session_state.get(SELECTED_PROJECT_WIDGET_KEY)
    if selected_project_id:
        st.session_state[SELECTED_PROJECT_ID_STATE_KEY] = selected_project_id
    reset_config_folder_state()


def prepare_home_folder_picker(
    *,
    context_key: str,
    initial_home_folder: str,
) -> None:
    if st.session_state.get(PROJECT_FORM_CONTEXT_KEY) == context_key:
        return

    st.session_state[PROJECT_FORM_CONTEXT_KEY] = context_key
    st.session_state[CONFIG_FOLDER_PATH_KEY] = ""
    st.session_state[CONFIG_SELECTED_HOME_FOLDER_KEY] = initial_home_folder
    st.session_state[CONFIG_FOLDER_SELECT_KEY] = FOLDER_SELECTION_PLACEHOLDER


def format_project_label(config: dict[str, Any], project_id: str) -> str:
    project = get_project(config, project_id)
    if project is None:
        return project_id
    return f"{project_id} - {project[PROJECT_NAME_KEY]}"


def render_active_project_selector(
    config: dict[str, Any],
    user: User,
) -> str:
    available_project_ids = project_ids(config)
    selected_project_id = select_project_id(
        config,
        user.email,
        st.session_state.get(SELECTED_PROJECT_ID_STATE_KEY),
    )
    if selected_project_id:
        st.session_state[SELECTED_PROJECT_ID_STATE_KEY] = selected_project_id
        st.session_state[SELECTED_PROJECT_WIDGET_KEY] = selected_project_id

    return st.selectbox(
        "Active project",
        options=available_project_ids,
        key=SELECTED_PROJECT_WIDGET_KEY,
        on_change=sync_active_project_selection,
        format_func=lambda project_id: format_project_label(
            config,
            project_id,
        ),
    )


def render_config_summary(
    config: dict[str, Any],
    project: dict[str, str],
    investigator: str,
) -> None:
    st.success("muronto_config is ready.")
    st.subheader("Active project")
    st.write(f"Project ID: {project[PROJECT_ID_KEY]}")
    st.write(f"Project name: {project[PROJECT_NAME_KEY]}")
    st.write(f"LabArchives home folder: {project[LA_HOME_FOLDER_KEY]}")
    st.write(f"Investigator: {investigator}")
    st.write(f"PI: {project[PI_KEY]}")
    st.write(f"Species: {project[SPECIES_KEY]}")
    st.write(f"ASP: {project[ASP_KEY]}")
    st.caption(
        f"{len(config[PROJECTS_KEY])} project"
        f"{'' if len(config[PROJECTS_KEY]) == 1 else 's'} configured. "
        f"Notebook default: {config[DEFAULT_PROJECT_ID_KEY]}."
    )

    with st.expander("Config JSON", expanded=False):
        st.json(config)


def render_dropdown_option_viewer(config: dict[str, Any]) -> None:
    """Render a read-only view of saved dropdown option values."""
    options = normalize_options(config.get(OPTIONS_KEY))
    default_options = normalize_options(DEFAULT_OPTIONS)
    if not options:
        return

    with st.expander("Manage dropdown options", expanded=False):
        st.caption(
            "Read-only view. These are the dropdown values currently saved "
            "in muronto_config."
        )

        option_keys = sorted(options)
        selected_key = st.selectbox(
            "Option category",
            options=option_keys,
            key="config_option_viewer_category",
        )

        values = options.get(selected_key, [])
        default_values = set(default_options.get(selected_key, []))

        custom_values = [
            value for value in values
            if value not in default_values
        ]

        st.write(f"{len(values)} value(s) saved for `{selected_key}`.")

        if not values:
            st.info("No values are saved for this option category.")
            return

        if custom_values:
            st.warning(
                f"{len(custom_values)} custom/saved value(s) are not present in "
                "the current source-code defaults."
            )
            st.dataframe(
                [
                    {
                        "Custom value": value,
                        "Reason": "Not present in source-code defaults",
                    }
                    for value in custom_values
                ],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.success(
                "All saved values for this category are present in the current "
                "source-code defaults."
            )

        st.dataframe(
            [
                {
                    "Value": value,
                    "Source": (
                        "Default/source code"
                        if value in default_values
                        else "Custom/saved"
                    ),
                }
                for value in values
            ],
            use_container_width=True,
            hide_index=True,
        )


def project_form_defaults(
    project: dict[str, str] | None,
) -> dict[str, str]:
    defaults: dict[str, str] = {}
    for key in (
        PROJECT_ID_KEY,
        PROJECT_NAME_KEY,
        LA_HOME_FOLDER_KEY,
        PI_KEY,
        SPECIES_KEY,
        ASP_KEY,
    ):
        defaults[key] = (
            clean_string(project.get(key))
            if project is not None
            else DEFAULT_VALUES[key]
        )
    return defaults


def save_project_config(
    *,
    user: User,
    config_page: Any,
    existing_entry: Any | None,
    existing_config: dict[str, Any] | None,
    selected_values: dict[str, str],
    investigator: str,
    remember_investigator: bool,
    make_default: bool,
    options: dict[str, list[str]],
) -> None:
    missing_fields = [
        key
        for key, value in selected_values.items()
        if not clean_string(value)
    ]
    if not clean_string(investigator):
        missing_fields.append(INVESTIGATOR_KEY)

    if missing_fields:
        st.error(
            "Complete these fields before saving: "
            + ", ".join(missing_fields)
            + "."
        )
        return

    try:
        config = upsert_project_config(
            existing_config,
            selected_values,
            investigator=investigator,
            options=options,
            user_email=user.email,
            remember_investigator=remember_investigator,
            remember_project=True,
            make_default=make_default,
        )
        attachment_entry = save_config_attachment(
            config_page,
            config,
            existing_entry=existing_entry,
        )
    except ApiError as exc:
        st.error(f"Unable to save muronto_config JSON: {exc}")
        return
    except ValueError as exc:
        st.error(str(exc))
        return

    st.session_state[CONFIG_STATE_KEY] = config
    st.session_state[CONFIG_ATTACHMENT_STATE_KEY] = attachment_entry
    st.session_state[CONFIG_PAGE_STATE_KEY] = config_page
    st.session_state[CONFIG_PAGE_ID_STATE_KEY] = config_page.id
    st.session_state[CONFIG_ERROR_STATE_KEY] = None
    st.session_state[SELECTED_PROJECT_ID_STATE_KEY] = selected_values[
        PROJECT_ID_KEY
    ]
    st.success("Saved muronto_config JSON.")
    st.rerun()


def render_project_editor(
    user: User,
    notebook: Notebook,
    config_page: Any,
    *,
    existing_entry: Any | None,
    existing_config: dict[str, Any] | None,
    project: dict[str, str] | None,
    mode: str,
) -> None:
    is_edit = project is not None
    heading = "Edit project" if is_edit else "Add project"
    st.subheader(heading)

    options = normalize_options(
        existing_config.get(OPTIONS_KEY)
        if existing_config is not None
        else DEFAULT_OPTIONS
    )
    defaults = project_form_defaults(project)
    widget_prefix = (
        f"project_edit_{defaults[PROJECT_ID_KEY]}"
        if is_edit
        else "project_add"
    )

    prepare_home_folder_picker(
        context_key=f"{mode}:{defaults[PROJECT_ID_KEY] if is_edit else 'new'}",
        initial_home_folder=(defaults[LA_HOME_FOLDER_KEY] if is_edit else ""),
    )

    selected_values: dict[str, str] = {}
    selected_values[PROJECT_ID_KEY] = clean_string(
        st.text_input(
            "Project ID",
            value=defaults[PROJECT_ID_KEY] if is_edit else "",
            disabled=is_edit,
            key=f"{widget_prefix}_{PROJECT_ID_KEY}",
        )
    )
    selected_values[PROJECT_NAME_KEY] = clean_string(
        st.text_input(
            "Project name",
            value=defaults[PROJECT_NAME_KEY] if is_edit else "",
            key=f"{widget_prefix}_{PROJECT_NAME_KEY}",
        )
    )

    investigator = render_select_with_other(
        "Investigator",
        INVESTIGATOR_KEY,
        options,
        default_value=investigator_for_user(existing_config or {}, user.email),
        widget_prefix=widget_prefix,
    )
    remember_email = st.checkbox(
        "Use this investigator for my LabArchives email",
        value=True,
        key=f"{widget_prefix}_remember_investigator",
    )

    selected_values[PI_KEY] = render_select_with_other(
        "PI",
        PI_KEY,
        options,
        default_value=defaults[PI_KEY],
        widget_prefix=widget_prefix,
    )

    selected_values[SPECIES_KEY] = render_select_with_other(
        "Species",
        SPECIES_KEY,
        options,
        default_value=defaults[SPECIES_KEY],
        widget_prefix=widget_prefix,
    )
    selected_values[ASP_KEY] = render_select_with_other(
        "ASP",
        ASP_KEY,
        options,
        default_value=defaults[ASP_KEY],
        widget_prefix=widget_prefix,
    )
    selected_values[LA_HOME_FOLDER_KEY] = render_home_folder_picker(notebook)

    make_default = st.checkbox(
        "Set this as the notebook default project",
        value=(existing_config is None or not project_ids(existing_config)),
        key=f"{widget_prefix}_make_default",
    )

    if st.button("Save project", type="primary", key=f"{widget_prefix}_save"):
        save_project_config(
            user=user,
            config_page=config_page,
            existing_entry=existing_entry,
            existing_config=existing_config,
            selected_values=selected_values,
            investigator=investigator,
            remember_investigator=remember_email,
            make_default=make_default,
            options=options,
        )


def render_project_manager(
    user: User,
    notebook: Notebook,
    config_page: Any,
    config: dict[str, Any],
    existing_entry: Any | None,
) -> None:
    selected_project_id = render_active_project_selector(config, user)
    project = get_project(config, selected_project_id)
    if project is None:
        st.error("The selected project could not be loaded.")
        return

    render_config_summary(
        config,
        project,
        investigator_for_user(config, user.email),
    )

    render_dropdown_option_viewer(config)

    action = st.radio(
        "Project action",
        options=("Edit selected project", "Add project"),
        horizontal=True,
        key="project_action",
        on_change=reset_config_folder_state,
    )
    render_project_editor(
        user,
        notebook,
        config_page,
        existing_entry=existing_entry,
        existing_config=config,
        project=project if action == "Edit selected project" else None,
        mode=action,
    )


def render_project_config(user: User, notebook: Notebook) -> None:
    st.subheader("muronto_config")

    try:
        config_page = find_root_config_page(notebook)
    except ApiError as exc:
        st.error(f"Unable to inspect the notebook root: {exc}")
        return

    if config_page is None:
        st.info(
            "This notebook does not have a root-level muronto_config page."
        )
        if st.button("Create muronto_config page", type="primary"):
            try:
                config_page = create_root_config_page(notebook)
            except ApiError as exc:
                st.error(f"Unable to create muronto_config: {exc}")
                return

            st.session_state[CONFIG_PAGE_STATE_KEY] = config_page
            st.session_state[CONFIG_PAGE_ID_STATE_KEY] = config_page.id
            st.rerun()
        return

    cached_config = st.session_state.get(CONFIG_STATE_KEY)
    cached_page_id = st.session_state.get(CONFIG_PAGE_ID_STATE_KEY)
    if isinstance(cached_config, dict) and cached_page_id == config_page.id:
        st.session_state[CONFIG_PAGE_STATE_KEY] = config_page
        render_project_manager(
            user,
            notebook,
            config_page,
            cached_config,
            st.session_state.get(CONFIG_ATTACHMENT_STATE_KEY),
        )
        return

    st.session_state[CONFIG_PAGE_STATE_KEY] = config_page
    st.session_state[CONFIG_PAGE_ID_STATE_KEY] = config_page.id

    read_result = read_config_attachment(config_page)
    if read_result.config is not None:
        st.session_state[CONFIG_STATE_KEY] = read_result.config
        st.session_state[CONFIG_ATTACHMENT_STATE_KEY] = read_result.entry
        render_project_manager(
            user,
            notebook,
            config_page,
            read_result.config,
            read_result.entry,
        )
        return

    st.session_state[CONFIG_ERROR_STATE_KEY] = read_result.errors
    if read_result.entry is None:
        st.info("No muronto_config JSON attachment was found.")
    else:
        st.warning("The existing muronto_config JSON needs to be replaced.")
        for error in read_result.errors:
            st.caption(error)

    render_project_editor(
        user,
        notebook,
        config_page,
        existing_entry=read_result.entry,
        existing_config=None,
        project=None,
        mode="Create config",
    )


def render_logged_in(user: User) -> None:
    st.success(f"Signed in as {user.email}")
    selected_notebook = render_notebook_selection(user)
    if selected_notebook is not None:
        render_project_config(user, selected_notebook)

    if st.button("Sign out", type="secondary", use_container_width=True):
        logout()


def main() -> None:
    init_state()
    render_header()
    process_callback()

    user = st.session_state[USER_STATE_KEY]
    if user is None:
        render_login_form()
        return

    render_logged_in(user)


if __name__ == "__main__":
    main()
