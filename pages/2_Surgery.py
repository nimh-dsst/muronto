from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time
from typing import Any, TypedDict

import streamlit as st
from labapi import ApiError

from muronto_app.config import (
    COVERSLIP_DIAMETER_OPTIONS_KEY,
    COVERSLIP_THICKNESS_OPTIONS_KEY,
    COVERSLIP_TYPE_OPTIONS_KEY,
    CRANIAL_WINDOW_REGION_OPTIONS_KEY,
    CRYSTAL_SKULL_WELL_TYPE_OPTIONS_KEY,
    CS_TYPE_OPTIONS_KEY,
    ELECTRODE_SITE_OPTIONS_KEY,
    HEADPLATE_TYPE_OPTIONS_KEY,
    LA_HOME_FOLDER_KEY,
    MEDICATION_OPTIONS_KEY,
    OPTIONS_KEY,
    OTHER_CHOICE,
    PROBE_MODEL_OPTIONS_KEY,
    PROJECT_ID_KEY,
    SITE_OPTIONS_KEY,
    SURGEON_OPTIONS_KEY,
    VIRUS_OPTIONS_KEY,
    VIRUS_SOURCE_OPTIONS_KEY,
    choice_options,
    clean_string,
    investigator_for_user,
    normalize_options,
)
from muronto_app.labarchives import (
    SubjectRecord,
    SurgeryRecord,
    discover_subject_records,
    discover_surgery_records,
    find_root_config_page,
    resolve_notebook_folder,
    save_config_attachment,
    save_surgery_attachment,
    save_surgery_file_attachment,
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
    AP_KEY,
    ATTACHMENTS_KEY,
    BREGMA_LAMBDA_DIST_MM_KEY,
    CENTER_AP_KEY,
    CENTER_ML_KEY,
    CNN_PATTERN_TEXT,
    CONC_MGML_KEY,
    COVERSLIP_DIAMETER_KEY,
    COVERSLIP_THICKNESS_KEY,
    COVERSLIP_TYPE_KEY,
    CRANIAL_WINDOW_IMPLANT_TYPE,
    CRANIAL_WINDOW_KEY,
    CRYSTAL_SKULL_IMPLANT_TYPE,
    CRYSTAL_SKULL_KEY,
    CS_TYPE_KEY,
    DILUTION_KEY,
    DV_KEY,
    ELECTRODE_HEMISPHERE_KEY,
    ELECTRODE_IMPLANT_TYPE,
    ELECTRODE_SITE_KEY,
    ELECTRODE_TYPE_KEY,
    ELECTRODE_TYPE_OPTIONS,
    ELECTRODES_KEY,
    END_TIME_KEY,
    FRONT_AP_KEY,
    GENERAL_NOTES_KEY,
    GROUND_KEY,
    HEADPLATE_TYPE_KEY,
    HEMISPHERE_KEY,
    HEMISPHERE_OPTIONS,
    IMPLANT_CATEGORY,
    IMPLANT_TYPE_KEY,
    IMPLANT_TYPE_OPTIONS,
    INFUSION_RATE_NLMIN_KEY,
    INFUSION_VOLUME_NL_KEY,
    INFUSIONS_KEY,
    INJECTIONS_KEY,
    LEFT_ML_KEY,
    MEDICATION_KEY,
    MEDICATIONS_KEY,
    ML_KEY,
    NOTE_UPLOAD_TYPE,
    NOTES_KEY,
    PHOTO_UPLOAD_TYPE,
    PITCH_KEY,
    POST_INFUSION_FLOW_TEST_KEY,
    POST_INFUSION_FLOW_TEST_OPTIONS,
    POSTOP_CNN_KEY,
    PREOP_CNN_KEY,
    PROBE_ID_KEY,
    PROBE_MODEL_KEY,
    REFERENCE_KEY,
    REGION_KEY,
    ROLL_KEY,
    SITE_KEY,
    START_TIME_KEY,
    STOCK_TITER_KEY,
    STOCK_TITER_PATTERN_TEXT,
    SURGEON_KEY,
    SURGERY_CATEGORY_KEY,
    SURGERY_CATEGORY_OPTIONS,
    SURGERY_DATE_KEY,
    SURGERY_TIME_PATTERN,
    SURGICAL_PROCEDURES_KEY,
    TAKEN_PHOTO_UPLOAD_TYPE,
    VIRAL_INJECTION_CATEGORY,
    VIRUS_ID_KEY,
    VIRUS_KEY,
    VIRUS_SOURCE_KEY,
    VIRUS_STOCK_KEY,
    VIRUSES_KEY,
    VOLUME_KEY,
    WEIGHT_POST_G_KEY,
    WEIGHT_PRE_G_KEY,
    WELL_TYPE_KEY,
    WELL_TYPE_OPTIONS,
    YAW_KEY,
    SurgeryValidationError,
    build_surgery_payload,
    format_surgery_date,
    format_surgery_time,
    format_surgery_time_display,
    medication_names,
    procedure_option_values,
    with_surgery_options,
)

st.set_page_config(page_title="Muronto Surgery", layout="centered")

SURGERY_MEDICATION_COUNT_KEY = "surgery_medication_count"
SURGERY_PROCEDURE_COUNT_KEY = "surgery_procedure_count"
SURGERY_TAKEN_PHOTO_COUNT_KEY = "surgery_taken_photo_count"
SURGERY_TAKEN_PHOTO_SLOT_IDS_KEY = "surgery_taken_photo_slot_ids"
SURGERY_TAKEN_PHOTO_NEXT_SLOT_ID_KEY = "surgery_taken_photo_next_slot_id"
SURGERY_EDIT_MODE_KEY = "surgery_edit_existing"
SURGERY_SELECTED_RECORD_KEY = "surgery_edit_record"
SURGERY_CREATE_FORM_KEY = "surgery"

ATTACHMENT_ACTION_PRESERVE = "Preserve existing"
ATTACHMENT_ACTION_REPLACE = "Replace with new uploads"
ATTACHMENT_ACTION_REMOVE = "Remove existing"
ATTACHMENT_ACTION_OPTIONS = (
    ATTACHMENT_ACTION_PRESERVE,
    ATTACHMENT_ACTION_REPLACE,
    ATTACHMENT_ACTION_REMOVE,
)


class PerioperativeValues(TypedDict):
    weight_pre_g: int | float | None
    weight_post_g: int | float | None
    medications: list[dict[str, object]]
    start_time: time | None
    end_time: time | None
    bregma_lambda_dist_mm: int | float | None


class SurgicalOptionValues(TypedDict):
    sites: list[str]
    viruses: list[str]
    virus_sources: list[str]


class GeneralNotesAttachmentValues(TypedDict):
    general_notes: str
    note_uploads: list[Any]
    photo_uploads: list[Any]
    taken_photos: list[Any]


def render_text_guidance(text: str) -> None:
    st.markdown(text)


def surgery_key(form_key: str, suffix: str) -> str:
    return f"{form_key}_{suffix}"


def surgery_count_key(form_key: str, base_key: str) -> str:
    if form_key == SURGERY_CREATE_FORM_KEY:
        return base_key
    return surgery_key(form_key, base_key)


def selected_index(options: Sequence[str], value: object) -> int:
    cleaned_value = clean_string(value)
    if cleaned_value in options:
        return options.index(cleaned_value)
    return 0


def string_default(payload: Mapping[str, Any], key: str) -> str:
    return clean_string(payload.get(key))


