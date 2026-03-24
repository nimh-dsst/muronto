from __future__ import annotations

import html
import os
from typing import Final
from urllib.parse import urlsplit, urlunsplit

import streamlit as st
from labapi import (
    ApiError,
    AuthenticationError,
    Client,
    NodeExistsError,
    NotebookDirectory,
    NotebookPage,
    User,
)

DEFAULT_API_URL: Final[str] = "https://api.labarchives.com"
LABARCHIVES_BUTTON_BLUE: Final[str] = "#0b66d4"
LABARCHIVES_BUTTON_BLUE_HOVER: Final[str] = "#0953ac"
AUTH_BUTTON_GREEN: Final[str] = "#2f8f5b"
AUTH_BUTTON_GREEN_HOVER: Final[str] = "#256f47"
CLIENT_ENV_VARS: Final[tuple[str, str, str]] = (
    "API_URL",
    "ACCESS_KEYID",
    "ACCESS_PWD",
)

CLIENT_STATE_KEY: Final[str] = "labapi_client"
USER_STATE_KEY: Final[str] = "labapi_user"
LAST_CALLBACK_KEY: Final[str] = "labapi_last_callback"

BASE_URL_INPUT_KEY: Final[str] = "login_base_url"
ACCESS_KEY_ID_INPUT_KEY: Final[str] = "login_access_key_id"
ACCESS_KEY_PASSWORD_INPUT_KEY: Final[str] = "login_access_key_password"
USER_EMAIL_INPUT_KEY: Final[str] = "login_user_email"
AUTH_CODE_INPUT_KEY: Final[str] = "login_auth_code"
SELECTED_NOTEBOOK_ID_KEY: Final[str] = "selected_notebook_id"
SURGERY_RECORD_ACTION_KEY: Final[str] = "surgery_record_action"
CURRENT_DIRECTORY_PATH_KEY: Final[str] = "current_directory_path"
SELECTED_CHILD_NODE_ID_KEY: Final[str] = "selected_child_node_id"
SELECTED_PAGE_ID_KEY: Final[str] = "selected_page_id"
CHILD_SELECTION_PLACEHOLDER: Final[str] = "__select_child__"


st.set_page_config(page_title="Muronto Login", layout="centered")


def init_state() -> None:
    st.session_state.setdefault(
        BASE_URL_INPUT_KEY, os.getenv("API_URL", DEFAULT_API_URL)
    )
    st.session_state.setdefault(ACCESS_KEY_ID_INPUT_KEY, "")
    st.session_state.setdefault(ACCESS_KEY_PASSWORD_INPUT_KEY, "")
    st.session_state.setdefault(USER_EMAIL_INPUT_KEY, "")
    st.session_state.setdefault(AUTH_CODE_INPUT_KEY, "")
    st.session_state.setdefault(CLIENT_STATE_KEY, None)
    st.session_state.setdefault(USER_STATE_KEY, None)
    st.session_state.setdefault(LAST_CALLBACK_KEY, "")
    st.session_state.setdefault(CURRENT_DIRECTORY_PATH_KEY, "")
    st.session_state.setdefault(
        SELECTED_CHILD_NODE_ID_KEY, CHILD_SELECTION_PLACEHOLDER
    )
    st.session_state.setdefault(SELECTED_PAGE_ID_KEY, None)


