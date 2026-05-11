from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st
from labapi import ApiError

from muronto_app.config import (
    LA_HOME_FOLDER_KEY,
    OPTIONS_KEY,
    OTHER_CHOICE,
    PROJECT_ID_KEY,
    SURGEON_OPTIONS_KEY,
    choice_options,
    clean_string,
    investigator_for_user,
    normalize_options,
)
from muronto_app.labarchives import (
    SubjectRecord,
    discover_subject_records,
    find_root_config_page,
    resolve_notebook_folder,
    save_config_attachment,
    save_surgery_attachment,
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
    ANIMAL_ID_KEY,
    DOB_KEY,
    EAR_TAG_KEY,
    GENOTYPE_KEY,
    SEX_KEY,
    STRAIN_OPTIONS_KEY,
)
from muronto_app.surgery import (
    CNN_PATTERN_TEXT,
    SurgeryValidationError,
    build_surgery_payload,
    format_surgery_date,
    with_surgeon_options,
)

st.set_page_config(page_title="Muronto Surgery", layout="centered")


def render_text_guidance(text: str) -> None:
    st.markdown(text)


def render_surgeon_select(options: dict[str, list[str]]) -> str:
    choices = choice_options(options, SURGEON_OPTIONS_KEY)
    selected = st.selectbox("Surgeon", options=choices, key="surgery_surgeon")
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            "New Surgeon",
            key="surgery_surgeon_other",
        )
    )


def render_surgery_date() -> date | None:
    selected_date = st.date_input(
        "Surgery Date",
        value=None,
        key="surgery_date",
        format="YYYY/MM/DD",
    )
    if isinstance(selected_date, date):
        st.write(format_surgery_date(selected_date))
        return selected_date
    return None


def subject_label(record: SubjectRecord) -> str:
    animal_id = record.payload.get(ANIMAL_ID_KEY, "Unknown")
    ear_tag = record.payload.get(EAR_TAG_KEY, "")
    return f"{animal_id} - Ear Tag {ear_tag}" if ear_tag else animal_id