def number_default(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def mapping_default(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def mapping_list_default(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def parse_surgery_date(value: object) -> date | None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        return None

    try:
        return datetime.strptime(cleaned_value, "%Y%m%d").date()
    except ValueError:
        return None


def parse_surgery_time(value: object) -> time | None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        return None

    if not SURGERY_TIME_PATTERN.fullmatch(cleaned_value):
        return None

    try:
        return datetime.strptime(cleaned_value, "%H%M").time()
    except ValueError:
        return None


def surgery_record_widget_key(record: SurgeryRecord) -> str:
    entry_id = clean_string(getattr(record.attachment_entry, "id", ""))
    if entry_id:
        return stable_key_part(entry_id)
    surgery_date = clean_string(record.payload.get(SURGERY_DATE_KEY))
    return stable_key_part(surgery_date or "selected")


def surgery_record_label(record: SurgeryRecord) -> str:
    payload = record.payload
    surgery_date = clean_string(payload.get(SURGERY_DATE_KEY)) or "Unknown"
    surgeon = clean_string(payload.get(SURGEON_KEY))
    if surgeon:
        return f"{surgery_date} - {surgeon}"
    return surgery_date


def stable_key_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return cleaned[:48] or "value"


def sanitize_upload_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", clean_string(filename))
    cleaned = cleaned.strip("._-")
    return cleaned or "upload"


def surgery_upload_filename(
    *,
    animal_id: str,
    surgery_date: str,
    upload_type: str,
    index: int,
    original_filename: str,
) -> str:
    sanitized_original = sanitize_upload_filename(original_filename)
    return (
        f"{animal_id}_surgery_{surgery_date}_{upload_type}_{index}_"
        f"{sanitized_original}"
    )


def taken_photo_widget_key(
    form_key: str | int,
    slot_id: int | None = None,
) -> str:
    if slot_id is None:
        slot_id = int(form_key)
        form_key = SURGERY_CREATE_FORM_KEY
    return surgery_key(str(form_key), f"take_photo_{slot_id}")


def current_taken_photo_slot_ids(
    session_state: Any,
    form_key: str = SURGERY_CREATE_FORM_KEY,
) -> list[int]:
    slot_ids_key = surgery_count_key(
        form_key,
        SURGERY_TAKEN_PHOTO_SLOT_IDS_KEY,
    )
    next_slot_id_key = surgery_count_key(
        form_key,
        SURGERY_TAKEN_PHOTO_NEXT_SLOT_ID_KEY,
    )
    count_key = surgery_count_key(form_key, SURGERY_TAKEN_PHOTO_COUNT_KEY)
    raw_slot_ids = session_state.get(slot_ids_key)
    if isinstance(raw_slot_ids, list):
        slot_ids: list[int] = []
        for raw_slot_id in raw_slot_ids:
            if (
                isinstance(raw_slot_id, int)
                and raw_slot_id > 0
                and raw_slot_id not in slot_ids
            ):
                slot_ids.append(raw_slot_id)
    else:
        slot_ids = []

    max_slot_id = max(slot_ids, default=0)
    raw_next_slot_id = session_state.get(
        next_slot_id_key,
    )
    next_slot_id = (
        raw_next_slot_id
        if isinstance(raw_next_slot_id, int) and raw_next_slot_id > max_slot_id
        else max_slot_id + 1
    )

    session_state[slot_ids_key] = slot_ids
    session_state[next_slot_id_key] = next_slot_id
    session_state[count_key] = len(slot_ids)
    return slot_ids


def add_taken_photo_slot(
    session_state: Any,
    form_key: str = SURGERY_CREATE_FORM_KEY,
) -> None:
    slot_ids = current_taken_photo_slot_ids(session_state, form_key)
    slot_ids_key = surgery_count_key(
        form_key,
        SURGERY_TAKEN_PHOTO_SLOT_IDS_KEY,
    )
    next_slot_id_key = surgery_count_key(
        form_key,
        SURGERY_TAKEN_PHOTO_NEXT_SLOT_ID_KEY,
    )
    count_key = surgery_count_key(form_key, SURGERY_TAKEN_PHOTO_COUNT_KEY)
    raw_next_slot_id = session_state.get(
        next_slot_id_key,
    )
    next_slot_id = (
        raw_next_slot_id
        if isinstance(raw_next_slot_id, int) and raw_next_slot_id > 0
        else max(slot_ids, default=0) + 1
    )
    if next_slot_id in slot_ids:
        next_slot_id = max(slot_ids, default=0) + 1

    updated_slot_ids = [*slot_ids, next_slot_id]
    session_state[slot_ids_key] = updated_slot_ids
    session_state[next_slot_id_key] = next_slot_id + 1
    session_state[count_key] = len(updated_slot_ids)


def remove_taken_photo_slot(
    session_state: Any,
    slot_id: int,
    *,
    form_key: str = SURGERY_CREATE_FORM_KEY,
) -> None:
    slot_ids = current_taken_photo_slot_ids(session_state, form_key)
    updated_slot_ids = [
        current_slot_id
        for current_slot_id in slot_ids
        if current_slot_id != slot_id
    ]
    session_state[
        surgery_count_key(form_key, SURGERY_TAKEN_PHOTO_SLOT_IDS_KEY)
    ] = updated_slot_ids
    session_state[
        surgery_count_key(form_key, SURGERY_TAKEN_PHOTO_COUNT_KEY)
    ] = len(updated_slot_ids)
    session_state.pop(taken_photo_widget_key(form_key, slot_id), None)


def scoped_choice_options(
    options: dict[str, list[str]],
    options_key: str,
    default_values: tuple[str, ...],
    excluded_default_values: tuple[str, ...] = (),
) -> list[str]:
    values: list[str] = []
    excluded = set(excluded_default_values)
    for raw_value in (*default_values, *options.get(options_key, [])):
        value = clean_string(raw_value)
        if not value or value in values:
            continue
        if value in excluded and value not in default_values:
            continue
        values.append(value)
    return [*values, OTHER_CHOICE]


def render_surgeon_select(
    options: dict[str, list[str]],
    *,
    form_key: str,
    value: str = "",
) -> str:
    choices = choice_options(options, SURGEON_OPTIONS_KEY)
    cleaned_value = clean_string(value)
    index = (
        choices.index(cleaned_value)
        if cleaned_value in choices
        else choices.index(OTHER_CHOICE)
        if cleaned_value
        else 0
    )
    selected = st.selectbox(
        "Surgeon",
        options=choices,
        index=index,
        key=surgery_key(form_key, "surgeon"),
    )
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            "New Surgeon",
            key=surgery_key(form_key, "surgeon_other"),
            value="" if cleaned_value in choices else cleaned_value,
        )
    )


def render_medication_select(
    options: dict[str, list[str]],
    index: int,
    *,
    form_key: str,
    value: str = "",
) -> str:
    choices = choice_options(options, MEDICATION_OPTIONS_KEY)
    cleaned_value = clean_string(value)
    selected_index = (
        choices.index(cleaned_value)
        if cleaned_value in choices
        else choices.index(OTHER_CHOICE)
        if cleaned_value
        else 0
    )
    selected = st.selectbox(
        f"Medication {index}",
        options=choices,
        index=selected_index,
        key=surgery_key(form_key, f"medication_{index}"),
    )
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            f"New Medication {index}",
            key=surgery_key(form_key, f"medication_{index}_other"),
            value="" if cleaned_value in choices else cleaned_value,
        )
    )


def render_surgery_date(
    *,
    form_key: str,
    value: date | None = None,
) -> date | None:
    selected_date = st.date_input(
        "Surgery Date",
        value=value,
        key=surgery_key(form_key, "date"),
        format="YYYY/MM/DD",
    )
    if isinstance(selected_date, date):
        st.write(format_surgery_date(selected_date))
        return selected_date
    return None


def render_surgery_time(
    label: str,
    key: str,
    *,
    value: time | None = None,
) -> time | None:
    default_value = (
        format_surgery_time(value) if isinstance(value, time) else ""
    )
    entered_time = clean_string(
        st.text_input(
            label,
            value=default_value,
            key=key,
            max_chars=4,
            placeholder="0900",
            help=(
                "Enter 24-hour time as HHMM, for example 0900. "
                "Leading zeroes are required."
            ),
        )
    )
    if not entered_time:
        return None

    if not SURGERY_TIME_PATTERN.fullmatch(entered_time):
        st.error("Please enter a valid time (HHMM), for example 0900.")
        return None

    selected_time = parse_surgery_time(entered_time)
    if selected_time is None:
        st.error(f"{label} must be a valid 24-hour time.")
        return None

    st.write(format_surgery_time_display(selected_time))
    return selected_time


