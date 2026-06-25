from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date, datetime
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
    SubjectRecord,
    create_subject_page_with_json,
    discover_subject_records,
    find_root_config_page,
    resolve_notebook_folder,
    save_config_attachment,
    save_subject_attachment,
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
    ANIMAL_ID_LABEL,
    ANIMAL_ID_PATTERN,
    ANIMAL_ID_PATTERN_TEXT,
    CCN_KEY,
    CCN_LABEL,
    CCN_PATTERN,
    CCN_PATTERN_TEXT,
    DOB_KEY,
    DOB_LABEL,
    DOW_KEY,
    DOW_LABEL,
    EAR_TAG_KEY,
    EAR_TAG_LABEL,
    EAR_TAG_PATTERN,
    EAR_TAG_PATTERN_TEXT,
    GENOTYPE_KEY,
    GENOTYPE_LABEL,
    GENOTYPE_OPTIONS,
    PARENT_CCN_KEY,
    PARENT_CCN_LABEL,
    PARENT_REQUIRED_SOURCE_TYPE,
    SEX_KEY,
    SEX_LABEL,
    SEX_OPTIONS,
    SOURCE_TYPE_LABEL,
    STRAIN_LABEL,
    SUBJECT_VALIDATION_ERRORS_KEY,
    SubjectValidationError,
    build_subject_payload,
    format_subject_date,
    is_subject_incomplete,
    subject_strains,
    with_subject_options,
)

st.set_page_config(page_title="Muronto Subject", layout="centered")

SUBJECT_PAIR_COUNT_KEY = "subject_strain_genotype_count"
SUBJECT_EDIT_MODE_KEY = "subject_edit_existing"
SUBJECT_SELECTED_RECORD_KEY = "subject_edit_record"
SUBJECT_COPY_MODE_KEY = "subject_copy_existing"
SUBJECT_COPY_SOURCE_RECORD_KEY = "subject_copy_source_record"


def render_text_guidance(text: str) -> None:
    st.markdown(text)


def render_pattern_text_input(
    *,
    label: str,
    value: object = "",
    key: str,
    pattern: re.Pattern[str],
    pattern_text: str,
    example: str,
) -> str:
    entered_value = clean_string(
        st.text_input(label, value=clean_string(value), key=key)
    )
    if entered_value and not pattern.fullmatch(entered_value):
        st.error(
            f"{label} must match the regex pattern `{pattern_text}`, "
            f"for example `{example}`."
        )
    return entered_value


def selected_index(options: Sequence[str], value: str) -> int:
    cleaned_value = clean_string(value)
    if cleaned_value in options:
        return options.index(cleaned_value)
    return 0


def subject_label(record: SubjectRecord) -> str:
    animal_id = clean_string(record.payload.get(ANIMAL_ID_KEY)) or "Unknown"
    ear_tag = clean_string(record.payload.get(EAR_TAG_KEY))
    label = f"{animal_id} - Ear Tag {ear_tag}" if ear_tag else animal_id
    if is_subject_incomplete(record.payload):
        label = f"{label} (incomplete)"
    return label


def subject_record_widget_key(record: SubjectRecord) -> str:
    page_id = clean_string(getattr(record.page, "id", ""))
    if page_id:
        return page_id
    return clean_string(record.payload.get(ANIMAL_ID_KEY)) or "selected"


def parse_subject_date(value: object) -> date | None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        return None

    try:
        return datetime.strptime(cleaned_value, "%Y%m%d").date()
    except ValueError:
        return None


def subject_strain_genotypes(
    payload: dict[str, Any],
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


def render_select_with_other(
    *,
    label: str,
    options: dict[str, list[str]],
    options_key: str,
    widget_key: str,
    other_prompt: str,
    value: str = "",
) -> str:
    choices = choice_options(options, options_key)
    cleaned_value = clean_string(value)
    if cleaned_value in choices:
        index = choices.index(cleaned_value)
    elif cleaned_value:
        index = choices.index(OTHER_CHOICE)
    else:
        index = 0

    selected = st.selectbox(
        label,
        options=choices,
        key=widget_key,
        index=index,
    )
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            other_prompt,
            key=f"{widget_key}_other",
            value="" if cleaned_value in choices else cleaned_value,
        )
    )


