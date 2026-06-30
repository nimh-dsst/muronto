from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time
from typing import Any, TypedDict
from uuid import uuid4

import streamlit as st
from labapi import ApiError

from muronto_app.prairieview_xml_metadata_auditor import (
    parse_prairieview_xml_bytes,
)

from muronto_app.config import (
    BEHAVIOR_RIG_OPTIONS_KEY,
    BEHAVIOR_TASK_NAME_OPTIONS_KEY,
    BEHAVIOR_TASK_PHASE_OPTIONS_KEY,
    CAMERA_ACQ_SOFTWARE_OPTIONS_KEY,
    CAMERA_MODEL_OPTIONS_KEY,
    CAMERA_VIEW_OPTIONS_KEY,
    CHANNEL_OPTIONS_KEY,
    GREEN_CHANNEL_SUBSTRATE_OPTIONS_KEY,
    GREEN_CONSTRUCT_OPTIONS_KEY,
    IMAGING_LAYER_OPTIONS_KEY,
    IMAGING_REGION_OPTIONS_KEY,
    INVIVO2P_IMAGER_OPTIONS_KEY,
    INVIVO2P_SOFTWARE_NAME_OPTIONS_KEY,
    INVIVO2P_SYSTEM_ID_OPTIONS_KEY,
    LA_HOME_FOLDER_KEY,
    OPTIONS_KEY,
    OTHER_CHOICE,
    PROJECT_ID_KEY,
    RED_CHANNEL_SUBSTRATE_OPTIONS_KEY,
    RED_CONSTRUCT_OPTIONS_KEY,
    SENSORY_STIMULUS_TYPE_OPTIONS_KEY,
    SESSION_TYPE_OPTIONS_KEY,
    choice_options,
    clean_string,
    investigator_for_user,
    normalize_options,
)
from muronto_app.labarchives import (
    Invivo2pRecord,
    SubjectRecord,
    discover_invivo2p_records,
    discover_subject_records,
    find_root_config_page,
    resolve_notebook_folder,
    save_config_attachment,
    save_invivo2p_attachment,
    save_invivo2p_file_attachment,
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
    GENOTYPE_LABEL,
    SEX_KEY,
    STRAIN_LABEL,
    STRAIN_OPTIONS_KEY,
    is_subject_incomplete,
)
from muronto_app.invivo2p import (
    ATTACHMENTS_KEY,
    BEHAVIOR_RIG_KEY,
    BEHAVIOR_TASK_NAME_KEY,
    BEHAVIOR_TASK_PHASE_KEY,
    CAMERA_ACQ_SOFTWARE_KEY,
    CAMERA_VIEW_KEY,
    CAMERA_FRAME_RATE_HZ_KEY,
    CAMERA_MODEL_KEY,
    CAMERA_NOTES_KEY,
    CAMERA_NUMBER_KEY,
    CAMERAS_KEY,
    CHANNEL_KEY,
    DEPTH_UM_KEY,
    END_TIME_KEY,
    FOV_NOTES_KEY,
    FOV_NUMBER_KEY,
    FOV_SIZE_UM_KEY,
    FOVS_KEY,
    FRAME_RATE_HZ_KEY,
    GENERAL_NOTES_KEY,
    GREEN_CHANNEL_SUBSTRATE_KEY,
    GREEN_CONSTRUCT_KEY,
    HEMISPHERE_KEY,
    HEMISPHERE_OPTIONS,
    IMAGER_KEY,
    IMAGING_LASER_POWER_MW_KEY,
    IMAGING_LASER_WAVELENGTH_NM_KEY,
    IMAGING_LAYER_KEY,
    IMAGING_REGION_KEY,
    INVIVO2P_DRAFT_ID_KEY,
    INVIVO2P_SOFTWARE_NAME_KEY,
    INVIVO2P_STATUS_INCOMPLETE,
    INVIVO2P_STATUS_KEY,
    INVIVO2P_SYSTEM_ID_KEY,
    INVIVO2P_TIME_PATTERN,
    INVIVO2P_VALIDATION_ERRORS_KEY,
    NOTE_UPLOAD_TYPE,
    NUM_PLANES_KEY,
    OBJECTIVE_KEY,
    PHOTO_UPLOAD_TYPE,
    PLANE_NUMBER_KEY,
    PLANES_KEY,
    PRAIRIEVIEW_VERSION_KEY,
    RAW_2P_IMAGING_DATA_PATH_KEY,
    RAW_2P_IMAGING_METADATA_PATH_KEY,
    RAW_2P_SYNC_DATA_PATH_KEY,
    RAW_2P_SYNC_METADATA_PATH_KEY,
    RED_CHANNEL_SUBSTRATE_KEY,
    RED_CONSTRUCT_KEY,
    RESOLUTION_PIX_KEY,
    SENSORY_STIMULI_KEY,
    SENSORY_STIMULUS_TYPE_KEY,
    SESSION_DATE_KEY,
    SESSION_ID_KEY,
    SESSION_TYPE_KEY,
    START_TIME_KEY,
    STIMULUS_DURATION_MS_KEY,
    STIMULUS_FREQUENCY_HZ_KEY,
    STIMULUS_NOTES_KEY,
    STIMULUS_REPETITION_KEY,
    TAKEN_PHOTO_UPLOAD_TYPE,
    ZOOM_KEY,
    NUM_CHANNELS_RECORDED_KEY,
    CHANNEL_NUMBERS_RECORDED_KEY,
    CHANNEL_NAMES_RECORDED_KEY,
    OBJECTIVE_MAGNIFICATION_KEY,
    OBJECTIVE_NA_KEY,
    STAGE_X_KEY,
    STAGE_Y_KEY,
    Z_FOCUS_KEY,
    PMT_GAIN_0_KEY,
    PMT_GAIN_1_KEY,
    PLANE_RELATIVE_DEPTHS_KEY,
    FRAME_COUNT_TOTAL_KEY,
    DURATION_S_KEY,
    VOLUME_RATE_HZ_KEY,
    Invivo2pValidationError,
    build_invivo2p_payload,
    format_session_date,
    format_session_time,
    format_session_time_display,
    invivo2p_record_file_token,
    with_invivo2p_payload_options,
)

# ------------------------------------------------------------------
# Page-specific constants
# ------------------------------------------------------------------

INVIVO2P_XML_METADATA_KEY = "invivo2p_xml_metadata"

COMMON_BEHAVIOR_TASK_PHASE_OPTIONS = (
    "Habituation",
    "Training",
    "Testing",
    "n/a",
)

SEASIC_TASK_NAME = "Sensory Evidence Accumulation"

SEASIC_BEHAVIOR_TASK_PHASE_OPTIONS = (
    "Phase 0: Habituation",
    "Phase 1A: Lick Port Training",
    "Phase 1B: Reduce Lick Port Availability",
    "Phase 2A: Response Shaping",
    "Phase 2B: Intro Auditory Cue and No-Response Window",
    "Phase 3A: Intro Evidence LED and Single Stim Forced Choice",
    "Phase 3B: Intro Delay Between Evidence and Response Windows",
    "Phase 3C: Bidirectional Push and Pull Reward",
    "Phase 3D: Reduce response Window",
    "Phase 3E: Intro Delay Between Threshold Response and Reward",
    "Phase 4A: Intro Multiple Identical Stimuli per Trial",
    "Phase 4B: Intro Mixed Stimuli per Trial",
    "Phase 5: Testing with No Expectation Cue",
    "Phase 6: Training Expecation Cue",
    "Phase 7: Testing Expectation Cue",
    "n/a",
)

st.set_page_config(page_title="Muronto In Vivo 2P", layout="centered")