def add_reusable_surgery_option(
    *,
    notebook: Any,
    config: dict[str, Any],
    option_key: str,
    value: str,
) -> None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        st.warning("Enter a value before adding it.")
        return

    updated_config, changed = with_surgery_options(
        config,
        surgeon="",
        sites=[cleaned_value] if option_key == SITE_OPTIONS_KEY else [],
        viruses=[cleaned_value] if option_key == VIRUS_OPTIONS_KEY else [],
        virus_sources=(
            [cleaned_value] if option_key == VIRUS_SOURCE_OPTIONS_KEY else []
        ),
        headplate_types=(
            [cleaned_value] if option_key == HEADPLATE_TYPE_OPTIONS_KEY else []
        ),
        coverslip_types=(
            [cleaned_value] if option_key == COVERSLIP_TYPE_OPTIONS_KEY else []
        ),
        coverslip_diameters=(
            [cleaned_value]
            if option_key == COVERSLIP_DIAMETER_OPTIONS_KEY
            else []
        ),
        coverslip_thicknesses=(
            [cleaned_value]
            if option_key == COVERSLIP_THICKNESS_OPTIONS_KEY
            else []
        ),
        cranial_window_regions=(
            [cleaned_value]
            if option_key == CRANIAL_WINDOW_REGION_OPTIONS_KEY
            else []
        ),
        cs_types=(
            [cleaned_value] if option_key == CS_TYPE_OPTIONS_KEY else []
        ),
        crystal_skull_well_types=(
            [cleaned_value]
            if option_key == CRYSTAL_SKULL_WELL_TYPE_OPTIONS_KEY
            else []
        ),
        probe_models=(
            [cleaned_value] if option_key == PROBE_MODEL_OPTIONS_KEY else []
        ),
        electrode_sites=(
            [cleaned_value] if option_key == ELECTRODE_SITE_OPTIONS_KEY else []
        ),
    )
    if not changed:
        return

    config_page = st.session_state.get(CONFIG_PAGE_STATE_KEY)
    if config_page is None:
        config_page = find_root_config_page(notebook)

    if config_page is None:
        st.warning(
            "Could not find muronto_config to save the reusable option."
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


def add_option_and_select(
    *,
    notebook: Any,
    config: dict[str, Any],
    option_key: str,
    value: str,
    select_key: str,
    default_key: str,
) -> None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        st.warning("Enter a value before adding it.")
        return

    add_reusable_surgery_option(
        notebook=notebook,
        config=config,
        option_key=option_key,
        value=cleaned_value,
    )
    st.session_state.pop(select_key, None)
    st.session_state[default_key] = cleaned_value
    st.rerun()


def render_select_with_immediate_other(
    *,
    label: str,
    options: dict[str, list[str]],
    options_key: str,
    widget_key: str,
    other_prompt: str,
    notebook: Any,
    config: dict[str, Any],
    choices: list[str] | None = None,
    value: str = "",
) -> str:
    option_choices = choices or choice_options(options, options_key)
    default_key = f"{widget_key}_default"
    default_value = clean_string(
        st.session_state.pop(default_key, "")
    ) or clean_string(value)
    index = (
        option_choices.index(default_value)
        if default_value in option_choices
        else option_choices.index(OTHER_CHOICE)
        if default_value
        else 0
    )
    selected = st.selectbox(
        label,
        options=option_choices,
        index=index,
        key=widget_key,
    )
    if selected != OTHER_CHOICE:
        return selected

    new_value = st.text_input(
        other_prompt,
        key=f"{widget_key}_other",
        value="" if default_value in option_choices else default_value,
    )
    if st.button(
        f"Add {label}",
        key=f"{widget_key}_add",
        use_container_width=True,
    ):
        add_option_and_select(
            notebook=notebook,
            config=config,
            option_key=options_key,
            value=new_value,
            select_key=widget_key,
            default_key=default_key,
        )
    return clean_string(new_value)


def render_virus_multiselect(
    *,
    options: dict[str, list[str]],
    widget_key: str,
    notebook: Any,
    config: dict[str, Any],
    values: Sequence[str] = (),
) -> list[str]:
    choices = choice_options(options, VIRUS_OPTIONS_KEY)
    default_key = f"{widget_key}_default"
    default_values = st.session_state.pop(default_key, None)
    configured_values = (
        default_values
        if isinstance(default_values, list)
        else [value for value in values if clean_string(value) in choices]
    )
    selected = st.multiselect(
        "Viruses",
        options=choices,
        default=configured_values,
        key=widget_key,
    )
    selected_viruses = [
        clean_string(virus)
        for virus in selected
        if virus != OTHER_CHOICE and clean_string(virus)
    ]

    if OTHER_CHOICE not in selected:
        return selected_viruses

    new_virus = st.text_input(
        "New Virus",
        key=f"{widget_key}_other",
    )
    if st.button(
        "Add Virus",
        key=f"{widget_key}_add",
        use_container_width=True,
    ):
        cleaned_virus = clean_string(new_virus)
        if not cleaned_virus:
            st.warning("Enter a virus before adding it.")
            return selected_viruses

        add_reusable_surgery_option(
            notebook=notebook,
            config=config,
            option_key=VIRUS_OPTIONS_KEY,
            value=cleaned_virus,
        )
        st.session_state.pop(widget_key, None)
        st.session_state[default_key] = [*selected_viruses, cleaned_virus]
        st.rerun()

    return selected_viruses


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


def increment_medication_count(form_key: str) -> None:
    count_key = surgery_count_key(form_key, SURGERY_MEDICATION_COUNT_KEY)
    st.session_state[count_key] = st.session_state.get(count_key, 0) + 1


def render_medications(
    options: dict[str, list[str]],
    *,
    form_key: str,
    values: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, object]]:
    count_key = surgery_count_key(form_key, SURGERY_MEDICATION_COUNT_KEY)
    st.session_state.setdefault(count_key, len(values))

    medications: list[dict[str, object]] = []
    for index in range(1, st.session_state[count_key] + 1):
        medication_defaults = values[index - 1] if index <= len(values) else {}
        medication = render_medication_select(
            options,
            index,
            form_key=form_key,
            value=clean_string(medication_defaults.get(MEDICATION_KEY)),
        )
        conc_mgml = st.number_input(
            "Concentration (mg/ml)",
            min_value=0.0,
            value=number_default(medication_defaults.get(CONC_MGML_KEY)),
            step=0.1,
            key=surgery_key(form_key, f"medication_{index}_conc_mgml"),
        )
        volume = st.number_input(
            "Volume (ml)",
            min_value=0.0,
            value=number_default(medication_defaults.get(VOLUME_KEY)),
            step=0.01,
            key=surgery_key(form_key, f"medication_{index}_volume"),
        )
        medications.append(
            {
                MEDICATION_KEY: medication,
                CONC_MGML_KEY: conc_mgml,
                VOLUME_KEY: volume,
            }
        )

    return medications


def render_perioperative_monitoring(
    options: dict[str, list[str]],
    *,
    form_key: str,
    defaults: Mapping[str, Any] | None = None,
) -> PerioperativeValues:
    defaults = defaults or {}
    with st.expander(
        "Perioperative Monitoring & Medications",
        expanded=True,
    ):
        weight_pre_g = st.number_input(
            "Weight Pre (grams)",
            min_value=0.0,
            value=number_default(defaults.get(WEIGHT_PRE_G_KEY)),
            step=0.1,
            key=surgery_key(form_key, "weight_pre_g"),
        )
        weight_post_g = st.number_input(
            "Weight Post (grams)",
            min_value=0.0,
            value=number_default(defaults.get(WEIGHT_POST_G_KEY)),
            step=0.1,
            key=surgery_key(form_key, "weight_post_g"),
        )

        start_time = render_surgery_time(
            "Start Time",
            surgery_key(form_key, "start_time"),
            value=parse_surgery_time(defaults.get(START_TIME_KEY)),
        )
        end_time = render_surgery_time(
            "End Time",
            surgery_key(form_key, "end_time"),
            value=parse_surgery_time(defaults.get(END_TIME_KEY)),
        )
        bregma_lambda_dist_mm = st.number_input(
            "Bregma Lambda Distance (mm)",
            min_value=0.0,
            value=number_default(defaults.get(BREGMA_LAMBDA_DIST_MM_KEY)),
            step=0.1,
            placeholder="Optional",
            key=surgery_key(form_key, "bregma_lambda_dist_mm"),
        )

        st.markdown("#### Medications")
        st.caption(
            "Press Add medication only if medications were given to the "
            "subject."
        )
        if st.button(
            "Add medication",
            help="Add another medication entry.",
            use_container_width=True,
            key=surgery_key(form_key, "add_medication"),
        ):
            increment_medication_count(form_key)
            st.rerun()
        medications = render_medications(
            options,
            form_key=form_key,
            values=mapping_list_default(defaults.get(MEDICATIONS_KEY)),
        )

    return {
        "weight_pre_g": weight_pre_g,
        "weight_post_g": weight_post_g,
        "medications": medications,
        "start_time": start_time,
        "end_time": end_time,
        "bregma_lambda_dist_mm": bregma_lambda_dist_mm,
    }