def render_subject_date(
    label: str,
    key: str,
    value: date | None = None,
) -> date | None:
    selected_date = st.date_input(
        label,
        value=value,
        key=key,
        format="YYYY/MM/DD",
    )
    if isinstance(selected_date, date):
        st.write(format_subject_date(selected_date))
        return selected_date
    return None


def increment_strain_genotype_count(count_key: str) -> None:
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1


def render_strain_genotypes(
    options: dict[str, list[str]],
    *,
    form_key: str,
    values: Sequence[tuple[str, str]] = (),
) -> list[tuple[str, str]]:
    count_key = f"{form_key}_{SUBJECT_PAIR_COUNT_KEY}"
    st.session_state.setdefault(count_key, max(1, len(values)))

    strain_genotypes: list[tuple[str, str]] = []
    for index in range(1, st.session_state[count_key] + 1):
        strain_value = values[index - 1][0] if index <= len(values) else ""
        genotype_value = values[index - 1][1] if index <= len(values) else ""
        strain = render_select_with_other(
            label=f"{STRAIN_LABEL} {index}",
            options=options,
            options_key=STRAIN_OPTIONS_KEY,
            widget_key=f"{form_key}_strain_{index}",
            other_prompt=f"New {STRAIN_LABEL} {index}",
            value=strain_value,
        )
        genotype = st.selectbox(
            f"{GENOTYPE_LABEL} {index}",
            options=GENOTYPE_OPTIONS,
            key=f"{form_key}_genotype_{index}",
            index=selected_index(GENOTYPE_OPTIONS, genotype_value),
        )
        strain_genotypes.append((strain, genotype))

    return strain_genotypes


def render_parent_ccn(
    source_type: str,
    *,
    value: str = "",
    widget_key: str = PARENT_CCN_KEY,
) -> str:
    if clean_string(source_type) != PARENT_REQUIRED_SOURCE_TYPE:
        return ""

    render_text_guidance(
        f"{PARENT_CCN_LABEL} must match the regex pattern "
        f"`{CCN_PATTERN_TEXT}`, for example `123456`."
    )
    return render_pattern_text_input(
        label=PARENT_CCN_LABEL,
        value=value,
        key=widget_key,
        pattern=CCN_PATTERN,
        pattern_text=CCN_PATTERN_TEXT,
        example="123456",
    )