INVIVO2P_CREATE_FORM_KEY = "invivo2p"
INVIVO2P_EDIT_MODE_KEY = "invivo2p_edit_existing"
INVIVO2P_SELECTED_RECORD_KEY = "invivo2p_edit_record"

INVIVO2P_COPY_MODE_KEY = "invivo2p_copy_existing"
INVIVO2P_COPY_SOURCE_RECORD_KEY = "invivo2p_copy_source_record"

INVIVO2P_STIMULUS_COUNT_KEY = "invivo2p_stimulus_count"
INVIVO2P_CAMERA_COUNT_KEY = "invivo2p_camera_count"
INVIVO2P_FOV_COUNT_KEY = "invivo2p_fov_count"

ATTACHMENT_ACTION_PRESERVE = "Preserve existing"
ATTACHMENT_ACTION_REPLACE = "Replace with new uploads"
ATTACHMENT_ACTION_REMOVE = "Remove existing"
ATTACHMENT_ACTION_OPTIONS = (
    ATTACHMENT_ACTION_PRESERVE,
    ATTACHMENT_ACTION_REPLACE,
    ATTACHMENT_ACTION_REMOVE,
)


class GeneralNotesAttachmentValues(TypedDict):
    general_notes: str
    note_uploads: list[Any]
    photo_uploads: list[Any]
    taken_photos: list[Any]


def render_text_guidance(text: str) -> None:
    st.markdown(text)


def invivo2p_key(form_key: str, suffix: str) -> str:
    return f"{form_key}_{suffix}"


def invivo2p_count_key(form_key: str, base_key: str) -> str:
    if form_key == INVIVO2P_CREATE_FORM_KEY:
        return base_key
    return invivo2p_key(form_key, base_key)


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


def parse_session_date(value: object) -> date | None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        return None

    try:
        return datetime.strptime(cleaned_value, "%Y%m%d").date()
    except ValueError:
        return None


def parse_session_time(value: object) -> time | None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        return None

    if not INVIVO2P_TIME_PATTERN.fullmatch(cleaned_value):
        return None

    try:
        return datetime.strptime(cleaned_value, "%H%M").time()
    except ValueError:
        return None


def stable_key_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return cleaned[:48] or "value"


def subject_label(record: SubjectRecord) -> str:
    animal_id = clean_string(record.payload.get(ANIMAL_ID_KEY)) or "Unknown"
    ear_tag = clean_string(record.payload.get(EAR_TAG_KEY))
    label = f"{animal_id} - Ear Tag {ear_tag}" if ear_tag else animal_id
    if is_subject_incomplete(record.payload):
        label = f"{label} (incomplete)"
    return label


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


def render_selected_subject(record: SubjectRecord) -> None:
    payload = record.payload
    st.write(f"Animal ID: {payload.get(ANIMAL_ID_KEY, '')}")
    st.write(f"Ear Tag: {payload.get(EAR_TAG_KEY, '')}")
    st.write(f"Sex: {payload.get(SEX_KEY, '')}")
    st.write(f"DOB: {payload.get(DOB_KEY, '')}")

    pairs = subject_strain_genotypes(payload)
    if not pairs:
        st.write("Strain/Genotype: Not recorded")
        return

    for index, (strain, genotype) in enumerate(pairs, start=1):
        st.write(f"{STRAIN_LABEL} {index}: {strain}")
        st.write(f"{GENOTYPE_LABEL} {index}: {genotype}")


def invivo2p_record_widget_key(record: Invivo2pRecord) -> str:
    entry_id = clean_string(getattr(record.attachment_entry, "id", ""))
    if entry_id:
        return stable_key_part(entry_id)
    session_date = clean_string(record.payload.get(SESSION_DATE_KEY))
    return stable_key_part(session_date or "selected")


def invivo2p_record_label(record: Invivo2pRecord) -> str:
    payload = record.payload
    session_date = clean_string(payload.get(SESSION_DATE_KEY))
    label = session_date or "Incomplete draft"

    session_id = clean_string(payload.get(SESSION_ID_KEY))
    if session_id:
        label = f"{label} - {session_id}"

    imager = clean_string(payload.get(IMAGER_KEY))
    if imager:
        label = f"{label} - {imager}"

    if clean_string(payload.get(INVIVO2P_STATUS_KEY)) == (
        INVIVO2P_STATUS_INCOMPLETE
    ):
        label = f"{label} (incomplete)"
    return label


def subject_invivo2p_record_label(
    pair: tuple[SubjectRecord, Invivo2pRecord],
) -> str:
    subject_record, invivo2p_record = pair
    return (
        f"{subject_label(subject_record)} | "
        f"{invivo2p_record_label(invivo2p_record)}"
    )


def invivo2p_draft_id(
    *,
    form_key: str,
    payload_defaults: Mapping[str, Any],
) -> str:
    existing_draft_id = clean_string(
        payload_defaults.get(INVIVO2P_DRAFT_ID_KEY)
    )
    if existing_draft_id:
        return existing_draft_id

    state_key = invivo2p_key(form_key, "draft_id")
    draft_id = clean_string(st.session_state.get(state_key))
    if not draft_id:
        draft_id = uuid4().hex[:12]
        st.session_state[state_key] = draft_id
    return draft_id