def increment_procedure_count(form_key: str) -> None:
    count_key = surgery_count_key(form_key, SURGERY_PROCEDURE_COUNT_KEY)
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1


def procedure_injection_count_key(
    form_key: str,
    procedure_index: int,
) -> str:
    return surgery_key(
        form_key,
        f"procedure_{procedure_index}_injection_count",
    )


def injection_infusion_count_key(
    form_key: str,
    procedure_index: int,
    injection_index: int,
) -> str:
    return surgery_key(
        form_key,
        (
            f"procedure_{procedure_index}_"
            f"injection_{injection_index}_infusion_count"
        ),
    )


def procedure_electrode_count_key(
    form_key: str,
    procedure_index: int,
) -> str:
    return surgery_key(
        form_key,
        f"procedure_{procedure_index}_electrode_count",
    )


def increment_injection_count(form_key: str, procedure_index: int) -> None:
    count_key = procedure_injection_count_key(form_key, procedure_index)
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1


def increment_electrode_count(form_key: str, procedure_index: int) -> None:
    count_key = procedure_electrode_count_key(form_key, procedure_index)
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1


def increment_infusion_count(
    form_key: str,
    procedure_index: int,
    injection_index: int,
) -> None:
    count_key = injection_infusion_count_key(
        form_key,
        procedure_index,
        injection_index,
    )
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1


def render_virus_attributes(
    *,
    form_key: str,
    procedure_index: int,
    injection_index: int,
    virus: str,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}
    virus_key = surgery_key(
        form_key,
        (
            f"procedure_{procedure_index}_injection_{injection_index}_"
            f"virus_{stable_key_part(virus)}"
        ),
    )
    st.markdown(f"##### {virus}")
    virus_source = render_select_with_immediate_other(
        label="Virus Source",
        options=options,
        options_key=VIRUS_SOURCE_OPTIONS_KEY,
        widget_key=f"{virus_key}_source",
        other_prompt="New Virus Source",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(VIRUS_SOURCE_KEY)),
    )
    virus_id = st.text_input(
        "Virus ID",
        key=f"{virus_key}_virus_id",
        value=clean_string(defaults.get(VIRUS_ID_KEY)),
    )
    virus_stock = st.text_input(
        "Virus Lot",
        key=f"{virus_key}_virus_stock",
        value=clean_string(defaults.get(VIRUS_STOCK_KEY)),
    )
    render_text_guidance(
        "Stock Titer must match the regex pattern "
        f"`{STOCK_TITER_PATTERN_TEXT}`, for example `2_10_13`."
    )
    stock_titer = st.text_input(
        "Stock Titer",
        key=f"{virus_key}_stock_titer",
        value=clean_string(defaults.get(STOCK_TITER_KEY)),
    )
    dilution = st.text_input(
        "Dilution",
        key=f"{virus_key}_dilution",
        value=clean_string(defaults.get(DILUTION_KEY)),
    )
    infusion_rate_nlmin = st.number_input(
        "Infusion Rate (nl/min)",
        min_value=0.0,
        value=number_default(defaults.get(INFUSION_RATE_NLMIN_KEY)),
        step=1.0,
        key=f"{virus_key}_infusion_rate_nlmin",
    )
    return {
        VIRUS_KEY: virus,
        VIRUS_SOURCE_KEY: virus_source,
        VIRUS_ID_KEY: virus_id,
        VIRUS_STOCK_KEY: virus_stock,
        STOCK_TITER_KEY: stock_titer,
        DILUTION_KEY: dilution,
        INFUSION_RATE_NLMIN_KEY: infusion_rate_nlmin,
    }


def render_infusions(
    *,
    form_key: str,
    procedure_index: int,
    injection_index: int,
    values: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, object]]:
    count_key = injection_infusion_count_key(
        form_key,
        procedure_index,
        injection_index,
    )
    st.session_state.setdefault(count_key, max(1, len(values)))

    if st.button(
        "Add infusion location",
        key=(
            f"{form_key}_procedure_{procedure_index}_"
            f"injection_{injection_index}_add_infusion"
        ),
        use_container_width=True,
    ):
        increment_infusion_count(form_key, procedure_index, injection_index)
        st.rerun()

    infusions: list[dict[str, object]] = []
    for infusion_index in range(1, st.session_state[count_key] + 1):
        defaults = (
            values[infusion_index - 1] if infusion_index <= len(values) else {}
        )
        prefix = surgery_key(
            form_key,
            (
                f"procedure_{procedure_index}_"
                f"injection_{injection_index}_infusion_{infusion_index}"
            ),
        )
        st.markdown(f"##### Infusion Location {infusion_index}")
        ap = st.number_input(
            "AP",
            value=number_default(defaults.get(AP_KEY)),
            step=0.1,
            key=f"{prefix}_ap",
        )
        ml = st.number_input(
            "ML",
            value=number_default(defaults.get(ML_KEY)),
            step=0.1,
            key=f"{prefix}_ml",
        )
        dv = st.number_input(
            "DV",
            value=number_default(defaults.get(DV_KEY)),
            step=0.1,
            key=f"{prefix}_dv",
        )
        infusion_volume_nl = st.number_input(
            "Infusion Volume (nl)",
            min_value=0.0,
            value=number_default(defaults.get(INFUSION_VOLUME_NL_KEY)),
            step=10.0,
            key=f"{prefix}_infusion_volume_nl",
        )
        post_infusion_flow_test_default = (
            clean_string(defaults.get(POST_INFUSION_FLOW_TEST_KEY)) or "n/a"
        )
        post_infusion_flow_test = st.selectbox(
            "Post Infusion Flow Test",
            options=POST_INFUSION_FLOW_TEST_OPTIONS,
            key=f"{prefix}_post_infusion_flow_test",
            index=selected_index(
                POST_INFUSION_FLOW_TEST_OPTIONS,
                post_infusion_flow_test_default,
            ),
        )
        notes = st.text_input(
            "Notes",
            key=f"{prefix}_notes",
            value=clean_string(defaults.get(NOTES_KEY)),
        )
        infusions.append(
            {
                AP_KEY: ap,
                ML_KEY: ml,
                DV_KEY: dv,
                INFUSION_VOLUME_NL_KEY: infusion_volume_nl,
                POST_INFUSION_FLOW_TEST_KEY: post_infusion_flow_test,
                NOTES_KEY: notes,
            }
        )
    return infusions


def render_injection(
    *,
    form_key: str,
    procedure_index: int,
    injection_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}
    prefix = surgery_key(
        form_key,
        f"procedure_{procedure_index}_injection_{injection_index}",
    )
    st.markdown(f"#### Injection {injection_index}")
    site = render_select_with_immediate_other(
        label="Site",
        options=options,
        options_key=SITE_OPTIONS_KEY,
        widget_key=f"{prefix}_site",
        other_prompt="New Site",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(SITE_KEY)),
    )
    hemisphere = st.selectbox(
        "hemisphere",
        options=HEMISPHERE_OPTIONS,
        key=f"{prefix}_hemisphere",
        index=selected_index(HEMISPHERE_OPTIONS, defaults.get(HEMISPHERE_KEY)),
    )
    virus_defaults = mapping_list_default(defaults.get(VIRUSES_KEY))
    selected_viruses = render_virus_multiselect(
        options=options,
        widget_key=f"{prefix}_viruses",
        notebook=notebook,
        config=config,
        values=[
            clean_string(virus_defaults_item.get(VIRUS_KEY))
            for virus_defaults_item in virus_defaults
        ],
    )
    viruses = [
        render_virus_attributes(
            form_key=form_key,
            procedure_index=procedure_index,
            injection_index=injection_index,
            virus=virus,
            options=options,
            notebook=notebook,
            config=config,
            defaults=next(
                (
                    virus_defaults_item
                    for virus_defaults_item in virus_defaults
                    if clean_string(virus_defaults_item.get(VIRUS_KEY))
                    == virus
                ),
                {},
            ),
        )
        for virus in selected_viruses
    ]

    st.markdown("##### Infusion Locations")
    infusions = render_infusions(
        form_key=form_key,
        procedure_index=procedure_index,
        injection_index=injection_index,
        values=mapping_list_default(defaults.get(INFUSIONS_KEY)),
    )
    return {
        SITE_KEY: site,
        HEMISPHERE_KEY: hemisphere,
        "viruses": viruses,
        "infusions": infusions,
    }