def save_reusable_subject_options(
    *,
    notebook: Any,
    config: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    updated_config, changed = with_subject_options(
        config,
        strains=subject_strains(payload),
        source_type=clean_string(payload.get(SOURCE_TYPE_OPTIONS_KEY)),
    )
    if not changed:
        return

    config_page = st.session_state.get(CONFIG_PAGE_STATE_KEY)
    if config_page is None:
        config_page = find_root_config_page(notebook)

    if config_page is None:
        st.warning(
            "Saved the subject page, but could not find muronto_config to "
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
    *,
    notebook: Any,
    config: dict[str, Any],
    home_folder: Any,
    existing_record: SubjectRecord | None = None,
    copied_payload: dict[str, Any] | None = None,
    copy_source_key: str = "",
) -> None:
    options = normalize_options(config.get(OPTIONS_KEY))
    payload_defaults = {}
    if existing_record is not None:
        payload_defaults = existing_record.payload
    elif copied_payload is not None:
        payload_defaults = copied_payload

    is_editing = existing_record is not None
    is_copying = copied_payload is not None and existing_record is None

    form_key = "subject_create"

    if existing_record is not None:
        form_key = f"subject_edit_{subject_record_widget_key(existing_record)}"

    elif copied_payload is not None:
        form_key = f"subject_copy_{copy_source_key or 'source'}"
    if is_copying:
        payload_defaults = dict(payload_defaults)
        payload_defaults[ANIMAL_ID_KEY] = ""
        payload_defaults[EAR_TAG_KEY] = ""
        payload_defaults[CCN_KEY] = ""
    count_key = f"{form_key}_{SUBJECT_PAIR_COUNT_KEY}"

    if st.button(
        "Add Strain/Genotype",
        help="Add another Strain and Genotype entry.",
        use_container_width=True,
        key=f"{form_key}_add_strain_genotype",
    ):
        increment_strain_genotype_count(count_key)
        st.rerun()

    render_text_guidance(
        f"{ANIMAL_ID_LABEL} must match the regex pattern "
        f"`{ANIMAL_ID_PATTERN_TEXT}`, for example `123-4567`."
    )
    animal_id = render_pattern_text_input(
        label=ANIMAL_ID_LABEL,
        value=payload_defaults.get(ANIMAL_ID_KEY, ""),
        key=f"{form_key}_animal_id",
        pattern=ANIMAL_ID_PATTERN,
        pattern_text=ANIMAL_ID_PATTERN_TEXT,
        example="123-4567",
    )

    render_text_guidance(
        f"{EAR_TAG_LABEL} must match the regex pattern "
        f"`{EAR_TAG_PATTERN_TEXT}`, for example `123`."
    )
    ear_tag = render_pattern_text_input(
        label=EAR_TAG_LABEL,
        value=payload_defaults.get(EAR_TAG_KEY, ""),
        key=f"{form_key}_ear_tag",
        pattern=EAR_TAG_PATTERN,
        pattern_text=EAR_TAG_PATTERN_TEXT,
        example="123",
    )

    render_text_guidance(
        f"{CCN_LABEL} must match the regex pattern "
        f"`{CCN_PATTERN_TEXT}`, for example `123456`."
    )
    ccn = render_pattern_text_input(
        label=CCN_LABEL,
        value=payload_defaults.get(CCN_KEY, ""),
        key=f"{form_key}_ccn",
        pattern=CCN_PATTERN,
        pattern_text=CCN_PATTERN_TEXT,
        example="123456",
    )

    sex = st.selectbox(
        SEX_LABEL,
        options=SEX_OPTIONS,
        key=f"{form_key}_sex",
        index=selected_index(SEX_OPTIONS, payload_defaults.get(SEX_KEY, "")),
    )

    strain_genotypes = render_strain_genotypes(
        options,
        form_key=form_key,
        values=subject_strain_genotypes(payload_defaults),
    )

    dob = render_subject_date(
        DOB_LABEL,
        f"{form_key}_dob",
        parse_subject_date(payload_defaults.get(DOB_KEY)),
    )
    dow = render_subject_date(
        DOW_LABEL,
        f"{form_key}_dow",
        parse_subject_date(payload_defaults.get(DOW_KEY)),
    )

    source_type = render_select_with_other(
        label=SOURCE_TYPE_LABEL,
        options=options,
        options_key=SOURCE_TYPE_OPTIONS_KEY,
        widget_key=f"{form_key}_source_type",
        other_prompt=f"New {SOURCE_TYPE_LABEL}",
        value=payload_defaults.get(SOURCE_TYPE_OPTIONS_KEY, ""),
    )

    parent_ccn = render_parent_ccn(
        source_type,
        value=payload_defaults.get(PARENT_CCN_KEY, ""),
        widget_key=f"{form_key}_parent_ccn",
    )
    if is_editing:
        submit_label = "Save subject edits"
    elif is_copying:
        submit_label = "Create copied subject page"
    else:
        submit_label = "Create subject page"
    submitted = st.button(
        submit_label,
        type="primary",
        use_container_width=True,
        key=f"{form_key}_submit",
    )

    if not submitted:
        return

    def build_payload(*, allow_incomplete: bool) -> dict[str, Any]:
        return build_subject_payload(
            animal_id=animal_id,
            ear_tag=ear_tag,
            ccn=ccn,
            sex=sex,
            strain_genotypes=strain_genotypes,
            dob=dob,
            dow=dow,
            source_type=source_type,
            parent_ccn=parent_ccn,
            allow_incomplete=allow_incomplete,
        )

    def build_payload_for_save() -> tuple[dict[str, Any], list[str]]:
        try:
            return build_payload(allow_incomplete=False), []
        except SubjectValidationError:
            incomplete_payload = build_payload(allow_incomplete=True)
            validation_errors = [
                error
                for error in incomplete_payload.get(
                    SUBJECT_VALIDATION_ERRORS_KEY,
                    [],
                )
                if isinstance(error, str) and error
            ]
            return incomplete_payload, validation_errors

    try:
        payload, validation_errors = build_payload_for_save()
    except SubjectValidationError as exc:
        st.error(
            f"Enter a valid {ANIMAL_ID_LABEL} before saving the subject page."
        )
        for error in exc.errors:
            st.caption(error)
        return

    try:
        if existing_record is None:
            result = create_subject_page_with_json(home_folder, payload)
        else:
            result = save_subject_attachment(existing_record.page, payload)
    except ApiError as exc:
        st.error(f"Unable to save the subject page: {exc}")
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
            "Saved the subject page, but could not save reusable subject "
            f"options to muronto_config: {exc}"
        )

    action = "Updated" if is_editing else "Created"
    if is_subject_incomplete(payload):
        st.warning(
            "Saved an incomplete subject record. Return to Edit existing "
            "subject to complete it."
        )
        for error in validation_errors:
            st.caption(error)
    st.success(f"{action} subject page `{result.page.name}`.")
    with st.expander("Subject JSON", expanded=True):
        st.json(payload)