def render_select_with_immediate_other(
    *,
    label: str,
    options: dict[str, list[str]],
    options_key: str,
    widget_key: str,
    other_prompt: str,
    value: str = "",
    choices: list[str] | None = None,
) -> str:
    option_choices = choices or choice_options(options, options_key)
    cleaned_value = clean_string(value)
    index = (
        option_choices.index(cleaned_value)
        if cleaned_value in option_choices
        else option_choices.index(OTHER_CHOICE)
        if cleaned_value
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

    return clean_string(
        st.text_input(
            other_prompt,
            key=f"{widget_key}_other",
            value="" if cleaned_value in option_choices else cleaned_value,
        )
    )


def render_session_date(
    *,
    form_key: str,
    value: date | None = None,
) -> date | None:
    selected_date = st.date_input(
        "Session Date",
        value=value,
        key=invivo2p_key(form_key, "session_date"),
        format="YYYY/MM/DD",
    )
    if isinstance(selected_date, date):
        st.write(format_session_date(selected_date))
        return selected_date
    return None


def render_session_time(
    label: str,
    key: str,
    *,
    value: time | None = None,
) -> time | None:
    default_value = (
        format_session_time(value) if isinstance(value, time) else ""
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

    if not INVIVO2P_TIME_PATTERN.fullmatch(entered_time):
        st.error("Please enter a valid time (HHMM), for example 0900.")
        return None

    selected_time = parse_session_time(entered_time)
    if selected_time is None:
        st.error(f"{label} must be a valid 24-hour time.")
        return None

    st.write(format_session_time_display(selected_time))
    return selected_time


def save_reusable_invivo2p_options(
    *,
    notebook: Any,
    config: dict[str, Any],
    payload: Mapping[str, Any],
) -> None:
    updated_config, changed = with_invivo2p_payload_options(
        config,
        payload,
    )
    if not changed:
        return

    config_page = st.session_state.get(CONFIG_PAGE_STATE_KEY)
    if config_page is None:
        config_page = find_root_config_page(notebook)

    if config_page is None:
        st.warning(
            "Saved the invivo2p record, but could not find muronto_config "
            "to save reusable invivo2p options."
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


def load_invivo2p_records(page: Any) -> list[Invivo2pRecord] | None:
    try:
        return discover_invivo2p_records(page)
    except ApiError as exc:
        st.error(f"Unable to load invivo2p records from LabArchives: {exc}")
    return None


def load_all_invivo2p_records(
    subject_records: Sequence[SubjectRecord],
) -> list[tuple[SubjectRecord, Invivo2pRecord]] | None:
    all_invivo2p_records: list[tuple[SubjectRecord, Invivo2pRecord]] = []

    for subject_record in subject_records:
        invivo2p_records = load_invivo2p_records(subject_record.page)
        if invivo2p_records is None:
            return None

        for invivo2p_record in invivo2p_records:
            all_invivo2p_records.append((subject_record, invivo2p_record))

    return all_invivo2p_records


def sanitize_upload_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", clean_string(filename))
    cleaned = cleaned.strip("._-")
    return cleaned or "upload"


def invivo2p_upload_filename(
    *,
    animal_id: str,
    session_token: str,
    upload_type: str,
    index: int,
    original_filename: str,
) -> str:
    sanitized_original = sanitize_upload_filename(original_filename)
    return (
        f"{animal_id}_invivo2p_{session_token}_{upload_type}_{index}_"
        f"{sanitized_original}"
    )


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
        key=invivo2p_key(form_key, "attachment_reference_action"),
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


def save_general_invivo2p_attachments(
    *,
    page: Any,
    payload: Mapping[str, Any],
    attachment_values: GeneralNotesAttachmentValues,
) -> list[dict[str, str]]:
    animal_id = clean_string(payload.get(ANIMAL_ID_KEY))
    session_token = invivo2p_record_file_token(payload)
    if not session_token:
        raise ValueError("session_date or invivo2p_draft_id is required.")

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
        filename = invivo2p_upload_filename(
            animal_id=animal_id,
            session_token=session_token,
            upload_type=upload_type,
            index=index,
            original_filename=original_filename,
        )
        try:
            result = save_invivo2p_file_attachment(
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


def behavior_task_phase_choices(behavior_task_name: str) -> list[str]:
    if clean_string(behavior_task_name) == SEASIC_TASK_NAME:
        return [*SEASIC_BEHAVIOR_TASK_PHASE_OPTIONS, OTHER_CHOICE]

    return [*COMMON_BEHAVIOR_TASK_PHASE_OPTIONS, OTHER_CHOICE]


def render_session_details(
    *,
    options: dict[str, list[str]],
    form_key: str,
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}

    with st.expander("Session Details", expanded=True):
        session_date = render_session_date(
            form_key=form_key,
            value=parse_session_date(defaults.get(SESSION_DATE_KEY)),
        )
        session_id = st.text_input(
            "Session ID",
            key=invivo2p_key(form_key, "session_id"),
            value=string_default(defaults, SESSION_ID_KEY),
        )
        session_type = render_select_with_immediate_other(
            label="Session Type",
            options=options,
            options_key=SESSION_TYPE_OPTIONS_KEY,
            widget_key=invivo2p_key(form_key, "session_type"),
            other_prompt="New Session Type",
            value=string_default(defaults, SESSION_TYPE_KEY),
        )
        behavior_task_name = render_select_with_immediate_other(
            label="Behavior Task Name",
            options=options,
            options_key=BEHAVIOR_TASK_NAME_OPTIONS_KEY,
            widget_key=invivo2p_key(form_key, "behavior_task_name"),
            other_prompt="New Behavior Task Name",
            value=string_default(defaults, BEHAVIOR_TASK_NAME_KEY),
        )
        behavior_task_phase = render_select_with_immediate_other(
            label="Behavior Task Phase",
            options=options,
            options_key=BEHAVIOR_TASK_PHASE_OPTIONS_KEY,
            widget_key=invivo2p_key(form_key, "behavior_task_phase"),
            other_prompt="New Behavior Task Phase",
            value=string_default(defaults, BEHAVIOR_TASK_PHASE_KEY),
            choices=behavior_task_phase_choices(behavior_task_name),
        )
        imager = render_select_with_immediate_other(
            label="Imager",
            options=options,
            options_key=INVIVO2P_IMAGER_OPTIONS_KEY,
            widget_key=invivo2p_key(form_key, "imager"),
            other_prompt="New Imager",
            value=string_default(defaults, IMAGER_KEY),
        )
        start_time = render_session_time(
            "Start Time (HHMM)",
            invivo2p_key(form_key, "start_time"),
            value=parse_session_time(defaults.get(START_TIME_KEY)),
        )
        end_time = render_session_time(
            "End Time (HHMM)",
            invivo2p_key(form_key, "end_time"),
            value=parse_session_time(defaults.get(END_TIME_KEY)),
        )

    return {
        SESSION_DATE_KEY: session_date,
        SESSION_ID_KEY: session_id,
        SESSION_TYPE_KEY: session_type,
        BEHAVIOR_TASK_NAME_KEY: behavior_task_name,
        BEHAVIOR_TASK_PHASE_KEY: behavior_task_phase,
        IMAGER_KEY: imager,
        START_TIME_KEY: start_time,
        END_TIME_KEY: end_time,
    }


def render_metadata_row(label: str, value: object, suffix: str = "") -> str:
    if isinstance(value, list):
        display_value = ", ".join(str(item) for item in value)
    elif value in ("", None):
        display_value = "—"
    else:
        display_value = str(value)

    if display_value != "—" and suffix:
        display_value = f"{display_value}{suffix}"

    st.markdown(
        f"""
        <div style="display: grid; grid-template-columns: 180px 1fr; gap: 12px; margin: 2px 0;">
            <div style="color: #666;">{label}</div>
            <div><code>{display_value}</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return "" if display_value == "—" else display_value.removesuffix(suffix)


def render_metadata_section(
    title: str,
    rows: Sequence[tuple[str, str, str]],
    metadata: Mapping[str, object],
) -> dict[str, str]:
    st.markdown(f"##### {title}")

    values: dict[str, str] = {}
    for label, key_name, suffix in rows:
        raw_value = metadata.get(key_name, "")
        values[key_name] = render_metadata_row(label, raw_value, suffix)

    st.markdown("")
    return values


def render_imaging_settings(
    *,
    options: dict[str, list[str]],
    form_key: str,
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    defaults = defaults or {}

    xml_metadata = st.session_state.get(
        invivo2p_key(form_key, INVIVO2P_XML_METADATA_KEY),
        {},
    )
    if not isinstance(xml_metadata, Mapping):
        xml_metadata = {}

    metadata = {
        key: xml_metadata.get(key, defaults.get(key, ""))
        for key in (
            PRAIRIEVIEW_VERSION_KEY,
            NUM_CHANNELS_RECORDED_KEY,
            CHANNEL_NUMBERS_RECORDED_KEY,
            CHANNEL_NAMES_RECORDED_KEY,
            OBJECTIVE_KEY,
            OBJECTIVE_MAGNIFICATION_KEY,
            OBJECTIVE_NA_KEY,
            ZOOM_KEY,
            IMAGING_LASER_WAVELENGTH_NM_KEY,
            RESOLUTION_PIX_KEY,
            FOV_SIZE_UM_KEY,
            STAGE_X_KEY,
            STAGE_Y_KEY,
            Z_FOCUS_KEY,
            IMAGING_LASER_POWER_MW_KEY,
            PMT_GAIN_0_KEY,
            PMT_GAIN_1_KEY,
            NUM_PLANES_KEY,
            PLANE_RELATIVE_DEPTHS_KEY,
            FRAME_COUNT_TOTAL_KEY,
            DURATION_S_KEY,
            FRAME_RATE_HZ_KEY,
            VOLUME_RATE_HZ_KEY,
        )
    }

    with st.expander("Imaging System & Settings", expanded=True):
        invivo2p_system_id = render_select_with_immediate_other(
            label="2P System ID",
            options=options,
            options_key=INVIVO2P_SYSTEM_ID_OPTIONS_KEY,
            widget_key=invivo2p_key(form_key, "system_id"),
            other_prompt="New 2P System ID",
            value=string_default(defaults, INVIVO2P_SYSTEM_ID_KEY),
        )
        invivo2p_software_name = render_select_with_immediate_other(
            label="2P Software",
            options=options,
            options_key=INVIVO2P_SOFTWARE_NAME_OPTIONS_KEY,
            widget_key=invivo2p_key(form_key, "software_name"),
            other_prompt="New 2P Software",
            value=string_default(defaults, INVIVO2P_SOFTWARE_NAME_KEY),
        )
        behavior_rig = render_select_with_immediate_other(
            label="Behavior Rig",
            options=options,
            options_key=BEHAVIOR_RIG_OPTIONS_KEY,
            widget_key=invivo2p_key(form_key, "behavior_rig"),
            other_prompt="New Behavior Rig",
            value=string_default(defaults, BEHAVIOR_RIG_KEY),
        )

        st.divider()
        st.markdown("### PrairieView Metadata")

        metadata_values: dict[str, str] = {}

        metadata_values.update(
            render_metadata_section(
                "Software",
                (
                    ("PrairieView Version", PRAIRIEVIEW_VERSION_KEY, ""),
                ),
                metadata,
            )
        )

        metadata_values.update(
            render_metadata_section(
                "Objective",
                (
                    ("Name", OBJECTIVE_KEY, ""),
                    ("Magnification", OBJECTIVE_MAGNIFICATION_KEY, "×"),
                    ("Numerical Aperture", OBJECTIVE_NA_KEY, ""),
                ),
                metadata,
            )
        )

        metadata_values.update(
            render_metadata_section(
                "Imaging",
                (
                    ("Zoom", ZOOM_KEY, ""),
                    (
                        "Laser Wavelength",
                        IMAGING_LASER_WAVELENGTH_NM_KEY,
                        " nm",
                    ),
                    ("Laser Power", IMAGING_LASER_POWER_MW_KEY, " mW"),
                    ("FOV Size", FOV_SIZE_UM_KEY, " µm"),
                ),
                metadata,
            )
        )

        metadata_values.update(
            render_metadata_section(
                "Acquisition",
                (
                    ("Resolution", RESOLUTION_PIX_KEY, ""),
                    ("Frame Rate", FRAME_RATE_HZ_KEY, " Hz"),
                    ("Volume Rate", VOLUME_RATE_HZ_KEY, " Hz"),
                    ("Duration", DURATION_S_KEY, " s"),
                    ("Frame Count", FRAME_COUNT_TOTAL_KEY, ""),
                    ("Num Planes", NUM_PLANES_KEY, ""),
                    ("Plane Depths", PLANE_RELATIVE_DEPTHS_KEY, " µm"),
                ),
                metadata,
            )
        )

        metadata_values.update(
            render_metadata_section(
                "Channels",
                (
                    ("Number Recorded", NUM_CHANNELS_RECORDED_KEY, ""),
                    ("Channel Numbers", CHANNEL_NUMBERS_RECORDED_KEY, ""),
                    ("Channel Names", CHANNEL_NAMES_RECORDED_KEY, ""),
                ),
                metadata,
            )
        )

        metadata_values.update(
            render_metadata_section(
                "Stage",
                (
                    ("X", STAGE_X_KEY, ""),
                    ("Y", STAGE_Y_KEY, ""),
                    ("Z Focus", Z_FOCUS_KEY, ""),
                ),
                metadata,
            )
        )

        metadata_values.update(
            render_metadata_section(
                "PMTs",
                (
                    ("PMT 0 Gain", PMT_GAIN_0_KEY, ""),
                    ("PMT 1 Gain", PMT_GAIN_1_KEY, ""),
                ),
                metadata,
            )
        )

    return {
        INVIVO2P_SYSTEM_ID_KEY: invivo2p_system_id,
        INVIVO2P_SOFTWARE_NAME_KEY: invivo2p_software_name,
        BEHAVIOR_RIG_KEY: behavior_rig,
        **metadata_values,
    }

def render_channel_settings(
    *,
    options: dict[str, list[str]],
    form_key: str,
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    defaults = defaults or {}

    with st.expander("Channels & Constructs", expanded=True):
        channel = render_select_with_immediate_other(
            label="Channel",
            options=options,
            options_key=CHANNEL_OPTIONS_KEY,
            widget_key=invivo2p_key(form_key, "channel"),
            other_prompt="New Channel",
            value=string_default(defaults, CHANNEL_KEY),
        )

        green_construct = ""
        green_substrate = ""
        red_construct = ""
        red_substrate = ""

        if channel in ("Green", "Green + Red"):
            green_construct = render_select_with_immediate_other(
                label="Green Construct",
                options=options,
                options_key=GREEN_CONSTRUCT_OPTIONS_KEY,
                widget_key=invivo2p_key(form_key, "green_construct"),
                other_prompt="New Green Construct",
                value=string_default(defaults, GREEN_CONSTRUCT_KEY),
            )
            green_substrate = render_select_with_immediate_other(
                label="Green Channel Substrate",
                options=options,
                options_key=GREEN_CHANNEL_SUBSTRATE_OPTIONS_KEY,
                widget_key=invivo2p_key(form_key, "green_substrate"),
                other_prompt="New Green Channel Substrate",
                value=string_default(defaults, GREEN_CHANNEL_SUBSTRATE_KEY),
            )

        if channel in ("Red", "Green + Red"):
            red_construct = render_select_with_immediate_other(
                label="Red Construct",
                options=options,
                options_key=RED_CONSTRUCT_OPTIONS_KEY,
                widget_key=invivo2p_key(form_key, "red_construct"),
                other_prompt="New Red Construct",
                value=string_default(defaults, RED_CONSTRUCT_KEY),
            )
            red_substrate = render_select_with_immediate_other(
                label="Red Channel Substrate",
                options=options,
                options_key=RED_CHANNEL_SUBSTRATE_OPTIONS_KEY,
                widget_key=invivo2p_key(form_key, "red_substrate"),
                other_prompt="New Red Channel Substrate",
                value=string_default(defaults, RED_CHANNEL_SUBSTRATE_KEY),
            )

    return {
        CHANNEL_KEY: channel,
        GREEN_CONSTRUCT_KEY: green_construct,
        GREEN_CHANNEL_SUBSTRATE_KEY: green_substrate,
        RED_CONSTRUCT_KEY: red_construct,
        RED_CHANNEL_SUBSTRATE_KEY: red_substrate,
    }


def fov_plane_count_key(form_key: str, fov_index: int) -> str:
    return invivo2p_key(form_key, f"fov_{fov_index}_plane_count")


def increment_fov_count(form_key: str) -> None:
    count_key = invivo2p_count_key(form_key, INVIVO2P_FOV_COUNT_KEY)
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1

def decrement_fov_count(form_key: str) -> None:
    count_key = invivo2p_count_key(form_key, INVIVO2P_FOV_COUNT_KEY)
    current_count = st.session_state.get(count_key, 1)
    st.session_state[count_key] = max(1, current_count - 1)

def increment_plane_count(form_key: str, fov_index: int) -> None:
    count_key = fov_plane_count_key(form_key, fov_index)
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1


def decrement_plane_count(form_key: str, fov_index: int) -> None:
    count_key = fov_plane_count_key(form_key, fov_index)
    current_count = st.session_state.get(count_key, 1)
    st.session_state[count_key] = max(1, current_count - 1)


def render_planes(
    *,
    form_key: str,
    fov_index: int,
    values: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, object]]:
    count_key = fov_plane_count_key(form_key, fov_index)
    st.session_state.setdefault(count_key, max(1, len(values)))

    if st.button(
        "Add plane",
        key=invivo2p_key(form_key, f"fov_{fov_index}_add_plane"),
        use_container_width=True,
    ):
        increment_plane_count(form_key, fov_index)
        st.rerun()
    if st.button(
        "Remove last plane",
        key=invivo2p_key(form_key, f"fov_{fov_index}_remove_plane"),
        use_container_width=True,
    ):
        decrement_plane_count(form_key, fov_index)
        st.rerun()
    planes: list[dict[str, object]] = []
    for plane_index in range(1, st.session_state[count_key] + 1):
        defaults = values[plane_index - 1] if plane_index <= len(values) else {}
        prefix = invivo2p_key(
            form_key,
            f"fov_{fov_index}_plane_{plane_index}",
        )

        st.markdown(f"##### Plane {plane_index}")
        imaging_layer = render_select_with_immediate_other(
            label="Imaging Layer",
            options=normalize_options(st.session_state[CONFIG_STATE_KEY].get(OPTIONS_KEY)),
            options_key=IMAGING_LAYER_OPTIONS_KEY,
            widget_key=f"{prefix}_imaging_layer",
            other_prompt="New Imaging Layer",
            value=clean_string(defaults.get(IMAGING_LAYER_KEY)),
        )
        depth_um = st.number_input(
            "Depth (um)",
            min_value=0.0,
            value=number_default(defaults.get(DEPTH_UM_KEY)),
            step=1.0,
            key=f"{prefix}_depth_um",
        )

        planes.append(
            {
                PLANE_NUMBER_KEY: plane_index,
                IMAGING_LAYER_KEY: imaging_layer,
                DEPTH_UM_KEY: depth_um,
            }
        )

    return planes


def render_fovs(
    *,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
    form_key: str,
    values: Sequence[Mapping[str, Any]] = (),
) -> tuple[int, list[dict[str, object]]]:
    st.subheader("Fields of View")

    count_key = invivo2p_count_key(form_key, INVIVO2P_FOV_COUNT_KEY)
    st.session_state.setdefault(count_key, max(1, len(values)))

    if st.button(
        "Add FOV",
        key=invivo2p_key(form_key, "add_fov"),
        use_container_width=True,
    ):
        increment_fov_count(form_key)
        st.rerun()

    if st.button(
        "Remove last FOV",
        key=invivo2p_key(form_key, "remove_fov"),
        use_container_width=True,
    ):
        decrement_fov_count(form_key)
        st.rerun()

    fovs: list[dict[str, object]] = []

    for fov_index in range(1, st.session_state[count_key] + 1):
        defaults = values[fov_index - 1] if fov_index <= len(values) else {}
        plane_defaults = mapping_list_default(defaults.get(PLANES_KEY))

        with st.expander(
            f"FOV {fov_index}",
            expanded=fov_index == st.session_state[count_key],
        ):
            imaging_region = render_select_with_immediate_other(
                label="Imaging Region",
                options=options,
                options_key=IMAGING_REGION_OPTIONS_KEY,
                widget_key=invivo2p_key(form_key, f"fov_{fov_index}_region"),
                other_prompt="New Imaging Region",
                value=clean_string(defaults.get(IMAGING_REGION_KEY)),
            )
            hemisphere = st.selectbox(
                "Hemisphere",
                options=HEMISPHERE_OPTIONS,
                key=invivo2p_key(form_key, f"fov_{fov_index}_hemisphere"),
                index=selected_index(
                    HEMISPHERE_OPTIONS,
                    defaults.get(HEMISPHERE_KEY),
                ),
            )

            planes = render_planes(
                form_key=form_key,
                fov_index=fov_index,
                values=plane_defaults,
            )

            fov_notes = st.text_area(
                "FOV Notes",
                key=invivo2p_key(form_key, f"fov_{fov_index}_notes"),
                value=clean_string(defaults.get(FOV_NOTES_KEY)),
            )

            fovs.append(
                {
                    FOV_NUMBER_KEY: fov_index,
                    IMAGING_REGION_KEY: imaging_region,
                    HEMISPHERE_KEY: hemisphere,
                    NUM_PLANES_KEY: len(planes),
                    PLANES_KEY: planes,
                    FOV_NOTES_KEY: fov_notes,
                }
            )

    return len(fovs), fovs


def increment_stimulus_count(form_key: str) -> None:
    count_key = invivo2p_count_key(form_key, INVIVO2P_STIMULUS_COUNT_KEY)
    st.session_state[count_key] = st.session_state.get(count_key, 0) + 1


def render_sensory_stimuli(
    *,
    options: dict[str, list[str]],
    form_key: str,
    values: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, object]]:
    with st.expander("Sensory Stimuli", expanded=False):
        st.caption("Optional. Add entries only if sensory stimuli were used.")

        count_key = invivo2p_count_key(form_key, INVIVO2P_STIMULUS_COUNT_KEY)
        st.session_state.setdefault(count_key, len(values))

        if st.button(
            "Add sensory stimulus",
            key=invivo2p_key(form_key, "add_stimulus"),
            use_container_width=True,
        ):
            increment_stimulus_count(form_key)
            st.rerun()

        stimuli: list[dict[str, object]] = []
        for stimulus_index in range(1, st.session_state[count_key] + 1):
            defaults = (
                values[stimulus_index - 1]
                if stimulus_index <= len(values)
                else {}
            )
            prefix = invivo2p_key(form_key, f"stimulus_{stimulus_index}")

            st.markdown(f"#### Stimulus {stimulus_index}")
            stimulus_type = render_select_with_immediate_other(
                label="Sensory Stimulus Type",
                options=options,
                options_key=SENSORY_STIMULUS_TYPE_OPTIONS_KEY,
                widget_key=f"{prefix}_type",
                other_prompt="New Sensory Stimulus Type",
                value=clean_string(defaults.get(SENSORY_STIMULUS_TYPE_KEY)),
            )
            duration_ms = st.number_input(
                "Duration (ms)",
                min_value=0.0,
                value=number_default(defaults.get(STIMULUS_DURATION_MS_KEY)),
                step=1.0,
                key=f"{prefix}_duration_ms",
            )
            repetition = st.text_input(
                "Repetition",
                key=f"{prefix}_repetition",
                value=clean_string(defaults.get(STIMULUS_REPETITION_KEY)),
            )
            frequency_hz = st.number_input(
                "Frequency (Hz)",
                min_value=0.0,
                value=number_default(defaults.get(STIMULUS_FREQUENCY_HZ_KEY)),
                step=1.0,
                key=f"{prefix}_frequency_hz",
            )
            stimulus_notes = st.text_area(
                "Stimulus Notes",
                key=f"{prefix}_notes",
                value=clean_string(defaults.get(STIMULUS_NOTES_KEY)),
            )

            stimuli.append(
                {
                    SENSORY_STIMULUS_TYPE_KEY: stimulus_type,
                    STIMULUS_DURATION_MS_KEY: duration_ms,
                    STIMULUS_REPETITION_KEY: repetition,
                    STIMULUS_FREQUENCY_HZ_KEY: frequency_hz,
                    STIMULUS_NOTES_KEY: stimulus_notes,
                }
            )

    return stimuli


def increment_camera_count(form_key: str) -> None:
    count_key = invivo2p_count_key(form_key, INVIVO2P_CAMERA_COUNT_KEY)
    st.session_state[count_key] = st.session_state.get(count_key, 0) + 1


def render_cameras(
    *,
    options: dict[str, list[str]],
    form_key: str,
    values: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, object]]:
    with st.expander("Behavior Cameras", expanded=False):
        st.caption("Optional. Add entries only if cameras were used.")

        count_key = invivo2p_count_key(form_key, INVIVO2P_CAMERA_COUNT_KEY)
        st.session_state.setdefault(count_key, len(values))

        if st.button(
            "Add camera",
            key=invivo2p_key(form_key, "add_camera"),
            use_container_width=True,
        ):
            increment_camera_count(form_key)
            st.rerun()

        cameras: list[dict[str, object]] = []
        for camera_index in range(1, st.session_state[count_key] + 1):
            defaults = (
                values[camera_index - 1] if camera_index <= len(values) else {}
            )
            prefix = invivo2p_key(form_key, f"camera_{camera_index}")

            st.markdown(f"#### Camera {camera_index}")
            camera_model = render_select_with_immediate_other(
                label="Camera Model",
                options=options,
                options_key=CAMERA_MODEL_OPTIONS_KEY,
                widget_key=f"{prefix}_model",
                other_prompt="New Camera Model",
                value=clean_string(defaults.get(CAMERA_MODEL_KEY)),
            )
            camera_acq_software = render_select_with_immediate_other(
                label="Camera Acquisition Software",
                options=options,
                options_key=CAMERA_ACQ_SOFTWARE_OPTIONS_KEY,
                widget_key=f"{prefix}_acq_software",
                other_prompt="New Camera Acquisition Software",
                value=clean_string(defaults.get(CAMERA_ACQ_SOFTWARE_KEY)),
            )
            camera_view = render_select_with_immediate_other(
                label="Camera View",
                options=options,
                options_key=CAMERA_VIEW_OPTIONS_KEY,
                widget_key=f"{prefix}_view",
                other_prompt="New Camera View",
                value=clean_string(defaults.get(CAMERA_VIEW_KEY)),
            )
            camera_frame_rate_hz = st.number_input(
                "Camera Frame Rate (Hz)",
                min_value=0.0,
                value=number_default(defaults.get(CAMERA_FRAME_RATE_HZ_KEY)),
                step=1.0,
                key=f"{prefix}_frame_rate_hz",
            )
            camera_notes = st.text_area(
                "Camera Notes",
                key=f"{prefix}_notes",
                value=clean_string(defaults.get(CAMERA_NOTES_KEY)),
            )

            cameras.append(
                {
                    CAMERA_NUMBER_KEY: camera_index,
                    CAMERA_MODEL_KEY: camera_model,
                    CAMERA_VIEW_KEY: camera_view,
                    CAMERA_ACQ_SOFTWARE_KEY: camera_acq_software,
                    CAMERA_FRAME_RATE_HZ_KEY: camera_frame_rate_hz,
                    CAMERA_NOTES_KEY: camera_notes,
                }
            )

    return cameras


def render_general_notes_attachments(
    *,
    form_key: str,
    defaults: Mapping[str, Any] | None = None,
) -> GeneralNotesAttachmentValues:
    defaults = defaults or {}

    with st.expander("General Notes & Attachments", expanded=True):
        general_notes = st.text_area(
            "General Notes",
            key=invivo2p_key(form_key, "general_notes"),
            value=clean_string(defaults.get(GENERAL_NOTES_KEY)),
        )
        note_uploads = st.file_uploader(
            "Note Upload",
            accept_multiple_files=True,
            key=invivo2p_key(form_key, "note_upload"),
        )
        photo_uploads = st.file_uploader(
            "Photo Upload",
            type=["png", "jpg", "jpeg", "tif", "tiff"],
            accept_multiple_files=True,
            key=invivo2p_key(form_key, "photo_upload"),
        )

        # Keeping taken_photos empty for now keeps the first invivo2p page
        # simpler. We can add camera_input later if you want parity with surgery.
        taken_photos: list[Any] = []

    return {
        "general_notes": general_notes,
        "note_uploads": list(note_uploads or []),
        "photo_uploads": list(photo_uploads or []),
        "taken_photos": taken_photos,
    }


def render_raw_data_paths(
    *,
    form_key: str,
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    defaults = defaults or {}

    with st.expander("Raw Data & Metadata Paths", expanded=False):
        raw_2p_imaging_data_path = st.text_input(
            "Raw 2P Imaging Data Path",
            key=invivo2p_key(form_key, "raw_2p_imaging_data_path"),
            value=string_default(defaults, RAW_2P_IMAGING_DATA_PATH_KEY),
        )
        raw_2p_imaging_metadata_path = st.text_input(
            "Raw 2P Imaging Metadata Path",
            key=invivo2p_key(form_key, "raw_2p_imaging_metadata_path"),
            value=string_default(defaults, RAW_2P_IMAGING_METADATA_PATH_KEY),
        )
        raw_2p_sync_data_path = st.text_input(
            "Raw 2P Sync Data Path",
            key=invivo2p_key(form_key, "raw_2p_sync_data_path"),
            value=string_default(defaults, RAW_2P_SYNC_DATA_PATH_KEY),
        )
        raw_2p_sync_metadata_path = st.text_input(
            "Raw 2P Sync Metadata Path",
            key=invivo2p_key(form_key, "raw_2p_sync_metadata_path"),
            value=string_default(defaults, RAW_2P_SYNC_METADATA_PATH_KEY),
        )

    return {
        RAW_2P_IMAGING_DATA_PATH_KEY: raw_2p_imaging_data_path,
        RAW_2P_IMAGING_METADATA_PATH_KEY: raw_2p_imaging_metadata_path,
        RAW_2P_SYNC_DATA_PATH_KEY: raw_2p_sync_data_path,
        RAW_2P_SYNC_METADATA_PATH_KEY: raw_2p_sync_metadata_path,
    }


def render_prairieview_xml_import(*, form_key: str) -> dict[str, Any]:
    def metadata_value(metadata: Mapping[str, Any], key: str) -> object:
        value = metadata.get(key, "")
        return "" if value is None else value

    def metadata_text(metadata: Mapping[str, Any], key: str) -> str:
        value = metadata_value(metadata, key)
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return clean_string(value)

    def prairieview_to_muronto_metadata(
        metadata: Mapping[str, Any],
    ) -> dict[str, object]:
        return {
            PRAIRIEVIEW_VERSION_KEY: metadata_value(metadata, "pv_version"),
            NUM_CHANNELS_RECORDED_KEY: metadata_value(
                metadata,
                "num_channels_recorded",
            ),
            CHANNEL_NUMBERS_RECORDED_KEY: metadata_text(
                metadata,
                "channel_numbers_recorded",
            ),
            CHANNEL_NAMES_RECORDED_KEY: metadata_text(
                metadata,
                "channel_names_recorded",
            ),
            OBJECTIVE_KEY: metadata_value(metadata, "objective_name"),
            OBJECTIVE_MAGNIFICATION_KEY: metadata_value(
                metadata,
                "objective_magnification",
            ),
            OBJECTIVE_NA_KEY: metadata_value(metadata, "objective_na"),
            ZOOM_KEY: metadata_value(metadata, "optical_zoom"),
            IMAGING_LASER_WAVELENGTH_NM_KEY: metadata_value(
                metadata,
                "laser_wavelength_nm",
            ),
            RESOLUTION_PIX_KEY: metadata_value(
                metadata,
                "resolution_pix",
            ),
            FOV_SIZE_UM_KEY: metadata_value(
                metadata,
                "fov_size_um",
            ),
            STAGE_X_KEY: metadata_value(metadata, "stage_x"),
            STAGE_Y_KEY: metadata_value(metadata, "stage_y"),
            Z_FOCUS_KEY: metadata_value(metadata, "z_focus"),
            IMAGING_LASER_POWER_MW_KEY: metadata_value(
                metadata,
                "laser_power_0",
            ),
            PMT_GAIN_0_KEY: metadata_value(metadata, "pmt_gain_0"),
            PMT_GAIN_1_KEY: metadata_value(metadata, "pmt_gain_1"),
            NUM_PLANES_KEY: metadata_value(metadata, "num_planes_inferred"),
            PLANE_RELATIVE_DEPTHS_KEY: metadata_text(
                metadata,
                "plane_relative_depths",
            ),
            FRAME_COUNT_TOTAL_KEY: metadata_value(
                metadata,
                "frame_count_total",
            ),
            DURATION_S_KEY: metadata_value(metadata, "duration_s"),
            FRAME_RATE_HZ_KEY: metadata_value(
                metadata,
                "frame_rate_actual_hz",
            ),
            VOLUME_RATE_HZ_KEY: metadata_value(
                metadata,
                "volume_rate_hz",
            ),
        }

    with st.expander("PrairieView XML Metadata Import", expanded=False):
        uploaded_xml = st.file_uploader(
            "PrairieView XML file",
            type=["xml"],
            key=invivo2p_key(form_key, "prairieview_xml_upload"),
        )

        if uploaded_xml is None:
            return {}

        try:
            parsed = parse_prairieview_xml_bytes(uploaded_xml.getvalue())
        except Exception as exc:
            st.error(f"Unable to parse PrairieView XML: {exc}")
            return {}

        metadata = parsed.get("metadata", {})
        if not isinstance(metadata, Mapping):
            st.error("Parsed PrairieView XML did not contain metadata.")
            return {}

        muronto_metadata = prairieview_to_muronto_metadata(metadata)

        st.success("Parsed PrairieView XML.")

        with st.expander("Preview mapped XML metadata", expanded=True):
            st.json(muronto_metadata)

        if st.button(
            "Apply XML metadata to record",
            key=invivo2p_key(form_key, "apply_xml_metadata"),
            use_container_width=True,
        ):
            st.session_state[
                invivo2p_key(form_key, INVIVO2P_XML_METADATA_KEY)
            ] = muronto_metadata
            st.rerun()

        return muronto_metadata


def render_invivo2p_form(
    *,
    notebook: Any,
    config: dict[str, Any],
    project: dict[str, str],
    investigator: str,
    selected_subject: SubjectRecord,
    existing_record: Invivo2pRecord | None = None,
    copied_payload: dict[str, Any] | None = None,
    copy_source_key: str = "",
) -> None:
    subject_payload = selected_subject.payload

    payload_defaults = {}
    if existing_record is not None:
        payload_defaults = existing_record.payload
    elif copied_payload is not None:
        payload_defaults = copied_payload

    is_copying = copied_payload is not None and existing_record is None

    form_key = INVIVO2P_CREATE_FORM_KEY
    if existing_record is not None:
        form_key = (
            f"invivo2p_edit_{invivo2p_record_widget_key(existing_record)}"
        )
    elif copied_payload is not None:
        form_key = f"invivo2p_copy_{copy_source_key or 'source'}"

    if is_copying:
        payload_defaults = dict(payload_defaults)
        payload_defaults[SESSION_DATE_KEY] = ""
        payload_defaults[SESSION_ID_KEY] = ""
        payload_defaults[INVIVO2P_DRAFT_ID_KEY] = ""
        payload_defaults[ATTACHMENTS_KEY] = []
        payload_defaults[RAW_2P_IMAGING_DATA_PATH_KEY] = ""
        payload_defaults[RAW_2P_IMAGING_METADATA_PATH_KEY] = ""
        payload_defaults[RAW_2P_SYNC_DATA_PATH_KEY] = ""
        payload_defaults[RAW_2P_SYNC_METADATA_PATH_KEY] = ""
    
    xml_metadata_state_key = invivo2p_key(form_key, INVIVO2P_XML_METADATA_KEY)
    if xml_metadata_state_key not in st.session_state:
        st.session_state[xml_metadata_state_key] = {
            key: payload_defaults.get(key, "")
            for key in (
                PRAIRIEVIEW_VERSION_KEY,
                NUM_CHANNELS_RECORDED_KEY,
                CHANNEL_NUMBERS_RECORDED_KEY,
                CHANNEL_NAMES_RECORDED_KEY,
                OBJECTIVE_KEY,
                OBJECTIVE_MAGNIFICATION_KEY,
                OBJECTIVE_NA_KEY,
                ZOOM_KEY,
                IMAGING_LASER_WAVELENGTH_NM_KEY,
                RESOLUTION_PIX_KEY,
                FOV_SIZE_UM_KEY,
                STAGE_X_KEY,
                STAGE_Y_KEY,
                Z_FOCUS_KEY,
                IMAGING_LASER_POWER_MW_KEY,
                PMT_GAIN_0_KEY,
                PMT_GAIN_1_KEY,
                NUM_PLANES_KEY,
                PLANE_RELATIVE_DEPTHS_KEY,
                FRAME_COUNT_TOTAL_KEY,
                DURATION_S_KEY,
                FRAME_RATE_HZ_KEY,
                VOLUME_RATE_HZ_KEY,
            )
        }

    existing_references = existing_attachment_references(payload_defaults)
    options = normalize_options(config.get(OPTIONS_KEY))

    session_values = render_session_details(
        options=options,
        form_key=form_key,
        defaults=payload_defaults,
    )

    render_prairieview_xml_import(form_key=form_key)

    imaging_values = render_imaging_settings(
        options=options,
        form_key=form_key,
        defaults=payload_defaults,
    )
    channel_values = render_channel_settings(
        options=options,
        form_key=form_key,
        defaults=payload_defaults,
    )
    num_fovs, fovs = render_fovs(
        options=options,
        notebook=notebook,
        config=config,
        form_key=form_key,
        values=mapping_list_default(payload_defaults.get(FOVS_KEY)),
    )
    sensory_stimuli = render_sensory_stimuli(
        options=options,
        form_key=form_key,
        values=mapping_list_default(payload_defaults.get(SENSORY_STIMULI_KEY)),
    )
    cameras = render_cameras(
        options=options,
        form_key=form_key,
        values=mapping_list_default(payload_defaults.get(CAMERAS_KEY)),
    )
    raw_data_paths = render_raw_data_paths(
        form_key=form_key,
        defaults=payload_defaults,
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
        "Save invivo2p record",
        type="primary",
        use_container_width=True,
        key=invivo2p_key(form_key, "submit"),
    )
    if not submitted:
        return

    draft_id = invivo2p_draft_id(
        form_key=form_key,
        payload_defaults=payload_defaults,
    )

    def build_payload(
        attachments: list[dict[str, str]],
        *,
        allow_incomplete: bool,
    ) -> dict[str, Any]:
        return build_invivo2p_payload(
            project_id=project[PROJECT_ID_KEY],
            investigator=investigator,
            animal_id=subject_payload.get(ANIMAL_ID_KEY, ""),
            ear_tag=subject_payload.get(EAR_TAG_KEY, ""),
            session_date=session_values[SESSION_DATE_KEY],
            session_id=clean_string(session_values[SESSION_ID_KEY]),
            session_type=clean_string(session_values[SESSION_TYPE_KEY]),
            behavior_task_name=clean_string(
                session_values[BEHAVIOR_TASK_NAME_KEY]
            ),
            behavior_task_phase=clean_string(
                session_values[BEHAVIOR_TASK_PHASE_KEY]
            ),
            imager=clean_string(session_values[IMAGER_KEY]),
            start_time=session_values[START_TIME_KEY],
            end_time=session_values[END_TIME_KEY],
            invivo2p_system_id=clean_string(
                imaging_values[INVIVO2P_SYSTEM_ID_KEY]
            ),
            invivo2p_software_name=clean_string(
                imaging_values[INVIVO2P_SOFTWARE_NAME_KEY]
            ),
            behavior_rig=clean_string(imaging_values[BEHAVIOR_RIG_KEY]),
            channel=clean_string(channel_values[CHANNEL_KEY]),
            xml_metadata_values=st.session_state.get(
                invivo2p_key(form_key, INVIVO2P_XML_METADATA_KEY),
                imaging_values,
            ),
            green_construct=clean_string(channel_values[GREEN_CONSTRUCT_KEY]),
            red_construct=clean_string(channel_values[RED_CONSTRUCT_KEY]),
            green_channel_substrate=clean_string(
                channel_values[GREEN_CHANNEL_SUBSTRATE_KEY]
            ),
            red_channel_substrate=clean_string(
                channel_values[RED_CHANNEL_SUBSTRATE_KEY]
            ),
            num_fovs=num_fovs,
            fovs=fovs,
            sensory_stimuli=sensory_stimuli,
            cameras=cameras,
            raw_2p_imaging_data_path=raw_data_paths[
                RAW_2P_IMAGING_DATA_PATH_KEY
            ],
            raw_2p_imaging_metadata_path=raw_data_paths[
                RAW_2P_IMAGING_METADATA_PATH_KEY
            ],
            raw_2p_sync_data_path=raw_data_paths[RAW_2P_SYNC_DATA_PATH_KEY],
            raw_2p_sync_metadata_path=raw_data_paths[
                RAW_2P_SYNC_METADATA_PATH_KEY
            ],
            general_notes=general_attachment_values["general_notes"],
            attachments=attachments,
            allow_incomplete=allow_incomplete,
            draft_id=draft_id if allow_incomplete else "",
        )
    

    def build_payload_for_save(
        attachments: list[dict[str, str]],
    ) -> tuple[dict[str, Any], list[str]]:
        try:
            return (
                build_payload(
                    attachments,
                    allow_incomplete=False,
                ),
                [],
            )
        except Invivo2pValidationError:
            incomplete_payload = build_payload(
                attachments,
                allow_incomplete=True,
            )
            validation_errors = [
                error
                for error in incomplete_payload.get(
                    INVIVO2P_VALIDATION_ERRORS_KEY,
                    [],
                )
                if isinstance(error, str) and error
            ]
            return incomplete_payload, validation_errors

    payload, validation_errors = build_payload_for_save([])

    try:
        has_uploads = has_new_attachment_uploads(general_attachment_values)

        attachment_references = save_general_invivo2p_attachments(
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

        payload, validation_errors = build_payload_for_save(
            resolved_attachment_references
        )
    except ValueError as exc:
        st.error(f"Unable to upload invivo2p attachment: {exc}")
        return

    is_incomplete = (
        clean_string(payload.get(INVIVO2P_STATUS_KEY))
        == INVIVO2P_STATUS_INCOMPLETE
    )

    try:
        result = save_invivo2p_attachment(
            selected_subject.page,
            payload,
            existing_entry=(
                existing_record.attachment_entry if existing_record else None
            ),
        )
    except ApiError as exc:
        st.error(f"Unable to save the invivo2p record: {exc}")
        return
    except ValueError as exc:
        st.error(str(exc))
        return

    try:
        save_reusable_invivo2p_options(
            notebook=notebook,
            config=config,
            payload=payload,
        )
    except ApiError as exc:
        st.warning(
            "Saved the invivo2p record, but could not save reusable "
            f"invivo2p options to muronto_config: {exc}"
        )

    action = "Created" if result.created else "Updated"
    if is_incomplete:
        st.warning(
            "Saved an incomplete invivo2p record. Return to Edit existing "
            "invivo2p record to complete it."
        )
        for error in validation_errors:
            st.caption(error)

    st.success(f"{action} invivo2p record for `{payload[ANIMAL_ID_KEY]}`.")
    with st.expander("Invivo2p JSON", expanded=True):
        st.json(payload)


def main() -> None:
    context = render_project_context("In Vivo 2P")
    if context is None:
        return

    notebook = st.session_state.get(SELECTED_NOTEBOOK_STATE_KEY)
    _user, config, project = context
    if notebook is None or not isinstance(config, dict):
        st.warning("Select a notebook and complete muronto_config first.")
        st.page_link("Project.py", label="Open Project")
        return

    investigator = investigator_for_user(config, _user.email)

    st.subheader("In Vivo 2P")
    st.write(f"Project ID: {project[PROJECT_ID_KEY]}")
    st.write(f"Investigator: {investigator}")

    edit_existing = st.toggle(
        "Edit existing invivo2p record",
        key=INVIVO2P_EDIT_MODE_KEY,
    )

    copy_existing = st.toggle(
        "Copy values from existing invivo2p record",
        key=INVIVO2P_COPY_MODE_KEY,
        disabled=edit_existing,
    )

    if edit_existing and copy_existing:
        copy_existing = False

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
            key="invivo2p_subject",
        )
        selected_subject = subject_records[selected_subject_index]
        render_selected_subject(selected_subject)

    selected_invivo2p_record: Invivo2pRecord | None = None
    copied_invivo2p_payload: dict[str, Any] | None = None
    copy_source_key = ""

    if edit_existing:
        invivo2p_records = load_invivo2p_records(selected_subject.page)
        if invivo2p_records is None:
            return
        if not invivo2p_records:
            st.info(
                "No invivo2p JSON records were found on the selected subject."
            )
            return

        selected_invivo2p_index = st.selectbox(
            "Invivo2p Record",
            options=list(range(len(invivo2p_records))),
            format_func=lambda index: invivo2p_record_label(
                invivo2p_records[index]
            ),
            key=INVIVO2P_SELECTED_RECORD_KEY,
        )
        selected_invivo2p_record = invivo2p_records[selected_invivo2p_index]

    elif copy_existing:
        all_invivo2p_records = load_all_invivo2p_records(subject_records)
        if all_invivo2p_records is None:
            return
        if not all_invivo2p_records:
            st.info("No invivo2p JSON records were found in any subject.")
            return

        selected_copy_index = st.selectbox(
            "Source Invivo2p Record to Copy",
            options=list(range(len(all_invivo2p_records))),
            format_func=lambda index: subject_invivo2p_record_label(
                all_invivo2p_records[index]
            ),
            key=INVIVO2P_COPY_SOURCE_RECORD_KEY,
        )

        st.info(
            "The selected source invivo2p record will pre-fill the form. "
            "Saving will create a new invivo2p record for the destination subject."
        )

        copy_source_subject, copy_source_record = all_invivo2p_records[
            selected_copy_index
        ]
        copied_invivo2p_payload = copy_source_record.payload
        copy_source_key = (
            f"{subject_label(copy_source_subject)}_"
            f"{invivo2p_record_widget_key(copy_source_record)}"
        )

    render_invivo2p_form(
        notebook=notebook,
        config=config,
        project=project,
        investigator=investigator,
        selected_subject=selected_subject,
        existing_record=selected_invivo2p_record,
        copied_payload=copied_invivo2p_payload,
        copy_source_key=copy_source_key,
    )


if __name__ == "__main__":
    main()