def render_viral_injection_procedure(
    *,
    form_key: str,
    procedure_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}
    injection_defaults = mapping_list_default(defaults.get(INJECTIONS_KEY))
    count_key = procedure_injection_count_key(form_key, procedure_index)
    st.session_state.setdefault(count_key, max(1, len(injection_defaults)))
    if st.button(
        "Add injection",
        key=surgery_key(
            form_key,
            f"procedure_{procedure_index}_add_injection",
        ),
        use_container_width=True,
    ):
        increment_injection_count(form_key, procedure_index)
        st.rerun()

    injections = [
        render_injection(
            form_key=form_key,
            procedure_index=procedure_index,
            injection_index=injection_index,
            options=options,
            notebook=notebook,
            config=config,
            defaults=(
                injection_defaults[injection_index - 1]
                if injection_index <= len(injection_defaults)
                else {}
            ),
        )
        for injection_index in range(1, st.session_state[count_key] + 1)
    ]
    return {
        SURGERY_CATEGORY_KEY: VIRAL_INJECTION_CATEGORY,
        "injections": injections,
    }


def render_implant_type(
    *,
    form_key: str,
    procedure_index: int,
    value: str = "",
) -> str:
    choices = [*IMPLANT_TYPE_OPTIONS, OTHER_CHOICE]
    cleaned_value = clean_string(value)
    index = (
        choices.index(cleaned_value)
        if cleaned_value in choices
        else choices.index(OTHER_CHOICE)
        if cleaned_value
        else 0
    )
    selected = st.selectbox(
        "Implant Type",
        options=choices,
        index=index,
        key=surgery_key(form_key, f"procedure_{procedure_index}_implant_type"),
    )
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            "New Implant Type",
            key=surgery_key(
                form_key,
                f"procedure_{procedure_index}_implant_type_other",
            ),
            value="" if cleaned_value in choices else cleaned_value,
        )
    )


def render_cranial_window_implant(
    *,
    form_key: str,
    procedure_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}
    prefix = surgery_key(
        form_key,
        f"procedure_{procedure_index}_cranial_window",
    )
    headplate_type = render_select_with_immediate_other(
        label="Headplate Type",
        options=options,
        options_key=HEADPLATE_TYPE_OPTIONS_KEY,
        widget_key=f"{prefix}_headplate_type",
        other_prompt="New Headplate Type",
        notebook=notebook,
        config=config,
        choices=scoped_choice_options(
            options,
            HEADPLATE_TYPE_OPTIONS_KEY,
            ("Standard_Y",),
            ("Standard_0",),
        ),
        value=clean_string(defaults.get(HEADPLATE_TYPE_KEY)),
    )
    coverslip_type = render_select_with_immediate_other(
        label="Coverslip Type",
        options=options,
        options_key=COVERSLIP_TYPE_OPTIONS_KEY,
        widget_key=f"{prefix}_coverslip_type",
        other_prompt="New Coverslip Type",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(COVERSLIP_TYPE_KEY)),
    )
    coverslip_diameter = render_select_with_immediate_other(
        label="Coverslip Diameter",
        options=options,
        options_key=COVERSLIP_DIAMETER_OPTIONS_KEY,
        widget_key=f"{prefix}_coverslip_diameter",
        other_prompt="New Coverslip Diameter",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(COVERSLIP_DIAMETER_KEY)),
    )
    coverslip_thickness = render_select_with_immediate_other(
        label="Coverslip Thickness",
        options=options,
        options_key=COVERSLIP_THICKNESS_OPTIONS_KEY,
        widget_key=f"{prefix}_coverslip_thickness",
        other_prompt="New Coverslip Thickness",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(COVERSLIP_THICKNESS_KEY)),
    )
    region = render_select_with_immediate_other(
        label="Region",
        options=options,
        options_key=CRANIAL_WINDOW_REGION_OPTIONS_KEY,
        widget_key=f"{prefix}_region",
        other_prompt="New Region",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(REGION_KEY)),
    )
    center_ap = st.number_input(
        "Center AP",
        value=number_default(defaults.get(CENTER_AP_KEY)),
        step=0.1,
        key=f"{prefix}_center_ap",
    )
    center_ml = st.number_input(
        "Center ML",
        value=number_default(defaults.get(CENTER_ML_KEY)),
        step=0.1,
        key=f"{prefix}_center_ml",
    )
    well_type = st.selectbox(
        "Well Type",
        options=WELL_TYPE_OPTIONS,
        key=f"{prefix}_well_type",
        index=selected_index(WELL_TYPE_OPTIONS, defaults.get(WELL_TYPE_KEY)),
    )
    notes = st.text_input(
        "Notes",
        key=f"{prefix}_notes",
        value=clean_string(defaults.get(NOTES_KEY)),
    )

    return {
        HEADPLATE_TYPE_KEY: headplate_type,
        COVERSLIP_TYPE_KEY: coverslip_type,
        COVERSLIP_DIAMETER_KEY: coverslip_diameter,
        COVERSLIP_THICKNESS_KEY: coverslip_thickness,
        REGION_KEY: region,
        CENTER_AP_KEY: center_ap,
        CENTER_ML_KEY: center_ml,
        WELL_TYPE_KEY: well_type,
        NOTES_KEY: notes,
    }


def render_crystal_skull_implant(
    *,
    form_key: str,
    procedure_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}
    prefix = surgery_key(
        form_key,
        f"procedure_{procedure_index}_crystal_skull",
    )
    headplate_type = render_select_with_immediate_other(
        label="Headplate Type",
        options=options,
        options_key=HEADPLATE_TYPE_OPTIONS_KEY,
        widget_key=f"{prefix}_headplate_type",
        other_prompt="New Headplate Type",
        notebook=notebook,
        config=config,
        choices=scoped_choice_options(
            options,
            HEADPLATE_TYPE_OPTIONS_KEY,
            ("Standard_0",),
            ("Standard_Y",),
        ),
        value=clean_string(defaults.get(HEADPLATE_TYPE_KEY)),
    )
    cs_type = render_select_with_immediate_other(
        label="CS Type",
        options=options,
        options_key=CS_TYPE_OPTIONS_KEY,
        widget_key=f"{prefix}_cs_type",
        other_prompt="New CS Type",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(CS_TYPE_KEY)),
    )
    front_ap = st.number_input(
        "Front AP",
        value=number_default(defaults.get(FRONT_AP_KEY)),
        step=0.1,
        key=f"{prefix}_front_ap",
    )
    left_ml = st.number_input(
        "Left ML",
        value=number_default(defaults.get(LEFT_ML_KEY)),
        step=0.1,
        key=f"{prefix}_left_ml",
    )
    well_type = render_select_with_immediate_other(
        label="Well Type",
        options=options,
        options_key=CRYSTAL_SKULL_WELL_TYPE_OPTIONS_KEY,
        widget_key=f"{prefix}_well_type",
        other_prompt="New Well Type",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(WELL_TYPE_KEY)),
    )

    return {
        HEADPLATE_TYPE_KEY: headplate_type,
        CS_TYPE_KEY: cs_type,
        FRONT_AP_KEY: front_ap,
        LEFT_ML_KEY: left_ml,
        WELL_TYPE_KEY: well_type,
    }