def load_subject_records(home_folder: Any) -> list[SubjectRecord] | None:
    try:
        return discover_subject_records(home_folder)
    except ApiError as exc:
        st.error(f"Unable to load subjects from LabArchives: {exc}")
    return None


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
    edit_existing = st.toggle(
        "Edit existing subject",
        key=SUBJECT_EDIT_MODE_KEY,
    )

    copy_existing = st.toggle(
        "Copy values from existing subject",
        key=SUBJECT_COPY_MODE_KEY,
        disabled=edit_existing,
    )

    if edit_existing and copy_existing:
        copy_existing = False

    try:
        home_folder = resolve_notebook_folder(
            notebook,
            project[LA_HOME_FOLDER_KEY],
        )
    except ApiError as exc:
        st.error(f"Unable to open the LabArchives home folder: {exc}")
        return
    except ValueError as exc:
        st.error(str(exc))
        return

    if not edit_existing and not copy_existing:
        render_subject_form(
            notebook=notebook,
            config=config,
            home_folder=home_folder,
        )
        return

    subject_records = load_subject_records(home_folder)
    if subject_records is None:
        return
    if not subject_records:
        st.info("No subject JSON records were found in the project folder.")
        return

    # -------------------------
    # Copy mode
    # -------------------------
    if copy_existing:
        selected_copy_index = st.selectbox(
            "Copy values from subject",
            options=list(range(len(subject_records))),
            format_func=lambda index: subject_label(subject_records[index]),
            key=SUBJECT_COPY_SOURCE_RECORD_KEY,
        )

        st.info(
            "Copied values will pre-fill the form, but a new subject page will be created."
        )

        copy_source_record = subject_records[selected_copy_index]

        render_subject_form(
            notebook=notebook,
            config=config,
            home_folder=home_folder,
            copied_payload=copy_source_record.payload,
            copy_source_key=subject_record_widget_key(copy_source_record),
        )
        return

    # -------------------------
    # Edit mode
    # -------------------------
    selected_subject_index = st.selectbox(
        "Subject",
        options=list(range(len(subject_records))),
        format_func=lambda index: subject_label(subject_records[index]),
        key=SUBJECT_SELECTED_RECORD_KEY,
    )

    render_subject_form(
        notebook=notebook,
        config=config,
        home_folder=home_folder,
        existing_record=subject_records[selected_subject_index],
    )


if __name__ == "__main__":
    main()
