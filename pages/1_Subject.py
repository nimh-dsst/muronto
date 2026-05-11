from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st
from labapi import ApiError

from muronto_app.config import (
    LA_HOME_FOLDER_KEY,
    OPTIONS_KEY,
    OTHER_CHOICE,
    SOURCE_TYPE_OPTIONS_KEY,
    STRAIN_OPTIONS_KEY,
    choice_options,
    clean_string,
    normalize_options,
)
from muronto_app.labarchives import (
    create_subject_page_with_json,
    find_root_config_page,
    resolve_notebook_folder,
    save_config_attachment,
)
from muronto_app.page_helpers import render_project_context
from muronto_app.state import (
    CONFIG_ATTACHMENT_STATE_KEY,
    CONFIG_PAGE_ID_STATE_KEY,
    CONFIG_PAGE_STATE_KEY,
    CONFIG_STATE_KEY,
    SELECTED_NOTEBOOK_STATE_KEY,
)
from muronto_app.subject import (
    ANIMAL_ID_PATTERN_TEXT,
    CCN_PATTERN_TEXT,
    EAR_TAG_PATTERN_TEXT,
    GENOTYPE_OPTIONS,
    SEX_OPTIONS,
    SubjectValidationError,
    build_subject_payload,
    format_subject_date,
    subject_strains,
    with_subject_options,
)

st.set_page_config(page_title="Muronto Subject", layout="centered")

SUBJECT_PAIR_COUNT_KEY = "subject_strain_genotype_count"


def render_text_guidance(text: str) -> None:
    st.markdown(text)


def render_select_with_other(
    *,
    label: str,
    options: dict[str, list[str]],
    options_key: str,
    widget_key: str,
    other_prompt: str,
) -> str:
    choices = choice_options(options, options_key)
    selected = st.selectbox(label, options=choices, key=widget_key)
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            other_prompt,
            key=f"{widget_key}_other",
        )
    )


def render_subject_date(label: str, key: str) -> date | None:
    selected_date = st.date_input(
        label,
        value=None,
        key=key,
        format="YYYY/MM/DD",
    )
    if isinstance(selected_date, date):
        st.write(format_subject_date(selected_date))
        return selected_date
    return None


def increment_strain_genotype_count() -> None:
    st.session_state[SUBJECT_PAIR_COUNT_KEY] = (
        st.session_state.get(SUBJECT_PAIR_COUNT_KEY, 1) + 1
    )


def render_strain_genotypes(
    options: dict[str, list[str]],
) -> list[tuple[str, str]]:
    st.session_state.setdefault(SUBJECT_PAIR_COUNT_KEY, 1)

    strain_genotypes: list[tuple[str, str]] = []
    for index in range(1, st.session_state[SUBJECT_PAIR_COUNT_KEY] + 1):
        strain = render_select_with_other(
            label=f"strain_{index}",
            options=options,
            options_key=STRAIN_OPTIONS_KEY,
            widget_key=f"subject_strain_{index}",
            other_prompt=f"New strain_{index}",
        )
        genotype = st.selectbox(
            f"genotype_{index}",
            options=GENOTYPE_OPTIONS,
            key=f"subject_genotype_{index}",
        )
        strain_genotypes.append((strain, genotype))

    return strain_genotypes


def save_reusable_subject_options(
    *,
    notebook: Any,
    config: dict[str, Any],
    payload: dict[str, str],
) -> None:
    updated_config, changed = with_subject_options(
        config,
        strains=subject_strains(payload),
        source_type=payload[SOURCE_TYPE_OPTIONS_KEY],
    )
    if not changed:
        return

    config_page = st.session_state.get(CONFIG_PAGE_STATE_KEY)
    if config_page is None:
        config_page = find_root_config_page(notebook)

    if config_page is None:
        st.warning(
            "Created the subject page, but could not find muronto_config to "
            "save reusable subject options."
        )
        return

    attachment_entry = save_config_attachment(
        config_page,
        updated_config,
        existing_entry=st.session_state.get(CONFIG_ATTACHMENT_STATE_KEY),
    )
    st.session_state[CONFIG_STATE_KEY] = updated_config
    st.session_state[CONFIG_ATTACHMENT_STATE_KEY] = attachment_entry
    st.session_state[CONFIG_PAGE_STATE_KEY] = config_page
    st.session_state[CONFIG_PAGE_ID_STATE_KEY] = config_page.id