def render_electrode_object(
    *,
    form_key: str,
    procedure_index: int,
    electrode_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}
    prefix = surgery_key(
        form_key,
        f"procedure_{procedure_index}_electrode_{electrode_index}",
    )
    st.markdown(f"#### Electrode {electrode_index}")
    electrode_type = st.selectbox(
        "Electrode Type",
        options=ELECTRODE_TYPE_OPTIONS,
        key=f"{prefix}_electrode_type",
        index=selected_index(
            ELECTRODE_TYPE_OPTIONS,
            defaults.get(ELECTRODE_TYPE_KEY),
        ),
    )
    probe_model = render_select_with_immediate_other(
        label="Probe Model",
        options=options,
        options_key=PROBE_MODEL_OPTIONS_KEY,
        widget_key=f"{prefix}_probe_model",
        other_prompt="New Probe Model",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(PROBE_MODEL_KEY)),
    )
    probe_id = st.text_input(
        "Probe ID",
        key=f"{prefix}_probe_id",
        value=clean_string(defaults.get(PROBE_ID_KEY)),
    )
    electrode_site = render_select_with_immediate_other(
        label="Electrode Site",
        options=options,
        options_key=ELECTRODE_SITE_OPTIONS_KEY,
        widget_key=f"{prefix}_electrode_site",
        other_prompt="New Electrode Site",
        notebook=notebook,
        config=config,
        value=clean_string(defaults.get(ELECTRODE_SITE_KEY)),
    )
    electrode_hemisphere = st.selectbox(
        "Electrode Hemisphere",
        options=HEMISPHERE_OPTIONS,
        key=f"{prefix}_electrode_hemisphere",
        index=selected_index(
            HEMISPHERE_OPTIONS,
            defaults.get(ELECTRODE_HEMISPHERE_KEY),
        ),
    )
    pitch = st.text_input(
        "Pitch",
        key=f"{prefix}_pitch",
        value=clean_string(defaults.get(PITCH_KEY)),
    )
    yaw = st.text_input(
        "Yaw",
        key=f"{prefix}_yaw",
        value=clean_string(defaults.get(YAW_KEY)),
    )
    roll = st.text_input(
        "Roll",
        key=f"{prefix}_roll",
        value=clean_string(defaults.get(ROLL_KEY)),
    )
    ap = st.number_input(
        "AP",
        value=number_default(defaults.get(AP_KEY)),
        step=0.1,
        key=f"{prefix}_ap",
    )
    ml = st.number_input(
        "ML",
        value=number_default(defaults.get(ML_KEY)),
        step=0.1,
        key=f"{prefix}_ml",
    )
    dv = st.number_input(
        "DV",
        value=number_default(defaults.get(DV_KEY)),
        step=0.1,
        key=f"{prefix}_dv",
    )
    ground = st.text_input(
        "Ground",
        key=f"{prefix}_ground",
        value=clean_string(defaults.get(GROUND_KEY)),
    )
    reference = st.text_input(
        "Reference",
        key=f"{prefix}_reference",
        value=clean_string(defaults.get(REFERENCE_KEY)),
    )
    notes = st.text_input(
        "Notes",
        key=f"{prefix}_notes",
        value=clean_string(defaults.get(NOTES_KEY)),
    )

    return {
        ELECTRODE_TYPE_KEY: electrode_type,
        PROBE_MODEL_KEY: probe_model,
        PROBE_ID_KEY: probe_id,
        ELECTRODE_SITE_KEY: electrode_site,
        ELECTRODE_HEMISPHERE_KEY: electrode_hemisphere,
        PITCH_KEY: pitch,
        YAW_KEY: yaw,
        ROLL_KEY: roll,
        AP_KEY: ap,
        ML_KEY: ml,
        DV_KEY: dv,
        GROUND_KEY: ground,
        REFERENCE_KEY: reference,
        NOTES_KEY: notes,
    }


def render_electrode_implant(
    *,
    form_key: str,
    procedure_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    values: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, object]]:
    count_key = procedure_electrode_count_key(form_key, procedure_index)
    st.session_state.setdefault(count_key, max(1, len(values)))
    if st.button(
        "Add electrode",
        key=surgery_key(
            form_key,
            f"procedure_{procedure_index}_add_electrode",
        ),
        use_container_width=True,
    ):
        increment_electrode_count(form_key, procedure_index)
        st.rerun()

    return [
        render_electrode_object(
            form_key=form_key,
            procedure_index=procedure_index,
            electrode_index=electrode_index,
            options=options,
            notebook=notebook,
            config=config,
            defaults=(
                values[electrode_index - 1]
                if electrode_index <= len(values)
                else {}
            ),
        )
        for electrode_index in range(1, st.session_state[count_key] + 1)
    ]


def render_implant_procedure(
    *,
    form_key: str,
    procedure_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}
    implant_type = render_implant_type(
        form_key=form_key,
        procedure_index=procedure_index,
        value=clean_string(defaults.get(IMPLANT_TYPE_KEY)),
    )
    procedure: dict[str, object] = {
        SURGERY_CATEGORY_KEY: IMPLANT_CATEGORY,
        IMPLANT_TYPE_KEY: implant_type,
    }
    if implant_type == CRANIAL_WINDOW_IMPLANT_TYPE:
        procedure[CRANIAL_WINDOW_KEY] = render_cranial_window_implant(
            form_key=form_key,
            procedure_index=procedure_index,
            options=options,
            notebook=notebook,
            config=config,
            defaults=mapping_default(defaults.get(CRANIAL_WINDOW_KEY)),
        )
        return procedure

    if implant_type == CRYSTAL_SKULL_IMPLANT_TYPE:
        procedure[CRYSTAL_SKULL_KEY] = render_crystal_skull_implant(
            form_key=form_key,
            procedure_index=procedure_index,
            options=options,
            notebook=notebook,
            config=config,
            defaults=mapping_default(defaults.get(CRYSTAL_SKULL_KEY)),
        )
        return procedure

    if implant_type == ELECTRODE_IMPLANT_TYPE:
        procedure[ELECTRODES_KEY] = render_electrode_implant(
            form_key=form_key,
            procedure_index=procedure_index,
            options=options,
            notebook=notebook,
            config=config,
            values=mapping_list_default(defaults.get(ELECTRODES_KEY)),
        )
        return procedure

    st.info(
        "Only Cranial Window, Crystal Skull, and Electrode implant fields are "
        "implemented yet."
    )
    return procedure


def render_surgical_procedures(
    *,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    form_key: str,
    values: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, object]]:
    st.subheader("Surgical Procedures")
    count_key = surgery_count_key(form_key, SURGERY_PROCEDURE_COUNT_KEY)
    st.session_state.setdefault(count_key, max(1, len(values)))
    if st.button(
        "Add surgical procedure",
        key=surgery_key(form_key, "add_procedure"),
        use_container_width=True,
    ):
        increment_procedure_count(form_key)
        st.rerun()

    procedures: list[dict[str, object]] = []
    for procedure_index in range(
        1,
        st.session_state[count_key] + 1,
    ):
        procedure_defaults = (
            values[procedure_index - 1]
            if procedure_index <= len(values)
            else {}
        )
        is_latest_procedure = procedure_index == st.session_state[count_key]
        with st.expander(
            f"Procedure {procedure_index}",
            expanded=is_latest_procedure,
        ):
            category = st.selectbox(
                "Subject Category",
                options=SURGERY_CATEGORY_OPTIONS,
                key=surgery_key(
                    form_key,
                    f"procedure_{procedure_index}_category",
                ),
                index=selected_index(
                    SURGERY_CATEGORY_OPTIONS,
                    procedure_defaults.get(SURGERY_CATEGORY_KEY),
                ),
            )
            if category == IMPLANT_CATEGORY:
                procedures.append(
                    render_implant_procedure(
                        form_key=form_key,
                        procedure_index=procedure_index,
                        options=options,
                        notebook=notebook,
                        config=config,
                        defaults=procedure_defaults,
                    )
                )
                continue

            procedures.append(
                render_viral_injection_procedure(
                    form_key=form_key,
                    procedure_index=procedure_index,
                    options=options,
                    notebook=notebook,
                    config=config,
                    defaults=procedure_defaults,
                )
            )
    return procedures