def clean(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def missing_client_env_vars() -> list[str]:
    return [name for name in CLIENT_ENV_VARS if not clean(os.getenv(name, ""))]


def has_client_env_config() -> bool:
    return not missing_client_env_vars()


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


def can_build_client() -> bool:
    try:
        build_client()
    except AuthenticationError:
        return False

    return True


def complete_login(user_email: str, auth_code: str) -> User:
    client = build_client()
    user = client.login(user_email.strip(), auth_code.strip())
    st.session_state[CLIENT_STATE_KEY] = client
    st.session_state[USER_STATE_KEY] = user
    return user


def logout() -> None:
    st.session_state[CLIENT_STATE_KEY] = None
    st.session_state[USER_STATE_KEY] = None
    st.session_state[AUTH_CODE_INPUT_KEY] = ""
    st.session_state[LAST_CALLBACK_KEY] = ""
    st.session_state[CURRENT_DIRECTORY_PATH_KEY] = ""
    st.session_state[SELECTED_CHILD_NODE_ID_KEY] = CHILD_SELECTION_PLACEHOLDER
    st.session_state[SELECTED_PAGE_ID_KEY] = None
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
        st.info(
            "LabArchives returned with an auth code. Set `API_URL`, "
            "`ACCESS_KEYID`, and `ACCESS_PWD` in the environment, or "
            "enter the missing values above, to finish signing in."
        )
        st.caption(f"Authentication details from labapi: {exc}")
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
            background:
                radial-gradient(
                    circle at top right,
                    rgba(43, 104, 123, 0.15),
                    transparent 28%
                ),
                linear-gradient(180deg, #f7fbff 0%, #eef5ef 100%);
        }}
        .hero {{
            padding: 1.5rem 1.6rem;
            border-radius: 1rem;
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
            font-size: 2.3rem;
            line-height: 1.05;
        }}
        .hero p {{
            margin: 0.75rem 0 0 0;
            max-width: 34rem;
            font-size: 1rem;
            line-height: 1.55;
        }}
        .login-methods {{
            margin: 0 0 1rem 0;
            padding: 1rem 1.1rem;
            border-radius: 0.9rem;
            border: 1px solid rgba(17, 56, 63, 0.10);
            background: rgba(255, 255, 255, 0.78);
            box-shadow: 0 10px 24px rgba(17, 56, 63, 0.07);
        }}
        .login-methods h3 {{
            margin: 0 0 0.45rem 0;
            color: #11383f;
            font-size: 1rem;
        }}
        .login-methods ol {{
            margin: 0;
            padding-left: 1.2rem;
            color: #28464d;
            line-height: 1.6;
        }}
        .button-ref {{
            font-weight: 700;
        }}
        .button-ref-blue {{
            color: {LABARCHIVES_BUTTON_BLUE};
        }}
        .button-ref-green {{
            color: {AUTH_BUTTON_GREEN};
        }}
        .labarchives-link-button {{
            display: flex;
            width: 100%;
            min-height: 2.5rem;
            align-items: center;
            justify-content: center;
            padding: 0.55rem 1rem;
            border-radius: 0.55rem;
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
        button[kind="primary"] {{
            background: {AUTH_BUTTON_GREEN};
            border-color: {AUTH_BUTTON_GREEN};
        }}
        button[kind="primary"]:hover {{
            background: {AUTH_BUTTON_GREEN_HOVER};
            border-color: {AUTH_BUTTON_GREEN_HOVER};
        }}
        </style>
        <div class="hero">
            <h1>Muronto</h1>
            <p>
                Sign in to LabArchives before recording neuro-behavior
                experimental records.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def reset_navigation_state() -> None:
    st.session_state[CURRENT_DIRECTORY_PATH_KEY] = ""
    st.session_state[SELECTED_CHILD_NODE_ID_KEY] = CHILD_SELECTION_PLACEHOLDER
    st.session_state[SELECTED_PAGE_ID_KEY] = None


def get_location_label(notebook_name: str, relative_path: str) -> str:
    if not relative_path:
        return notebook_name
    return f"{notebook_name}/{relative_path}"


def validate_new_child_name(raw_name: str, node_label: str) -> str | None:
    name = clean(raw_name)
    if name is None:
        st.error(f"Enter a {node_label} name.")
        return None

    if "/" in name:
        st.error(f"{node_label.capitalize()} names cannot contain `/`.")
        return None

    if name in {".", ".."}:
        st.error(f"{node_label.capitalize()} names cannot be `.` or `..`.")
        return None

    return name


def create_child_node(
    current_container,
    node_class: type[NotebookDirectory] | type[NotebookPage],
    raw_name: str,
    node_label: str,
    location_label: str,
) -> None:
    name = validate_new_child_name(raw_name, node_label)
    if name is None:
        return

    try:
        new_node = current_container.create(node_class, name)
        current_container.refresh()
    except NodeExistsError:
        st.error(
            f"A {node_label} named `{name}` already exists in "
            f"`{location_label}`."
        )
        return
    except ApiError as exc:
        st.error(f"Unable to create the {node_label}: {exc}")
        return

    st.success(
        f"Created {node_label} `{new_node.name}` in `{location_label}`."
    )


def render_create_actions(current_container, location_label: str) -> None:
    st.subheader("Create in current folder")
    st.caption(
        f"Add a folder or page directly inside `{location_label}`. "
        "Names cannot include `/`."
    )

    directory_column, page_column = st.columns(2)

    with directory_column:
        with st.form("create_directory_form", clear_on_submit=True):
            st.markdown("**New folder**")
            directory_name = st.text_input("Folder name")
            create_directory = st.form_submit_button(
                "Create folder",
                use_container_width=True,
            )

        if create_directory:
            create_child_node(
                current_container,
                NotebookDirectory,
                directory_name,
                "folder",
                location_label,
            )

    with page_column:
        with st.form("create_page_form", clear_on_submit=True):
            st.markdown("**New page**")
            page_name = st.text_input("Page name")
            create_page = st.form_submit_button(
                "Create page",
                use_container_width=True,
            )

        if create_page:
            create_child_node(
                current_container,
                NotebookPage,
                page_name,
                "page",
                location_label,
            )


def get_current_container(selected_notebook):
    current_path = st.session_state[CURRENT_DIRECTORY_PATH_KEY]
    if not current_path:
        return selected_notebook

    return selected_notebook.traverse(current_path).as_dir()


def get_sorted_children(container) -> list:
    return sorted(
        container.children,
        key=lambda child: (not child.is_dir(), child.name.lower(), child.id),
    )


def render_breadcrumbs(selected_notebook) -> None:
    current_path = st.session_state[CURRENT_DIRECTORY_PATH_KEY]
    segments = [segment for segment in current_path.split("/") if segment]

    crumbs: list[tuple[str, str]] = [(selected_notebook.name, "")]
    for index in range(len(segments)):
        crumbs.append((segments[index], "/".join(segments[: index + 1])))

    st.caption("Notebook path")
    columns = st.columns((len(crumbs) * 2) - 1)

    for index, (label, path_value) in enumerate(crumbs):
        button_column = columns[index * 2]
        breadcrumb_key = (
            f"breadcrumb_{selected_notebook.id}_{index}_{path_value or 'root'}"
        )
        if button_column.button(
            label,
            key=breadcrumb_key,
            use_container_width=True,
        ):
            st.session_state[CURRENT_DIRECTORY_PATH_KEY] = path_value
            st.session_state[SELECTED_CHILD_NODE_ID_KEY] = (
                CHILD_SELECTION_PLACEHOLDER
            )
            st.session_state[SELECTED_PAGE_ID_KEY] = None
            st.rerun()

        if index < len(crumbs) - 1:
            columns[(index * 2) + 1].markdown(
                "<div style='text-align:center;padding-top:0.45rem;'>/</div>",
                unsafe_allow_html=True,
            )


def render_logged_in(user: User) -> None:
    st.success(f"Signed in as {user.email}")

    notebooks = sorted(
        user.notebooks.values(),
        key=lambda notebook: (not notebook.is_default, notebook.name.lower()),
    )

    left, right = st.columns(2)
    left.metric("Accessible notebooks", len(user.notebooks))

    default_notebook = next(
        (notebook for notebook in notebooks if notebook.is_default), None
    )
    right.metric(
        "Default notebook",
        default_notebook.name if default_notebook else "Not set",
    )

    if notebooks:
        st.subheader("Notebook selection")

        notebook_options = [notebook.id for notebook in notebooks]
        default_notebook_id = (
            default_notebook.id
            if default_notebook is not None
            else notebook_options[0]
        )

        if (
            st.session_state.get(SELECTED_NOTEBOOK_ID_KEY)
            not in notebook_options
        ):
            st.session_state[SELECTED_NOTEBOOK_ID_KEY] = default_notebook_id

        notebooks_by_id = {notebook.id: notebook for notebook in notebooks}

        selected_notebook_id = st.selectbox(
            "Choose a notebook",
            options=notebook_options,
            key=SELECTED_NOTEBOOK_ID_KEY,
            on_change=reset_navigation_state,
            format_func=lambda notebook_id: (
                f"{notebooks_by_id[notebook_id].name} (Default)"
                if notebooks_by_id[notebook_id].is_default
                else notebooks_by_id[notebook_id].name
            ),
        )
        selected_notebook = notebooks_by_id[selected_notebook_id]

        st.subheader("Surgery record")
        selected_action = st.radio(
            "What would you like to do?",
            options=[
                "Create a new surgery record",
                "Open an existing record",
            ],
            key=SURGERY_RECORD_ACTION_KEY,
            horizontal=True,
        )

        st.subheader("Notebook navigator")
        current_children: list = []
        navigator_available = True

        try:
            current_container = get_current_container(selected_notebook)
            current_children = get_sorted_children(current_container)
        except Exception as exc:
            st.error(
                "The notebook directory view could not be loaded. "
                "Navigation was reset to the notebook root."
            )
            st.caption(f"Navigator details: {exc}")
            reset_navigation_state()

            try:
                current_container = selected_notebook
                current_children = get_sorted_children(current_container)
            except Exception as recovery_exc:
                st.error("The notebook root could not be loaded.")
                st.caption(f"Root load details: {recovery_exc}")
                current_container = selected_notebook
                navigator_available = False

        render_breadcrumbs(selected_notebook)

        current_path = st.session_state[CURRENT_DIRECTORY_PATH_KEY]
        current_location_label = get_location_label(
            selected_notebook.name, current_path
        )
        st.caption(f"Current folder: `{current_location_label}`")
        if navigator_available:
            render_create_actions(current_container, current_location_label)
            current_children = get_sorted_children(current_container)
        else:
            st.info(
                "Notebook contents are unavailable until this folder can "
                "be loaded."
            )

        valid_child_ids = [CHILD_SELECTION_PLACEHOLDER] + [
            child.id for child in current_children
        ]
        page_ids = {
            child.id for child in current_children if not child.is_dir()
        }
        children_by_id = {child.id: child for child in current_children}

        if (
            st.session_state.get(SELECTED_CHILD_NODE_ID_KEY)
            not in valid_child_ids
        ):
            st.session_state[SELECTED_CHILD_NODE_ID_KEY] = (
                CHILD_SELECTION_PLACEHOLDER
            )
        if st.session_state.get(SELECTED_PAGE_ID_KEY) not in page_ids:
            st.session_state[SELECTED_PAGE_ID_KEY] = None

        if current_children:
            selected_child_id = st.selectbox(
                "Choose a folder or page",
                options=valid_child_ids,
                key=SELECTED_CHILD_NODE_ID_KEY,
                format_func=lambda child_id: (
                    "Choose a folder or page"
                    if child_id == CHILD_SELECTION_PLACEHOLDER
                    else (
                        f"Folder: {children_by_id[child_id].name}"
                        if children_by_id[child_id].is_dir()
                        else f"Page: {children_by_id[child_id].name}"
                    )
                ),
            )

            if selected_child_id == CHILD_SELECTION_PLACEHOLDER:
                st.session_state[SELECTED_PAGE_ID_KEY] = None
            else:
                selected_child = children_by_id[selected_child_id]

                if selected_child.is_dir():
                    st.session_state[CURRENT_DIRECTORY_PATH_KEY] = (
                        selected_child.path.relative_to(
                            selected_notebook
                        ).to_string()
                    )
                    st.session_state[SELECTED_PAGE_ID_KEY] = None
                    st.rerun()

                st.session_state[SELECTED_PAGE_ID_KEY] = selected_child.id
        elif navigator_available:
            st.info("This folder has no child folders or pages.")

        if selected_action == "Create a new surgery record":
            st.info(
                "A new surgery record will be created in "
                f"`{current_location_label}`."
            )
            if (
                st.session_state.get(SELECTED_CHILD_NODE_ID_KEY)
                != CHILD_SELECTION_PLACEHOLDER
                and current_children
            ):
                selected_child = children_by_id.get(
                    st.session_state[SELECTED_CHILD_NODE_ID_KEY]
                )
                if selected_child is not None and not selected_child.is_dir():
                    st.caption(
                        "Page selections are ignored while creating a new "
                        "surgery record. "
                        "The current folder remains the destination."
                    )
        else:
            selected_page = children_by_id.get(
                st.session_state[SELECTED_PAGE_ID_KEY]
            )
            if not navigator_available:
                st.info(
                    "Notebook contents are unavailable until the current "
                    "folder can be loaded."
                )
            elif selected_page is not None:
                st.info(
                    f"Ready to open `{selected_page.name}` from "
                    f"`{current_location_label}`."
                )
            elif not current_children:
                st.info(
                    "This folder is empty. Navigate to another folder to "
                    "open an existing record."
                )
            elif any(not child.is_dir() for child in current_children):
                st.info(
                    "Choose an existing page from the list above to open "
                    "that record."
                )
            else:
                st.info(
                    "This folder has no pages. Navigate into a folder to "
                    "find an existing record."
                )
    else:
        st.warning("No LabArchives notebooks are available for this account.")

    if st.button("Sign out", type="secondary", use_container_width=True):
        logout()


def render_login_methods(
    use_alternative_auth_code: bool, auth_url_available: bool
) -> None:
    auth_button_label = (
        "Sign in with alternative auth code"
        if use_alternative_auth_code
        else "Sign in with auth code"
    )

    browser_method_detail = (
        "This button is ready now."
        if auth_url_available
        else "This button becomes available after API access is configured."
    )

    st.markdown(
        f"""
        <div class="login-methods">
            <h3>Choose a login method first</h3>
            <ol>
                <li>
                    Click
                    <span class="button-ref button-ref-blue">
                        Open LabArchives sign-in
                    </span>
                    to authenticate in your browser.
                    {browser_method_detail}
                </li>
                <li>
                    Enter your LabArchives email and one-hour code, then
                    click
                    <span class="button-ref button-ref-green">
                        {html.escape(auth_button_label)}
                    </span>.
                </li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_form() -> None:
    missing_env_vars = missing_client_env_vars()
    use_alternative_auth_code = bool(missing_env_vars)
    has_usable_client_config = can_build_client()
    auth_button_label = (
        "Sign in with alternative auth code"
        if use_alternative_auth_code
        else "Sign in with auth code"
    )
    redirect_url = get_redirect_url()

    if redirect_url is None:
        auth_url = None
        auth_url_message = (
            "The current page URL is not available yet, so the "
            "LabArchives sign-in "
            "link cannot be generated from `st.context.url`."
        )
    elif not has_usable_client_config:
        auth_url = None
        auth_url_message = (
            "Set `API_URL`, `ACCESS_KEYID`, and `ACCESS_PWD` in the "
            "environment, "
            "or enter them above, before using the LabArchives sign-in link."
        )
    else:
        try:
            auth_url = build_client().generate_auth_url(redirect_url)
            auth_url_message = None
        except AuthenticationError:
            auth_url = None
            auth_url_message = (
                "Add API access credentials to generate the LabArchives "
                "sign-in link."
            )
        except Exception as exc:
            auth_url = None
            auth_url_message = (
                f"Unable to generate the LabArchives sign-in link: {exc}"
            )

    render_login_methods(
        use_alternative_auth_code=use_alternative_auth_code,
        auth_url_available=auth_url is not None,
    )

    st.subheader("API access")
    if has_client_env_config():
        st.success(
            "Using `API_URL`, `ACCESS_KEYID`, and `ACCESS_PWD` from "
            "the environment."
        )
    else:
        st.warning(
            "Environment credentials are incomplete. Missing: "
            + ", ".join(f"`{name}`" for name in missing_env_vars)
            + "."
        )
        st.text_input(
            "API base URL",
            key=BASE_URL_INPUT_KEY,
            help="Usually https://api.labarchives.com.",
        )
        st.text_input(
            "Access key ID",
            key=ACCESS_KEY_ID_INPUT_KEY,
            help=(
                "Leave blank to fall back to ACCESS_KEYID from the "
                "environment."
            ),
        )
        st.text_input(
            "Access key password",
            key=ACCESS_KEY_PASSWORD_INPUT_KEY,
            type="password",
            help=(
                "Leave blank to fall back to ACCESS_PWD from the environment."
            ),
        )

    st.subheader("User authentication")
    st.text_input("LabArchives email", key=USER_EMAIL_INPUT_KEY)
    st.text_input(
        "Alternative auth code" if use_alternative_auth_code else "Auth code",
        key=AUTH_CODE_INPUT_KEY,
        type="password",
        help=(
            "Paste the one-hour code from LabArchives."
            if use_alternative_auth_code
            else (
                "Paste a one-hour auth code or use the generated "
                "sign-in link below."
            )
        ),
    )
    if redirect_url is not None:
        st.caption(f"Redirect URL: `{redirect_url}`")

    with st.expander("How to authenticate", expanded=False):
        if use_alternative_auth_code:
            st.markdown(
                f"""
                <ol>
                    <li>
                        Fill in any missing API settings above if the
                        environment is incomplete.
                    </li>
                    <li>
                        Get a one-hour alternative auth code from
                        LabArchives.
                    </li>
                    <li>
                        Enter your email and code, then click
                        <span class="button-ref button-ref-green">
                            {html.escape(auth_button_label)}
                        </span>.
                    </li>
                </ol>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <ol>
                    <li>
                        Click
                        <span class="button-ref button-ref-blue">
                            Open LabArchives sign-in
                        </span>
                        to authenticate in LabArchives and return here
                        automatically.
                    </li>
                    <li>
                        Or enter your email and one-hour code, then click
                        <span class="button-ref button-ref-green">
                            {html.escape(auth_button_label)}
                        </span>.
                    </li>
                </ol>
                """,
                unsafe_allow_html=True,
            )

    if auth_url:
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
    elif auth_url_message:
        if auth_url_message.startswith("Unable to generate"):
            st.error(auth_url_message)
        else:
            st.info(auth_url_message)

    if use_alternative_auth_code and not has_usable_client_config:
        st.caption(
            "The alternative auth code still needs API client credentials. "
            "Provide the missing values above first."
        )

    if st.button(
        auth_button_label,
        type="primary",
        use_container_width=True,
        disabled=not has_usable_client_config,
    ):
        user_email = st.session_state[USER_EMAIL_INPUT_KEY].strip()
        auth_code = st.session_state[AUTH_CODE_INPUT_KEY].strip()

        if not user_email or not auth_code:
            st.error(
                "Enter both the LabArchives email address and an "
                + (
                    "alternative auth code."
                    if use_alternative_auth_code
                    else "auth code."
                )
            )
            return

        try:
            with st.spinner("Signing in to LabArchives..."):
                complete_login(user_email, auth_code)
        except AuthenticationError as exc:
            st.error(f"Authentication failed: {exc}")
            return
        except ApiError as exc:
            st.error(f"LabArchives API error: {exc}")
            return

        callback_auth_code = st.query_params.get("auth_code")
        callback_email = st.query_params.get("email")
        if callback_auth_code == auth_code and callback_email == user_email:
            st.session_state[LAST_CALLBACK_KEY] = (
                f"{callback_email}:{callback_auth_code}"
            )
            st.query_params.clear()

        st.rerun()


def main() -> None:
    init_state()
    render_header()
    process_callback()

    user = st.session_state[USER_STATE_KEY]
    if user is not None:
        render_logged_in(user)
        return

    render_login_form()


if __name__ == "__main__":
    main()