def render_subject_form(
    notebook: Any,
    config: dict[str, Any],
    project: dict[str, str],
) -> None:
    options = normalize_options(config.get(OPTIONS_KEY))

    if st.button(
        "Add strain/genotype",
        help="Add another strain and genotype entry box.",
        use_container_width=True,
    ):
        increment_strain_genotype_count()
        st.rerun()

    render_text_guidance(
        "animal_id must match the regex pattern "
        f"`{ANIMAL_ID_PATTERN_TEXT}`, for example `123-4567`."
    )
    animal_id = st.text_input("animal_id")

    render_text_guidance(
        "ear_tag must match the regex pattern "
        f"`{EAR_TAG_PATTERN_TEXT}`, for example `123`."
    )
    ear_tag = st.text_input("ear_tag")

    render_text_guidance(
        "ccn must match the regex pattern "
        f"`{CCN_PATTERN_TEXT}`, for example `123456`."
    )
    ccn = st.text_input("ccn")

    sex = st.selectbox("sex", options=SEX_OPTIONS, key="subject_sex")

    strain_genotypes = render_strain_genotypes(options)

    dob = render_subject_date("dob", "subject_dob")
    dow = render_subject_date("dow", "subject_dow")

    source_type = render_select_with_other(
        label="source_type",
        options=options,
        options_key=SOURCE_TYPE_OPTIONS_KEY,
        widget_key="subject_source_type",
        other_prompt="New source_type",
    )

    render_text_guidance(
        "parent_ccn must match the regex pattern "
        f"`{CCN_PATTERN_TEXT}`, for example `123456`."
    )
    parent_ccn = st.text_input("parent_ccn")

    submitted = st.button(
        "Create subject page",
        type="primary",
        use_container_width=True,
    )

    if not submitted:
        return

    try:
        payload = build_subject_payload(
            animal_id=animal_id,
            ear_tag=ear_tag,
            ccn=ccn,
            sex=sex,
            strain_genotypes=strain_genotypes,
            dob=dob,
            dow=dow,
            source_type=source_type,
            parent_ccn=parent_ccn,
        )
    except SubjectValidationError as exc:
        st.error("Complete the subject form before creating the page.")
        for error in exc.errors:
            st.caption(error)
        return

    try:
        home_folder = resolve_notebook_folder(
            notebook,
            project[LA_HOME_FOLDER_KEY],
        )
        result = create_subject_page_with_json(home_folder, payload)
    except ApiError as exc:
        st.error(f"Unable to create the subject page: {exc}")
        return
    except ValueError as exc:
        st.error(str(exc))
        return

    try:
        save_reusable_subject_options(
            notebook=notebook,
            config=config,
            payload=payload,
        )
    except ApiError as exc:
        st.warning(
            "Created the subject page, but could not save reusable subject "
            f"options to muronto_config: {exc}"
        )

    st.success(f"Created subject page `{result.page.name}`.")
    with st.expander("Subject JSON", expanded=True):
        st.json(payload)


def main() -> None:
    context = render_project_context("Subject")
    if context is None:
        return

    notebook = st.session_state.get(SELECTED_NOTEBOOK_STATE_KEY)
    _user, config, project = context
    if notebook is None or not isinstance(config, dict):
        st.warning("Select a notebook and complete muronto_config first.")
        st.page_link("Project.py", label="Open Project")
        return

    st.subheader("Subject")
    render_subject_form(notebook, config, project)


if __name__ == "__main__":
    main()