def render_general_notes_attachments(
    *,
    form_key: str,
    defaults: Mapping[str, Any] | None = None,
) -> GeneralNotesAttachmentValues:
    defaults = defaults or {}
    with st.expander("General Notes & Attachments", expanded=True):
        general_notes = st.text_area(
            "General Notes",
            key=surgery_key(form_key, "general_notes"),
            value=clean_string(defaults.get(GENERAL_NOTES_KEY)),
        )
        note_uploads = st.file_uploader(
            "Note Upload",
            accept_multiple_files=True,
            key=surgery_key(form_key, "note_upload"),
        )
        photo_uploads = st.file_uploader(
            "Photo Upload",
            type=["png", "jpg", "jpeg", "tif", "tiff"],
            accept_multiple_files=True,
            key=surgery_key(form_key, "photo_upload"),
        )
        slot_ids = current_taken_photo_slot_ids(st.session_state, form_key)
        taken_photos: list[Any] = []
        for photo_index, slot_id in enumerate(slot_ids, start=1):
            if st.button(
                f"Remove Photo {photo_index}",
                key=surgery_key(form_key, f"remove_taken_photo_{slot_id}"),
            ):
                remove_taken_photo_slot(
                    st.session_state,
                    form_key=form_key,
                    slot_id=slot_id,
                )
                st.rerun()

            taken_photo = st.camera_input(
                f"Take Photo {photo_index}",
                key=taken_photo_widget_key(form_key, slot_id),
            )
            if taken_photo is not None:
                taken_photos.append(taken_photo)

        if st.button(
            "Add photo",
            key=surgery_key(form_key, "add_taken_photo"),
        ):
            add_taken_photo_slot(st.session_state, form_key)
            st.rerun()

    return {
        "general_notes": general_notes,
        "note_uploads": list(note_uploads or []),
        "photo_uploads": list(photo_uploads or []),
        "taken_photos": taken_photos,
    }


def uploaded_file_name(uploaded_file: Any, default_filename: str) -> str:
    return clean_string(getattr(uploaded_file, "name", "")) or default_filename


def uploaded_file_mime_type(uploaded_file: Any, default_mime_type: str) -> str:
    return (
        clean_string(getattr(uploaded_file, "type", "")) or default_mime_type
    )


def uploaded_file_bytes(uploaded_file: Any) -> bytes:
    getvalue = getattr(uploaded_file, "getvalue", None)
    if callable(getvalue):
        return bytes(getvalue())

    seek = getattr(uploaded_file, "seek", None)
    if callable(seek):
        seek(0)
    read = getattr(uploaded_file, "read", None)
    if callable(read):
        return bytes(read())
    raise ValueError("Uploaded file could not be read.")


def save_general_surgery_attachments(
    *,
    page: Any,
    payload: Mapping[str, Any],
    attachment_values: GeneralNotesAttachmentValues,
) -> list[dict[str, str]]:
    animal_id = clean_string(payload.get(ANIMAL_ID_KEY))
    surgery_date = clean_string(payload.get(SURGERY_DATE_KEY))
    attachment_inputs: list[tuple[str, int, Any, str, str]] = []

    for index, uploaded_file in enumerate(
        attachment_values["note_uploads"],
        start=1,
    ):
        attachment_inputs.append(
            (
                NOTE_UPLOAD_TYPE,
                index,
                uploaded_file,
                uploaded_file_name(uploaded_file, "note_upload"),
                uploaded_file_mime_type(
                    uploaded_file,
                    "application/octet-stream",
                ),
            )
        )
    for index, uploaded_file in enumerate(
        attachment_values["photo_uploads"],
        start=1,
    ):
        attachment_inputs.append(
            (
                PHOTO_UPLOAD_TYPE,
                index,
                uploaded_file,
                uploaded_file_name(uploaded_file, "photo_upload"),
                uploaded_file_mime_type(uploaded_file, "image/jpeg"),
            )
        )

    for index, taken_photo in enumerate(
        attachment_values["taken_photos"],
        start=1,
    ):
        attachment_inputs.append(
            (
                TAKEN_PHOTO_UPLOAD_TYPE,
                index,
                taken_photo,
                "camera_capture.jpg",
                uploaded_file_mime_type(taken_photo, "image/jpeg"),
            )
        )

    references: list[dict[str, str]] = []
    for (
        upload_type,
        index,
        uploaded_file,
        original_filename,
        mime_type,
    ) in attachment_inputs:
        filename = surgery_upload_filename(
            animal_id=animal_id,
            surgery_date=surgery_date,
            upload_type=upload_type,
            index=index,
            original_filename=original_filename,
        )
        try:
            result = save_surgery_file_attachment(
                page,
                payload=uploaded_file_bytes(uploaded_file),
                filename=filename,
                mime_type=mime_type,
                upload_type=upload_type,
            )
        except (ApiError, ValueError) as exc:
            raise ValueError(f"{filename}: {exc}") from exc
        references.append(result.reference)

    return references


def existing_attachment_references(
    payload: Mapping[str, Any],
) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    for raw_reference in mapping_list_default(payload.get(ATTACHMENTS_KEY)):
        references.append(
            {
                key: clean_string(raw_reference.get(key))
                for key in (
                    "upload_type",
                    "entry_id",
                    "filename",
                    "caption",
                    "mime_type",
                )
            }
        )
    return references


def has_new_attachment_uploads(
    attachment_values: GeneralNotesAttachmentValues,
) -> bool:
    return bool(
        attachment_values["note_uploads"]
        or attachment_values["photo_uploads"]
        or attachment_values["taken_photos"]
    )


def merge_attachment_references(
    existing_references: list[dict[str, str]],
    new_references: list[dict[str, str]],
) -> list[dict[str, str]]:
    merged_by_filename: dict[str, dict[str, str]] = {}
    for reference in [*existing_references, *new_references]:
        filename = clean_string(reference.get("filename"))
        if filename:
            merged_by_filename[filename] = reference

    return list(merged_by_filename.values())


def render_attachment_reference_action(
    *,
    form_key: str,
    existing_references: list[dict[str, str]],
) -> str:
    if not existing_references:
        return ATTACHMENT_ACTION_REPLACE

    return st.radio(
        "Existing attachment references",
        options=ATTACHMENT_ACTION_OPTIONS,
        key=surgery_key(form_key, "attachment_reference_action"),
    )


def resolve_attachment_references(
    *,
    action: str,
    existing_references: list[dict[str, str]],
    new_references: list[dict[str, str]],
    has_new_uploads: bool,
) -> list[dict[str, str]] | None:
    if not existing_references:
        return new_references

    if action == ATTACHMENT_ACTION_PRESERVE:
        return merge_attachment_references(existing_references, new_references)

    if action == ATTACHMENT_ACTION_REPLACE:
        if not has_new_uploads:
            st.error(
                "Upload at least one new note or photo before replacing "
                "existing attachment references."
            )
            return None
        return new_references

    if has_new_uploads:
        st.error(
            "Remove existing attachment references cannot be combined with "
            "new uploads. Choose Replace with new uploads instead."
        )
        return None
    return []