def subject_strain_genotypes(
    payload: dict[str, str],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    index = 1
    while (
        f"{STRAIN_OPTIONS_KEY}_{index}" in payload
        or f"{GENOTYPE_KEY}_{index}" in payload
    ):
        strain = clean_string(payload.get(f"{STRAIN_OPTIONS_KEY}_{index}"))
        genotype = clean_string(payload.get(f"{GENOTYPE_KEY}_{index}"))
        if strain or genotype:
            pairs.append((strain, genotype))
        index += 1
    return pairs


def render_selected_subject(record: SubjectRecord) -> None:
    payload = record.payload
    st.write(f"Animal ID: {payload.get(ANIMAL_ID_KEY, '')}")
    st.write(f"Ear Tag: {payload.get(EAR_TAG_KEY, '')}")
    st.write(f"Sex: {payload.get(SEX_KEY, '')}")
    st.write(f"DOB: {payload.get(DOB_KEY, '')}")

    pairs = subject_strain_genotypes(payload)
    if not pairs:
        st.write("Strain/genotype: Not recorded")
        return

    for index, (strain, genotype) in enumerate(pairs, start=1):
        st.write(f"strain_{index}: {strain}")
        st.write(f"genotype_{index}: {genotype}")


def save_reusable_surgeon_options(
    *,
    notebook: Any,
    config: dict[str, Any],
    surgeon: str,
) -> None:
    updated_config, changed = with_surgeon_options(config, surgeon=surgeon)
    if not changed:
        return

    config_page = st.session_state.get(CONFIG_PAGE_STATE_KEY)
    if config_page is None:
        config_page = find_root_config_page(notebook)

    if config_page is None:
        st.warning(
            "Saved the surgery record, but could not find muronto_config to "
            "save the reusable surgeon option."
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


def load_subject_records(
    notebook: Any,
    project: dict[str, str],
) -> list[SubjectRecord] | None:
    try:
        home_folder = resolve_notebook_folder(
            notebook,
            project[LA_HOME_FOLDER_KEY],
        )
        return discover_subject_records(home_folder)
    except ApiError as exc:
        st.error(f"Unable to load subjects from LabArchives: {exc}")
    except ValueError as exc:
        st.error(str(exc))
    return None


def render_surgery_form(
    *,
    notebook: Any,
    config: dict[str, Any],
    project: dict[str, str],
    investigator: str,
    selected_subject: SubjectRecord,
) -> None:
    subject_payload = selected_subject.payload
    options = normalize_options(config.get(OPTIONS_KEY))

    surgeon = render_surgeon_select(options)
    surgery_date = render_surgery_date()

    render_text_guidance(
        "PreOp CNN must match the regex pattern "
        f"`{CNN_PATTERN_TEXT}`, for example `123456`."
    )
    preop_cnn = st.text_input("PreOp CNN", key="surgery_preop_cnn")

    render_text_guidance(
        "PostOp CNN must match the regex pattern "
        f"`{CNN_PATTERN_TEXT}`, for example `123456`."
    )
    postop_cnn = st.text_input("PostOp CNN", key="surgery_postop_cnn")

    submitted = st.button(
        "Save surgery record",
        type="primary",
        use_container_width=True,
    )
    if not submitted:
        return

    try:
        payload = build_surgery_payload(
            project_id=project[PROJECT_ID_KEY],
            investigator=investigator,
            animal_id=subject_payload.get(ANIMAL_ID_KEY, ""),
            ear_tag=subject_payload.get(EAR_TAG_KEY, ""),
            surgeon=surgeon,
            surgery_date=surgery_date,
            preop_cnn=preop_cnn,
            postop_cnn=postop_cnn,
        )
    except SurgeryValidationError as exc:
        st.error("Complete the surgery form before saving the record.")
        for error in exc.errors:
            st.caption(error)
        return

    try:
        result = save_surgery_attachment(selected_subject.page, payload)
    except ApiError as exc:
        st.error(f"Unable to save the surgery record: {exc}")
        return
    except ValueError as exc:
        st.error(str(exc))
        return

    try:
        save_reusable_surgeon_options(
            notebook=notebook,
            config=config,
            surgeon=payload["surgeon"],
        )
    except ApiError as exc:
        st.warning(
            "Saved the surgery record, but could not save the reusable "
            f"surgeon option to muronto_config: {exc}"
        )

    action = "Created" if result.created else "Updated"
    st.success(f"{action} surgery record for `{payload[ANIMAL_ID_KEY]}`.")
    with st.expander("Surgery JSON", expanded=True):
        st.json(payload)


def main() -> None:
    context = render_project_context("Surgery")
    if context is None:
        return

    notebook = st.session_state.get(SELECTED_NOTEBOOK_STATE_KEY)
    _user, config, project = context
    if notebook is None or not isinstance(config, dict):
        st.warning("Select a notebook and complete muronto_config first.")
        st.page_link("Project.py", label="Open Project")
        return

    investigator = investigator_for_user(config, _user.email)

    st.subheader("Surgery")
    st.write(f"Project ID: {project[PROJECT_ID_KEY]}")
    st.write(f"Investigator: {investigator}")

    st.subheader("Subject Information")
    subject_records = load_subject_records(notebook, project)
    if subject_records is None:
        return
    if not subject_records:
        st.info("No subject JSON records were found in the project folder.")
        return

    selected_subject_index = st.selectbox(
        "Subject",
        options=list(range(len(subject_records))),
        format_func=lambda index: subject_label(subject_records[index]),
        key="surgery_subject",
    )
    selected_subject = subject_records[selected_subject_index]
    render_selected_subject(selected_subject)

    st.subheader("Surgery Details")
    render_surgery_form(
        notebook=notebook,
        config=config,
        project=project,
        investigator=investigator,
        selected_subject=selected_subject,
    )


if __name__ == "__main__":
    main()