def save_reusable_surgery_options(
    *,
    notebook: Any,
    config: dict[str, Any],
    surgeon: str,
    medications: list[str],
    sites: list[str],
    viruses: list[str],
    virus_sources: list[str],
    headplate_types: list[str],
    coverslip_types: list[str],
    coverslip_diameters: list[str],
    coverslip_thicknesses: list[str],
    cranial_window_regions: list[str],
    cs_types: list[str],
    crystal_skull_well_types: list[str],
    probe_models: list[str],
    electrode_sites: list[str],
) -> None:
    updated_config, changed = with_surgery_options(
        config,
        surgeon=surgeon,
        medications=medications,
        sites=sites,
        viruses=viruses,
        virus_sources=virus_sources,
        headplate_types=headplate_types,
        coverslip_types=coverslip_types,
        coverslip_diameters=coverslip_diameters,
        coverslip_thicknesses=coverslip_thicknesses,
        cranial_window_regions=cranial_window_regions,
        cs_types=cs_types,
        crystal_skull_well_types=crystal_skull_well_types,
        probe_models=probe_models,
        electrode_sites=electrode_sites,
    )
    if not changed:
        return

    config_page = st.session_state.get(CONFIG_PAGE_STATE_KEY)
    if config_page is None:
        config_page = find_root_config_page(notebook)

    if config_page is None:
        st.warning(
            "Saved the surgery record, but could not find muronto_config to "
            "save reusable surgery options."
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


def load_surgery_records(page: Any) -> list[SurgeryRecord] | None:
    try:
        return discover_surgery_records(page)
    except ApiError as exc:
        st.error(f"Unable to load surgery records from LabArchives: {exc}")
    return None


def render_surgery_form(
    *,
    notebook: Any,
    config: dict[str, Any],
    project: dict[str, str],
    investigator: str,
    selected_subject: SubjectRecord,
    existing_record: SurgeryRecord | None = None,
) -> None:
    subject_payload = selected_subject.payload
    payload_defaults = existing_record.payload if existing_record else {}
    form_key = SURGERY_CREATE_FORM_KEY
    if existing_record is not None:
        form_key = f"surgery_edit_{surgery_record_widget_key(existing_record)}"
    existing_references = existing_attachment_references(payload_defaults)
    options = normalize_options(config.get(OPTIONS_KEY))

    with st.expander("Surgery Details", expanded=True):
        surgeon = render_surgeon_select(
            options,
            form_key=form_key,
            value=string_default(payload_defaults, SURGEON_KEY),
        )
        surgery_date = render_surgery_date(
            form_key=form_key,
            value=parse_surgery_date(payload_defaults.get(SURGERY_DATE_KEY)),
        )

        render_text_guidance(
            "PreOp CNN must match the regex pattern "
            f"`{CNN_PATTERN_TEXT}`, for example `123456`."
        )
        preop_cnn = st.text_input(
            "PreOp CNN",
            key=surgery_key(form_key, "preop_cnn"),
            value=string_default(payload_defaults, PREOP_CNN_KEY),
        )

        render_text_guidance(
            "PostOp CNN must match the regex pattern "
            f"`{CNN_PATTERN_TEXT}`, for example `123456`."
        )
        postop_cnn = st.text_input(
            "PostOp CNN",
            key=surgery_key(form_key, "postop_cnn"),
            value=string_default(payload_defaults, POSTOP_CNN_KEY),
        )

    perioperative_values = render_perioperative_monitoring(
        options,
        form_key=form_key,
        defaults=payload_defaults,
    )
    surgical_procedures = render_surgical_procedures(
        options=options,
        notebook=notebook,
        config=config,
        form_key=form_key,
        values=mapping_list_default(
            payload_defaults.get(SURGICAL_PROCEDURES_KEY)
        ),
    )
    general_attachment_values = render_general_notes_attachments(
        form_key=form_key,
        defaults=payload_defaults,
    )
    attachment_action = render_attachment_reference_action(
        form_key=form_key,
        existing_references=existing_references,
    )

    submitted = st.button(
        "Save surgery record",
        type="primary",
        use_container_width=True,
        key=surgery_key(form_key, "submit"),
    )
    if not submitted:
        return

    def build_payload(
        attachments: list[dict[str, str]],
    ) -> dict[str, Any]:
        return build_surgery_payload(
            project_id=project[PROJECT_ID_KEY],
            investigator=investigator,
            animal_id=subject_payload.get(ANIMAL_ID_KEY, ""),
            ear_tag=subject_payload.get(EAR_TAG_KEY, ""),
            surgeon=surgeon,
            surgery_date=surgery_date,
            preop_cnn=preop_cnn,
            postop_cnn=postop_cnn,
            general_notes=general_attachment_values["general_notes"],
            attachments=attachments,
            weight_pre_g=perioperative_values["weight_pre_g"],
            weight_post_g=perioperative_values["weight_post_g"],
            medications=perioperative_values["medications"],
            start_time=perioperative_values["start_time"],
            end_time=perioperative_values["end_time"],
            bregma_lambda_dist_mm=perioperative_values[
                "bregma_lambda_dist_mm"
            ],
            surgical_procedures=surgical_procedures,
        )

    try:
        payload = build_payload([])
    except SurgeryValidationError as exc:
        st.error("Complete the surgery form before saving the record.")
        for error in exc.errors:
            st.caption(error)
        return

    try:
        has_uploads = has_new_attachment_uploads(general_attachment_values)
        if (
            existing_references
            and attachment_action == ATTACHMENT_ACTION_REPLACE
        ):
            if not has_uploads:
                st.error(
                    "Upload at least one new note or photo before replacing "
                    "existing attachment references."
                )
                return
        if (
            existing_references
            and attachment_action == ATTACHMENT_ACTION_REMOVE
        ):
            if has_uploads:
                st.error(
                    "Remove existing attachment references cannot be combined "
                    "with new uploads. Choose Replace with new uploads "
                    "instead."
                )
                return

        attachment_references = save_general_surgery_attachments(
            page=selected_subject.page,
            payload=payload,
            attachment_values=general_attachment_values,
        )
        resolved_attachment_references = resolve_attachment_references(
            action=attachment_action,
            existing_references=existing_references,
            new_references=attachment_references,
            has_new_uploads=has_uploads,
        )
        if resolved_attachment_references is None:
            return
        payload = build_payload(resolved_attachment_references)
    except SurgeryValidationError as exc:
        st.error("Complete the surgery form before saving the record.")
        for error in exc.errors:
            st.caption(error)
        return
    except ValueError as exc:
        st.error(f"Unable to upload surgery attachment: {exc}")
        return

    try:
        result = save_surgery_attachment(
            selected_subject.page,
            payload,
            existing_entry=(
                existing_record.attachment_entry if existing_record else None
            ),
        )
    except ApiError as exc:
        st.error(f"Unable to save the surgery record: {exc}")
        return
    except ValueError as exc:
        st.error(str(exc))
        return

    try:
        (
            sites,
            viruses,
            virus_sources,
            headplate_types,
            coverslip_types,
            coverslip_diameters,
            coverslip_thicknesses,
            cranial_window_regions,
            cs_types,
            crystal_skull_well_types,
            probe_models,
            electrode_sites,
        ) = procedure_option_values(payload)
        save_reusable_surgery_options(
            notebook=notebook,
            config=config,
            surgeon=clean_string(payload["surgeon"]),
            medications=medication_names(payload),
            sites=sites,
            viruses=viruses,
            virus_sources=virus_sources,
            headplate_types=headplate_types,
            coverslip_types=coverslip_types,
            coverslip_diameters=coverslip_diameters,
            coverslip_thicknesses=coverslip_thicknesses,
            cranial_window_regions=cranial_window_regions,
            cs_types=cs_types,
            crystal_skull_well_types=crystal_skull_well_types,
            probe_models=probe_models,
            electrode_sites=electrode_sites,
        )
    except ApiError as exc:
        st.warning(
            "Saved the surgery record, but could not save the reusable "
            f"surgery options to muronto_config: {exc}"
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
    edit_existing = st.toggle(
        "Edit existing surgery record",
        key=SURGERY_EDIT_MODE_KEY,
    )

    with st.expander("Subject Information", expanded=True):
        subject_records = load_subject_records(notebook, project)
        if subject_records is None:
            return
        if not subject_records:
            st.info(
                "No subject JSON records were found in the project folder."
            )
            return

        selected_subject_index = st.selectbox(
            "Subject",
            options=list(range(len(subject_records))),
            format_func=lambda index: subject_label(subject_records[index]),
            key="surgery_subject",
        )
        selected_subject = subject_records[selected_subject_index]
        render_selected_subject(selected_subject)

    selected_surgery_record: SurgeryRecord | None = None
    if edit_existing:
        surgery_records = load_surgery_records(selected_subject.page)
        if surgery_records is None:
            return
        if not surgery_records:
            st.info(
                "No surgery JSON records were found on the selected subject."
            )
            return

        selected_surgery_index = st.selectbox(
            "Surgery Record",
            options=list(range(len(surgery_records))),
            format_func=lambda index: surgery_record_label(
                surgery_records[index]
            ),
            key=SURGERY_SELECTED_RECORD_KEY,
        )
        selected_surgery_record = surgery_records[selected_surgery_index]

    render_surgery_form(
        notebook=notebook,
        config=config,
        project=project,
        investigator=investigator,
        selected_subject=selected_subject,
        existing_record=selected_surgery_record,
    )


if __name__ == "__main__":
    main()
