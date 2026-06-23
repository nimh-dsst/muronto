"""In Vivo 2P Imaging record validation and payload helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import date, time
from typing import Any, Final

from muronto_app.config import (
    BEHAVIOR_RIG_OPTIONS_KEY,
    BEHAVIOR_TASK_NAME_OPTIONS_KEY,
    BEHAVIOR_TASK_PHASE_OPTIONS_KEY,
    CAMERA_ACQ_SOFTWARE_OPTIONS_KEY,
    CAMERA_MODEL_OPTIONS_KEY,
    CHANNEL_OPTIONS_KEY,
    GREEN_CHANNEL_SUBSTRATE_OPTIONS_KEY,
    GREEN_CONSTRUCT_OPTIONS_KEY,
    IMAGING_LAYER_OPTIONS_KEY,
    IMAGING_REGION_OPTIONS_KEY,
    INVESTIGATOR_KEY,
    INVIVO2P_IMAGER_OPTIONS_KEY,
    INVIVO2P_SOFTWARE_NAME_OPTIONS_KEY,
    INVIVO2P_SYSTEM_ID_OPTIONS_KEY,
    OBJECTIVE_OPTIONS_KEY,
    OPTIONS_KEY,
    PROJECT_ID_KEY,
    RED_CHANNEL_SUBSTRATE_OPTIONS_KEY,
    RED_CONSTRUCT_OPTIONS_KEY,
    SENSORY_STIMULUS_TYPE_OPTIONS_KEY,
    SESSION_TYPE_OPTIONS_KEY,
    add_option,
    clean_string,
    normalize_options,
)
from muronto_app.subject import (
    ANIMAL_ID_KEY,
    ANIMAL_ID_LABEL,
    EAR_TAG_KEY,
    EAR_TAG_LABEL,
)

INVIVO2P_ATTACHMENT_CAPTION: Final[str] = "muronto_invivo2p"
INVIVO2P_FILE_ATTACHMENT_CAPTION: Final[str] = "muronto_invivo2p_attachment"

INVIVO2P_STATUS_KEY: Final[str] = "invivo2p_status"
INVIVO2P_STATUS_COMPLETE: Final[str] = "complete"
INVIVO2P_STATUS_INCOMPLETE: Final[str] = "incomplete"
INVIVO2P_VALIDATION_ERRORS_KEY: Final[str] = "validation_errors"
INVIVO2P_DRAFT_ID_KEY: Final[str] = "invivo2p_draft_id"

SESSION_DATE_KEY: Final[str] = "session_date"
SESSION_ID_KEY: Final[str] = "session_id"
SESSION_TYPE_KEY: Final[str] = "session_type"
BEHAVIOR_TASK_NAME_KEY: Final[str] = "behavior_task_name"
BEHAVIOR_TASK_PHASE_KEY: Final[str] = "behavior_task_phase"

IMAGER_KEY: Final[str] = "imager"
START_TIME_KEY: Final[str] = "start_time"
END_TIME_KEY: Final[str] = "end_time"

INVIVO2P_SYSTEM_ID_KEY: Final[str] = "invivo2p_system_id"
INVIVO2P_SOFTWARE_NAME_KEY: Final[str] = "invivo2p_software_name"
BEHAVIOR_RIG_KEY: Final[str] = "behavior_rig"

OBJECTIVE_KEY: Final[str] = "objective"

IMAGING_LASER_WAVELENGTH_NM_KEY: Final[str] = (
    "imaging_laser_wavelength_nm"
)
IMAGING_LASER_POWER_MW_KEY: Final[str] = "imaging_laser_power_mw"

WF_OPTO_WAVELENGTH_NM_KEY: Final[str] = "wf_opto_wavelength_nm"
WF_OPTO_POWER_MW_KEY: Final[str] = "wf_opto_power_mw"
WF_OPTO_MODE_KEY: Final[str] = "wf_opto_mode"

SLM_OPTO_WAVELENGTH_NM_KEY: Final[str] = "slm_opto_wavelength_nm"
SLM_OPTO_POWER_MW_KEY: Final[str] = "slm_opto_power_mw"
SLM_OPTO_MODE_KEY: Final[str] = "slm_opto_mode"

FRAME_RATE_HZ_KEY: Final[str] = "frame_rate_hz"
ZOOM_KEY: Final[str] = "zoom"
RESOLUTION_PIX_KEY: Final[str] = "resolution_pix"
FOV_SIZE_UM_KEY: Final[str] = "fov_size_um"

SENSORY_STIMULI_KEY: Final[str] = "sensory_stimuli"
SENSORY_STIMULUS_TYPE_KEY: Final[str] = "sensory_stimulus_type"
STIMULUS_DURATION_MS_KEY: Final[str] = "stimulus_duration_ms"
STIMULUS_REPETITION_KEY: Final[str] = "stimulus_repetition"
STIMULUS_FREQUENCY_HZ_KEY: Final[str] = "stimulus_frequency_hz"
STIMULUS_NOTES_KEY: Final[str] = "stimulus_notes"

CAMERAS_KEY: Final[str] = "cameras"
CAMERA_NUMBER_KEY: Final[str] = "camera_number"
CAMERA_MODEL_KEY: Final[str] = "camera_model"
CAMERA_ACQ_SOFTWARE_KEY: Final[str] = "camera_acq_software"
CAMERA_FRAME_RATE_HZ_KEY: Final[str] = "camera_frame_rate_hz"
CAMERA_NOTES_KEY: Final[str] = "camera_notes"

CHANNEL_KEY: Final[str] = "channel"
GREEN_CONSTRUCT_KEY: Final[str] = "green_construct"
RED_CONSTRUCT_KEY: Final[str] = "red_construct"
GREEN_CHANNEL_SUBSTRATE_KEY: Final[str] = "green_channel_substrate"
RED_CHANNEL_SUBSTRATE_KEY: Final[str] = "red_channel_substrate"

NUM_FOVS_KEY: Final[str] = "num_fovs"

FOVS_KEY: Final[str] = "fovs"
FOV_NUMBER_KEY: Final[str] = "fov_number"
IMAGING_REGION_KEY: Final[str] = "imaging_region"
HEMISPHERE_KEY: Final[str] = "hemisphere"
NUM_PLANES_KEY: Final[str] = "num_planes"
PLANES_KEY: Final[str] = "planes"
FOV_NOTES_KEY: Final[str] = "fov_notes"

PLANE_NUMBER_KEY: Final[str] = "plane_number"
IMAGING_LAYER_KEY: Final[str] = "imaging_layer"
DEPTH_UM_KEY: Final[str] = "depth_um"

GENERAL_NOTES_KEY: Final[str] = "notes_general"

ATTACHMENTS_KEY: Final[str] = "attachments"
UPLOAD_TYPE_KEY: Final[str] = "upload_type"
ENTRY_ID_KEY: Final[str] = "entry_id"
FILENAME_KEY: Final[str] = "filename"
CAPTION_KEY: Final[str] = "caption"
MIME_TYPE_KEY: Final[str] = "mime_type"

NOTE_UPLOAD_TYPE: Final[str] = "note_upload"
PHOTO_UPLOAD_TYPE: Final[str] = "photo_upload"
TAKEN_PHOTO_UPLOAD_TYPE: Final[str] = "taken_photo"

INVIVO2P_FILE_UPLOAD_TYPES: Final[tuple[str, ...]] = (
    NOTE_UPLOAD_TYPE,
    PHOTO_UPLOAD_TYPE,
    TAKEN_PHOTO_UPLOAD_TYPE,
)

RAW_2P_IMAGING_DATA_PATH_KEY: Final[str] = "raw_2p_imaging_data_path"
RAW_2P_IMAGING_METADATA_PATH_KEY: Final[str] = "raw_2p_imaging_metadata_path"
RAW_2P_SYNC_DATA_PATH_KEY: Final[str] = "raw_2p_sync_data_path"
RAW_2P_SYNC_METADATA_PATH_KEY: Final[str] = "raw_2p_sync_metadata_path"

INVIVO2P_SESSION_TYPE_OPTIONS: Final[tuple[str, ...]] = (
    "2P Imaging",
    "2P Imaging + WF Opto",
    "2P Imaging + SLM Opto",
)

CHANNEL_OPTIONS: Final[tuple[str, ...]] = (
    "Green",
    "Red",
    "Green + Red",
)

HEMISPHERE_OPTIONS: Final[tuple[str, ...]] = ("LH", "RH")

INVIVO2P_TIME_PATTERN_TEXT: Final[str] = r"(?:[01]\d|2[0-3])[0-5]\d"
INVIVO2P_TIME_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^{INVIVO2P_TIME_PATTERN_TEXT}$"
)

WF_OPTO_MODE_OPTIONS: Final[tuple[str, ...]] = (
    "Continuous",
    "Pulsed",
)

SLM_OPTO_MODE_OPTIONS: Final[tuple[str, ...]] = (
    "Single Target",
    "Multi Target",
    "Sequential",
)


class Invivo2pValidationError(ValueError):
    """Raised when invivo2p form values do not make a valid payload."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def format_session_date(value: date) -> str:
    """Return a session date as ``YYYYMMDD``."""
    return value.strftime("%Y%m%d")


def format_session_time(value: time) -> str:
    """Return a session time as zero-padded ``HHMM``."""
    return value.strftime("%H%M")


def format_session_time_display(value: time) -> str:
    """Return a session time for display as ``HH:MM AM/PM``."""
    return value.strftime("%I:%M %p").lstrip("0")


def invivo2p_json_filename(animal_id: str, session_date: str) -> str:
    """Return the stable JSON filename for an invivo2p attachment."""
    return f"{animal_id}_invivo2p_{session_date}.json"


def invivo2p_record_file_token(payload: Mapping[str, Any]) -> str:
    """Return the dated or draft token used in invivo2p attachment filenames."""
    session_date = clean_string(payload.get(SESSION_DATE_KEY))
    if session_date:
        return session_date

    draft_id = clean_string(payload.get(INVIVO2P_DRAFT_ID_KEY))
    if draft_id:
        return f"incomplete_{draft_id}"

    return ""


def _validate_required(
    *,
    field_name: str,
    value: str,
    errors: list[str],
) -> None:
    if not value:
        errors.append(f"{field_name} is required.")


def _validate_non_negative_number(
    *,
    field_name: str,
    value: object,
    errors: list[str],
    allow_incomplete: bool = False,
) -> float | None:
    if value is None:
        errors.append(f"{field_name} is required.")
        return None if allow_incomplete else 0.0
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{field_name} must be a number.")
        return None if allow_incomplete else 0.0

    numeric_value = float(value)
    if numeric_value < 0:
        errors.append(f"{field_name} must be non-negative.")
    return numeric_value


def _validate_optional_non_negative_number(
    *,
    field_name: str,
    value: object,
    errors: list[str],
) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{field_name} must be a number.")
        return 0.0

    numeric_value = float(value)
    if numeric_value < 0:
        errors.append(f"{field_name} must be non-negative.")
    return numeric_value


def _validate_positive_integer(
    *,
    field_name: str,
    value: object,
    errors: list[str],
    allow_incomplete: bool = False,
) -> int | None:
    if value is None:
        errors.append(f"{field_name} is required.")
        return None if allow_incomplete else 0
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{field_name} must be an integer.")
        return None if allow_incomplete else 0
    if value <= 0:
        errors.append(f"{field_name} must be greater than 0.")
    return value


def _format_date_or_error(
    *,
    field_name: str,
    value: date | None,
    errors: list[str],
) -> str:
    if not isinstance(value, date):
        errors.append(f"{field_name} must be selected.")
        return ""
    return format_session_date(value)


def _format_time_or_error(
    *,
    field_name: str,
    value: time | None,
    errors: list[str],
) -> str:
    if not isinstance(value, time):
        errors.append(f"{field_name} must be selected.")
        return ""
    return format_session_time(value)


def _raw_list(
    raw_value: object,
    *,
    field_name: str,
    errors: list[str],
) -> list[object]:
    if not isinstance(raw_value, list):
        errors.append(f"{field_name} must be a list.")
        return []
    if not raw_value:
        errors.append(f"{field_name} must include at least one entry.")
    return raw_value


def _raw_optional_list(
    raw_value: object,
    *,
    field_name: str,
    errors: list[str],
) -> list[object]:
    if raw_value in (None, (), []):
        return []

    if not isinstance(raw_value, list):
        errors.append(f"{field_name} must be a list.")
        return []

    return raw_value


def _raw_mapping(
    raw_value: object,
    *,
    field_name: str,
    errors: list[str],
) -> Mapping[str, object] | None:
    if not isinstance(raw_value, Mapping):
        errors.append(f"{field_name} must be an object.")
        return None
    return raw_value


def _validate_attachment_references(
    raw_attachments: Iterable[Mapping[str, object]],
    errors: list[str],
) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []

    for index, raw_attachment in enumerate(raw_attachments, start=1):
        if not isinstance(raw_attachment, Mapping):
            errors.append(f"{ATTACHMENTS_KEY}_{index} must be an object.")
            continue

        upload_type = clean_string(raw_attachment.get(UPLOAD_TYPE_KEY))
        entry_id = clean_string(raw_attachment.get(ENTRY_ID_KEY))
        filename = clean_string(raw_attachment.get(FILENAME_KEY))
        caption = clean_string(raw_attachment.get(CAPTION_KEY))
        mime_type = clean_string(raw_attachment.get(MIME_TYPE_KEY))

        for required_key, value in (
            (UPLOAD_TYPE_KEY, upload_type),
            (ENTRY_ID_KEY, entry_id),
            (FILENAME_KEY, filename),
            (CAPTION_KEY, caption),
            (MIME_TYPE_KEY, mime_type),
        ):
            _validate_required(
                field_name=f"{ATTACHMENTS_KEY}_{index}.{required_key}",
                value=value,
                errors=errors,
            )

        if upload_type and upload_type not in INVIVO2P_FILE_UPLOAD_TYPES:
            errors.append(
                f"{ATTACHMENTS_KEY}_{index}.{UPLOAD_TYPE_KEY} must be one of "
                + ", ".join(INVIVO2P_FILE_UPLOAD_TYPES)
                + "."
            )

        attachments.append(
            {
                UPLOAD_TYPE_KEY: upload_type,
                ENTRY_ID_KEY: entry_id,
                FILENAME_KEY: filename,
                CAPTION_KEY: caption,
                MIME_TYPE_KEY: mime_type,
            }
        )

    return attachments


def _validate_sensory_stimuli(
    raw_stimuli: object,
    errors: list[str],
    *,
    allow_incomplete: bool = False,
) -> list[dict[str, str | float | None]]:
    stimuli: list[dict[str, str | float | None]] = []

    for stimulus_index, raw_stimulus in enumerate(
        _raw_optional_list(
            raw_stimuli,
            field_name=SENSORY_STIMULI_KEY,
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{SENSORY_STIMULI_KEY}_{stimulus_index}"
        stimulus_payload = _raw_mapping(
            raw_stimulus,
            field_name=field_name,
            errors=errors,
        )
        if stimulus_payload is None:
            continue

        sensory_stimulus_type = clean_string(
            stimulus_payload.get(SENSORY_STIMULUS_TYPE_KEY)
        )
        _validate_required(
            field_name=f"{field_name}.{SENSORY_STIMULUS_TYPE_KEY}",
            value=sensory_stimulus_type,
            errors=errors,
        )

        stimulus_duration_ms = _validate_optional_non_negative_number(
            field_name=f"{field_name}.{STIMULUS_DURATION_MS_KEY}",
            value=stimulus_payload.get(STIMULUS_DURATION_MS_KEY),
            errors=errors,
        )
        stimulus_frequency_hz = _validate_optional_non_negative_number(
            field_name=f"{field_name}.{STIMULUS_FREQUENCY_HZ_KEY}",
            value=stimulus_payload.get(STIMULUS_FREQUENCY_HZ_KEY),
            errors=errors,
        )

        stimuli.append(
            {
                SENSORY_STIMULUS_TYPE_KEY: sensory_stimulus_type,
                STIMULUS_DURATION_MS_KEY: stimulus_duration_ms,
                STIMULUS_REPETITION_KEY: clean_string(
                    stimulus_payload.get(STIMULUS_REPETITION_KEY)
                ),
                STIMULUS_FREQUENCY_HZ_KEY: stimulus_frequency_hz,
                STIMULUS_NOTES_KEY: clean_string(
                    stimulus_payload.get(STIMULUS_NOTES_KEY)
                ),
            }
        )

    return stimuli


def _validate_cameras(
    raw_cameras: object,
    errors: list[str],
    *,
    allow_incomplete: bool = False,
) -> list[dict[str, str | float | int | None]]:
    cameras: list[dict[str, str | float | int | None]] = []

    for camera_index, raw_camera in enumerate(
        _raw_optional_list(
            raw_cameras,
            field_name=CAMERAS_KEY,
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{CAMERAS_KEY}_{camera_index}"
        camera_payload = _raw_mapping(
            raw_camera,
            field_name=field_name,
            errors=errors,
        )
        if camera_payload is None:
            continue

        camera_number = _validate_positive_integer(
            field_name=f"{field_name}.{CAMERA_NUMBER_KEY}",
            value=camera_payload.get(CAMERA_NUMBER_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        camera_model = clean_string(camera_payload.get(CAMERA_MODEL_KEY))
        camera_acq_software = clean_string(
            camera_payload.get(CAMERA_ACQ_SOFTWARE_KEY)
        )

        _validate_required(
            field_name=f"{field_name}.{CAMERA_MODEL_KEY}",
            value=camera_model,
            errors=errors,
        )
        _validate_required(
            field_name=f"{field_name}.{CAMERA_ACQ_SOFTWARE_KEY}",
            value=camera_acq_software,
            errors=errors,
        )

        camera_frame_rate_hz = _validate_optional_non_negative_number(
            field_name=f"{field_name}.{CAMERA_FRAME_RATE_HZ_KEY}",
            value=camera_payload.get(CAMERA_FRAME_RATE_HZ_KEY),
            errors=errors,
        )

        cameras.append(
            {
                CAMERA_NUMBER_KEY: camera_number,
                CAMERA_MODEL_KEY: camera_model,
                CAMERA_ACQ_SOFTWARE_KEY: camera_acq_software,
                CAMERA_FRAME_RATE_HZ_KEY: camera_frame_rate_hz,
                CAMERA_NOTES_KEY: clean_string(
                    camera_payload.get(CAMERA_NOTES_KEY)
                ),
            }
        )

    return cameras


def _validate_plane_entries(
    raw_planes: object,
    *,
    field_prefix: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> list[dict[str, str | float | int | None]]:
    planes: list[dict[str, str | float | int | None]] = []

    for plane_index, raw_plane in enumerate(
        _raw_list(
            raw_planes,
            field_name=f"{field_prefix}.{PLANES_KEY}",
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{field_prefix}.{PLANES_KEY}_{plane_index}"
        plane_payload = _raw_mapping(
            raw_plane,
            field_name=field_name,
            errors=errors,
        )
        if plane_payload is None:
            continue

        plane_number = _validate_positive_integer(
            field_name=f"{field_name}.{PLANE_NUMBER_KEY}",
            value=plane_payload.get(PLANE_NUMBER_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        imaging_layer = clean_string(plane_payload.get(IMAGING_LAYER_KEY))
        _validate_required(
            field_name=f"{field_name}.{IMAGING_LAYER_KEY}",
            value=imaging_layer,
            errors=errors,
        )
        depth_um = _validate_non_negative_number(
            field_name=f"{field_name}.{DEPTH_UM_KEY}",
            value=plane_payload.get(DEPTH_UM_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )

        planes.append(
            {
                PLANE_NUMBER_KEY: plane_number,
                IMAGING_LAYER_KEY: imaging_layer,
                DEPTH_UM_KEY: depth_um,
            }
        )

    return planes


def _validate_fovs(
    raw_fovs: object,
    errors: list[str],
    *,
    allow_incomplete: bool = False,
) -> list[dict[str, object]]:
    fovs: list[dict[str, object]] = []

    for fov_index, raw_fov in enumerate(
        _raw_list(
            raw_fovs,
            field_name=FOVS_KEY,
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{FOVS_KEY}_{fov_index}"
        fov_payload = _raw_mapping(
            raw_fov,
            field_name=field_name,
            errors=errors,
        )
        if fov_payload is None:
            continue

        fov_number = _validate_positive_integer(
            field_name=f"{field_name}.{FOV_NUMBER_KEY}",
            value=fov_payload.get(FOV_NUMBER_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        imaging_region = clean_string(fov_payload.get(IMAGING_REGION_KEY))
        hemisphere = clean_string(fov_payload.get(HEMISPHERE_KEY))
        num_planes = _validate_positive_integer(
            field_name=f"{field_name}.{NUM_PLANES_KEY}",
            value=fov_payload.get(NUM_PLANES_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )

        _validate_required(
            field_name=f"{field_name}.{IMAGING_REGION_KEY}",
            value=imaging_region,
            errors=errors,
        )

        if hemisphere not in HEMISPHERE_OPTIONS:
            errors.append(
                f"{field_name}.{HEMISPHERE_KEY} must be one of "
                + ", ".join(HEMISPHERE_OPTIONS)
                + "."
            )

        planes = _validate_plane_entries(
            fov_payload.get(PLANES_KEY),
            field_prefix=field_name,
            errors=errors,
            allow_incomplete=allow_incomplete,
        )

        if num_planes is not None and len(planes) != num_planes:
            errors.append(
                f"{field_name}.{PLANES_KEY} must include exactly "
                f"{num_planes} plane entries."
            )

        fovs.append(
            {
                FOV_NUMBER_KEY: fov_number,
                IMAGING_REGION_KEY: imaging_region,
                HEMISPHERE_KEY: hemisphere,
                NUM_PLANES_KEY: num_planes,
                PLANES_KEY: planes,
                FOV_NOTES_KEY: clean_string(fov_payload.get(FOV_NOTES_KEY)),
            }
        )

    return fovs


def _validate_channel_fields(
    raw_payload: Mapping[str, object],
    errors: list[str],
) -> dict[str, str]:
    channel = clean_string(raw_payload.get(CHANNEL_KEY))
    _validate_required(
        field_name=CHANNEL_KEY,
        value=channel,
        errors=errors,
    )

    if channel and channel not in CHANNEL_OPTIONS:
        errors.append(
            f"{CHANNEL_KEY} must be one of "
            + ", ".join(CHANNEL_OPTIONS)
            + "."
        )

    green_construct = clean_string(raw_payload.get(GREEN_CONSTRUCT_KEY))
    red_construct = clean_string(raw_payload.get(RED_CONSTRUCT_KEY))
    green_substrate = clean_string(
        raw_payload.get(GREEN_CHANNEL_SUBSTRATE_KEY)
    )
    red_substrate = clean_string(
        raw_payload.get(RED_CHANNEL_SUBSTRATE_KEY)
    )

    if channel in ("Green", "Green + Red"):
        _validate_required(
            field_name=GREEN_CONSTRUCT_KEY,
            value=green_construct,
            errors=errors,
        )
        _validate_required(
            field_name=GREEN_CHANNEL_SUBSTRATE_KEY,
            value=green_substrate,
            errors=errors,
        )

    if channel in ("Red", "Green + Red"):
        _validate_required(
            field_name=RED_CONSTRUCT_KEY,
            value=red_construct,
            errors=errors,
        )
        _validate_required(
            field_name=RED_CHANNEL_SUBSTRATE_KEY,
            value=red_substrate,
            errors=errors,
        )

    return {
        CHANNEL_KEY: channel,
        GREEN_CONSTRUCT_KEY: green_construct,
        RED_CONSTRUCT_KEY: red_construct,
        GREEN_CHANNEL_SUBSTRATE_KEY: green_substrate,
        RED_CHANNEL_SUBSTRATE_KEY: red_substrate,
    }


def _validate_opto_fields(
    raw_payload: Mapping[str, object],
    *,
    session_type: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> dict[str, str | float | None]:
    wf_opto_wavelength_nm = _validate_optional_non_negative_number(
        field_name=WF_OPTO_WAVELENGTH_NM_KEY,
        value=raw_payload.get(WF_OPTO_WAVELENGTH_NM_KEY),
        errors=errors,
    )
    wf_opto_power_mw = _validate_optional_non_negative_number(
        field_name=WF_OPTO_POWER_MW_KEY,
        value=raw_payload.get(WF_OPTO_POWER_MW_KEY),
        errors=errors,
    )
    wf_opto_mode = clean_string(raw_payload.get(WF_OPTO_MODE_KEY))

    slm_opto_wavelength_nm = _validate_optional_non_negative_number(
        field_name=SLM_OPTO_WAVELENGTH_NM_KEY,
        value=raw_payload.get(SLM_OPTO_WAVELENGTH_NM_KEY),
        errors=errors,
    )
    slm_opto_power_mw = _validate_optional_non_negative_number(
        field_name=SLM_OPTO_POWER_MW_KEY,
        value=raw_payload.get(SLM_OPTO_POWER_MW_KEY),
        errors=errors,
    )
    slm_opto_mode = clean_string(raw_payload.get(SLM_OPTO_MODE_KEY))

    if session_type == "2P Imaging + WF Opto":
        if wf_opto_mode not in WF_OPTO_MODE_OPTIONS:
            errors.append(
                f"{WF_OPTO_MODE_KEY} must be one of "
                + ", ".join(WF_OPTO_MODE_OPTIONS)
                + "."
            )
        _validate_non_negative_number(
            field_name=WF_OPTO_WAVELENGTH_NM_KEY,
            value=raw_payload.get(WF_OPTO_WAVELENGTH_NM_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        _validate_non_negative_number(
            field_name=WF_OPTO_POWER_MW_KEY,
            value=raw_payload.get(WF_OPTO_POWER_MW_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )

    if session_type == "2P Imaging + SLM Opto":
        if slm_opto_mode not in SLM_OPTO_MODE_OPTIONS:
            errors.append(
                f"{SLM_OPTO_MODE_KEY} must be one of "
                + ", ".join(SLM_OPTO_MODE_OPTIONS)
                + "."
            )
        _validate_non_negative_number(
            field_name=SLM_OPTO_WAVELENGTH_NM_KEY,
            value=raw_payload.get(SLM_OPTO_WAVELENGTH_NM_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        _validate_non_negative_number(
            field_name=SLM_OPTO_POWER_MW_KEY,
            value=raw_payload.get(SLM_OPTO_POWER_MW_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )

    return {
        WF_OPTO_WAVELENGTH_NM_KEY: wf_opto_wavelength_nm,
        WF_OPTO_POWER_MW_KEY: wf_opto_power_mw,
        WF_OPTO_MODE_KEY: wf_opto_mode,
        SLM_OPTO_WAVELENGTH_NM_KEY: slm_opto_wavelength_nm,
        SLM_OPTO_POWER_MW_KEY: slm_opto_power_mw,
        SLM_OPTO_MODE_KEY: slm_opto_mode,
    }


def build_invivo2p_payload(
    *,
    project_id: str,
    investigator: str,
    animal_id: str,
    ear_tag: str,
    session_date: date | None,
    session_id: str,
    session_type: str,
    behavior_task_name: str,
    behavior_task_phase: str,
    imager: str,
    start_time: time | None,
    end_time: time | None,
    invivo2p_system_id: str,
    invivo2p_software_name: str,
    behavior_rig: str,
    objective: str,
    imaging_laser_wavelength_nm: int | float | None,
    imaging_laser_power_mw: int | float | None,
    frame_rate_hz: int | float | None,
    zoom: int | float | None,
    resolution_pix: str,
    fov_size_um: str,
    channel: str,
    green_construct: str = "",
    red_construct: str = "",
    green_channel_substrate: str = "",
    red_channel_substrate: str = "",
    wf_opto_wavelength_nm: int | float | None = None,
    wf_opto_power_mw: int | float | None = None,
    wf_opto_mode: str = "",
    slm_opto_wavelength_nm: int | float | None = None,
    slm_opto_power_mw: int | float | None = None,
    slm_opto_mode: str = "",
    num_fovs: int | None = None,
    fovs: object = (),
    sensory_stimuli: object = (),
    cameras: object = (),
    raw_2p_imaging_data_path: str = "",
    raw_2p_imaging_metadata_path: str = "",
    raw_2p_sync_data_path: str = "",
    raw_2p_sync_metadata_path: str = "",
    general_notes: str = "",
    attachments: Iterable[Mapping[str, object]] = (),
    allow_incomplete: bool = False,
    draft_id: str = "",
) -> dict[str, Any]:
    """Validate form values and return the invivo2p JSON payload."""
    cleaned_project_id = clean_string(project_id)
    cleaned_investigator = clean_string(investigator)
    cleaned_animal_id = clean_string(animal_id)
    cleaned_ear_tag = clean_string(ear_tag)
    cleaned_session_id = clean_string(session_id)
    cleaned_session_type = clean_string(session_type)
    cleaned_behavior_task_name = clean_string(behavior_task_name)
    cleaned_behavior_task_phase = clean_string(behavior_task_phase)
    cleaned_imager = clean_string(imager)
    cleaned_invivo2p_system_id = clean_string(invivo2p_system_id)
    cleaned_invivo2p_software_name = clean_string(invivo2p_software_name)
    cleaned_behavior_rig = clean_string(behavior_rig)
    cleaned_objective = clean_string(objective)
    cleaned_resolution_pix = clean_string(resolution_pix)
    cleaned_fov_size_um = clean_string(fov_size_um)
    cleaned_general_notes = clean_string(general_notes)
    cleaned_draft_id = clean_string(draft_id)
    errors: list[str] = []
    for field_name, value in (
        (PROJECT_ID_KEY, cleaned_project_id),
        (INVESTIGATOR_KEY, cleaned_investigator),
        (ANIMAL_ID_LABEL, cleaned_animal_id),
        (EAR_TAG_LABEL, cleaned_ear_tag),
        (SESSION_ID_KEY, cleaned_session_id),
        (SESSION_TYPE_KEY, cleaned_session_type),
        (BEHAVIOR_TASK_NAME_KEY, cleaned_behavior_task_name),
        (BEHAVIOR_TASK_PHASE_KEY, cleaned_behavior_task_phase),
        (IMAGER_KEY, cleaned_imager),
        (INVIVO2P_SYSTEM_ID_KEY, cleaned_invivo2p_system_id),
        (INVIVO2P_SOFTWARE_NAME_KEY, cleaned_invivo2p_software_name),
        (BEHAVIOR_RIG_KEY, cleaned_behavior_rig),
        (OBJECTIVE_KEY, cleaned_objective),
    ):
        _validate_required(
            field_name=field_name,
            value=value,
            errors=errors,
        )
    if (
        cleaned_session_type
        and cleaned_session_type not in INVIVO2P_SESSION_TYPE_OPTIONS
    ):
        errors.append(
            f"{SESSION_TYPE_KEY} must be one of "
            + ", ".join(INVIVO2P_SESSION_TYPE_OPTIONS)
            + "."
        )
    formatted_session_date = _format_date_or_error(
        field_name=SESSION_DATE_KEY,
        value=session_date,
        errors=errors,
    )
    formatted_start_time = _format_time_or_error(
        field_name=START_TIME_KEY,
        value=start_time,
        errors=errors,
    )
    formatted_end_time = _format_time_or_error(
        field_name=END_TIME_KEY,
        value=end_time,
        errors=errors,
    )
    if isinstance(start_time, time) and isinstance(end_time, time):
        if end_time <= start_time:
            errors.append(
                f"{END_TIME_KEY} must be later than {START_TIME_KEY}."
            )
    cleaned_imaging_laser_wavelength_nm = _validate_non_negative_number(
        field_name=IMAGING_LASER_WAVELENGTH_NM_KEY,
        value=imaging_laser_wavelength_nm,
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    cleaned_imaging_laser_power_mw = _validate_non_negative_number(
        field_name=IMAGING_LASER_POWER_MW_KEY,
        value=imaging_laser_power_mw,
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    cleaned_frame_rate_hz = _validate_non_negative_number(
        field_name=FRAME_RATE_HZ_KEY,
        value=frame_rate_hz,
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    cleaned_zoom = _validate_non_negative_number(
        field_name=ZOOM_KEY,
        value=zoom,
        errors=errors,
        allow_incomplete=allow_incomplete,
    )

    cleaned_num_fovs = _validate_positive_integer(
        field_name=NUM_FOVS_KEY,
        value=num_fovs,
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    
    channel_fields = _validate_channel_fields(
        {
            CHANNEL_KEY: channel,
            GREEN_CONSTRUCT_KEY: green_construct,
            RED_CONSTRUCT_KEY: red_construct,
            GREEN_CHANNEL_SUBSTRATE_KEY: green_channel_substrate,
            RED_CHANNEL_SUBSTRATE_KEY: red_channel_substrate,
        },
        errors,
    )

    opto_fields = _validate_opto_fields(
        {
            WF_OPTO_WAVELENGTH_NM_KEY: wf_opto_wavelength_nm,
            WF_OPTO_POWER_MW_KEY: wf_opto_power_mw,
            WF_OPTO_MODE_KEY: wf_opto_mode,
            SLM_OPTO_WAVELENGTH_NM_KEY: slm_opto_wavelength_nm,
            SLM_OPTO_POWER_MW_KEY: slm_opto_power_mw,
            SLM_OPTO_MODE_KEY: slm_opto_mode,
        },
        session_type=cleaned_session_type,
        errors=errors,
        allow_incomplete=allow_incomplete,
    )

    cleaned_fovs = _validate_fovs(
        fovs,
        errors,
        allow_incomplete=allow_incomplete,
    )
    if cleaned_num_fovs is not None and len(cleaned_fovs) != cleaned_num_fovs:
        errors.append(
            f"{FOVS_KEY} must include exactly {cleaned_num_fovs} entries."
        )

    cleaned_sensory_stimuli = _validate_sensory_stimuli(
        sensory_stimuli,
        errors,
        allow_incomplete=allow_incomplete,
    )

    cleaned_cameras = _validate_cameras(
        cameras,
        errors,
        allow_incomplete=allow_incomplete,
    )

    cleaned_attachments = _validate_attachment_references(
        attachments,
        errors,
    )

    if errors and not allow_incomplete:
        raise Invivo2pValidationError(errors)

    payload: dict[str, Any] = {
        PROJECT_ID_KEY: cleaned_project_id,
        INVESTIGATOR_KEY: cleaned_investigator,
        ANIMAL_ID_KEY: cleaned_animal_id,
        EAR_TAG_KEY: cleaned_ear_tag,
        SESSION_DATE_KEY: formatted_session_date,
        SESSION_ID_KEY: cleaned_session_id,
        SESSION_TYPE_KEY: cleaned_session_type,
        BEHAVIOR_TASK_NAME_KEY: cleaned_behavior_task_name,
        BEHAVIOR_TASK_PHASE_KEY: cleaned_behavior_task_phase,
        IMAGER_KEY: cleaned_imager,
        START_TIME_KEY: formatted_start_time,
        END_TIME_KEY: formatted_end_time,
        INVIVO2P_SYSTEM_ID_KEY: cleaned_invivo2p_system_id,
        INVIVO2P_SOFTWARE_NAME_KEY: cleaned_invivo2p_software_name,
        BEHAVIOR_RIG_KEY: cleaned_behavior_rig,
        OBJECTIVE_KEY: cleaned_objective,
        IMAGING_LASER_WAVELENGTH_NM_KEY: cleaned_imaging_laser_wavelength_nm,
        IMAGING_LASER_POWER_MW_KEY: cleaned_imaging_laser_power_mw,
        FRAME_RATE_HZ_KEY: cleaned_frame_rate_hz,
        ZOOM_KEY: cleaned_zoom,
        RESOLUTION_PIX_KEY: cleaned_resolution_pix,
        FOV_SIZE_UM_KEY: cleaned_fov_size_um,
        **channel_fields,
        **opto_fields,
        NUM_FOVS_KEY: cleaned_num_fovs,
        FOVS_KEY: cleaned_fovs,
        SENSORY_STIMULI_KEY: cleaned_sensory_stimuli,
        CAMERAS_KEY: cleaned_cameras,
        RAW_2P_IMAGING_DATA_PATH_KEY: clean_string(
            raw_2p_imaging_data_path
        ),
        RAW_2P_IMAGING_METADATA_PATH_KEY: clean_string(
            raw_2p_imaging_metadata_path
        ),
        RAW_2P_SYNC_DATA_PATH_KEY: clean_string(raw_2p_sync_data_path),
        RAW_2P_SYNC_METADATA_PATH_KEY: clean_string(
            raw_2p_sync_metadata_path
        ),
        GENERAL_NOTES_KEY: cleaned_general_notes,
        ATTACHMENTS_KEY: cleaned_attachments,
    }

    if not allow_incomplete:
        return payload

    payload[INVIVO2P_STATUS_KEY] = (
        INVIVO2P_STATUS_INCOMPLETE if errors else INVIVO2P_STATUS_COMPLETE
    )
    payload[INVIVO2P_VALIDATION_ERRORS_KEY] = list(errors)
    if errors and cleaned_draft_id and not formatted_session_date:
        payload[INVIVO2P_DRAFT_ID_KEY] = cleaned_draft_id
    return payload


def invivo2p_option_values(
    payload: Mapping[str, Any],
) -> tuple[
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
]:
    """Return reusable invivo2p option values from a payload."""
    sensory_stimulus_types: list[str] = []
    camera_models: list[str] = []
    camera_acq_software: list[str] = []
    imaging_regions: list[str] = []
    imaging_layers: list[str] = []

    for raw_stimulus in payload.get(SENSORY_STIMULI_KEY, []):
        if isinstance(raw_stimulus, Mapping):
            sensory_stimulus_type = clean_string(
                raw_stimulus.get(SENSORY_STIMULUS_TYPE_KEY)
            )
            if sensory_stimulus_type:
                sensory_stimulus_types.append(sensory_stimulus_type)

    for raw_camera in payload.get(CAMERAS_KEY, []):
        if isinstance(raw_camera, Mapping):
            camera_model = clean_string(raw_camera.get(CAMERA_MODEL_KEY))
            camera_software = clean_string(
                raw_camera.get(CAMERA_ACQ_SOFTWARE_KEY)
            )
            if camera_model:
                camera_models.append(camera_model)
            if camera_software:
                camera_acq_software.append(camera_software)

    for raw_fov in payload.get(FOVS_KEY, []):
        if not isinstance(raw_fov, Mapping):
            continue

        imaging_region = clean_string(raw_fov.get(IMAGING_REGION_KEY))
        if imaging_region:
            imaging_regions.append(imaging_region)

        raw_planes = raw_fov.get(PLANES_KEY, [])
        if not isinstance(raw_planes, list):
            continue

        for raw_plane in raw_planes:
            if isinstance(raw_plane, Mapping):
                imaging_layer = clean_string(raw_plane.get(IMAGING_LAYER_KEY))
                if imaging_layer:
                    imaging_layers.append(imaging_layer)

    return (
        [clean_string(payload.get(SESSION_TYPE_KEY))],
        [clean_string(payload.get(BEHAVIOR_TASK_NAME_KEY))],
        [clean_string(payload.get(BEHAVIOR_TASK_PHASE_KEY))],
        [clean_string(payload.get(IMAGER_KEY))],
        [clean_string(payload.get(INVIVO2P_SYSTEM_ID_KEY))],
        [clean_string(payload.get(INVIVO2P_SOFTWARE_NAME_KEY))],
        [clean_string(payload.get(BEHAVIOR_RIG_KEY))],
        [clean_string(payload.get(OBJECTIVE_KEY))],
        sensory_stimulus_types,
        camera_models,
        camera_acq_software,
        [clean_string(payload.get(GREEN_CONSTRUCT_KEY))],
        [clean_string(payload.get(RED_CONSTRUCT_KEY))],
        [clean_string(payload.get(CHANNEL_KEY))],
        imaging_regions,
        imaging_layers,
        [clean_string(payload.get(GREEN_CHANNEL_SUBSTRATE_KEY))],
        [clean_string(payload.get(RED_CHANNEL_SUBSTRATE_KEY))],
    )


def with_invivo2p_options(
    config: Mapping[str, Any],
    *,
    session_types: Iterable[str] = (),
    behavior_task_names: Iterable[str] = (),
    behavior_task_phases: Iterable[str] = (),
    imagers: Iterable[str] = (),
    invivo2p_system_ids: Iterable[str] = (),
    invivo2p_software_names: Iterable[str] = (),
    behavior_rigs: Iterable[str] = (),
    objectives: Iterable[str] = (),
    sensory_stimulus_types: Iterable[str] = (),
    camera_models: Iterable[str] = (),
    camera_acq_software: Iterable[str] = (),
    green_constructs: Iterable[str] = (),
    red_constructs: Iterable[str] = (),
    channels: Iterable[str] = (),
    imaging_regions: Iterable[str] = (),
    imaging_layers: Iterable[str] = (),
    green_channel_substrates: Iterable[str] = (),
    red_channel_substrates: Iterable[str] = (),
) -> tuple[dict[str, Any], bool]:
    """Return config with reusable invivo2p options and whether it changed."""
    updated_config = deepcopy(dict(config))
    options = normalize_options(updated_config.get(OPTIONS_KEY))
    original_options = deepcopy(options)

    for session_type in session_types:
        add_option(options, SESSION_TYPE_OPTIONS_KEY, session_type)
    for behavior_task_name in behavior_task_names:
        add_option(options, BEHAVIOR_TASK_NAME_OPTIONS_KEY, behavior_task_name)
    for behavior_task_phase in behavior_task_phases:
        add_option(options, BEHAVIOR_TASK_PHASE_OPTIONS_KEY, behavior_task_phase)
    for imager in imagers:
        add_option(options, INVIVO2P_IMAGER_OPTIONS_KEY, imager)
    for system_id in invivo2p_system_ids:
        add_option(options, INVIVO2P_SYSTEM_ID_OPTIONS_KEY, system_id)
    for software_name in invivo2p_software_names:
        add_option(options, INVIVO2P_SOFTWARE_NAME_OPTIONS_KEY, software_name)
    for behavior_rig in behavior_rigs:
        add_option(options, BEHAVIOR_RIG_OPTIONS_KEY, behavior_rig)
    for objective in objectives:
        add_option(options, OBJECTIVE_OPTIONS_KEY, objective)
    for sensory_stimulus_type in sensory_stimulus_types:
        add_option(
            options,
            SENSORY_STIMULUS_TYPE_OPTIONS_KEY,
            sensory_stimulus_type,
        )
    for camera_model in camera_models:
        add_option(options, CAMERA_MODEL_OPTIONS_KEY, camera_model)
    for camera_software in camera_acq_software:
        add_option(options, CAMERA_ACQ_SOFTWARE_OPTIONS_KEY, camera_software)
    for green_construct in green_constructs:
        add_option(options, GREEN_CONSTRUCT_OPTIONS_KEY, green_construct)
    for red_construct in red_constructs:
        add_option(options, RED_CONSTRUCT_OPTIONS_KEY, red_construct)
    for channel in channels:
        add_option(options, CHANNEL_OPTIONS_KEY, channel)
    for imaging_region in imaging_regions:
        add_option(options, IMAGING_REGION_OPTIONS_KEY, imaging_region)
    for imaging_layer in imaging_layers:
        add_option(options, IMAGING_LAYER_OPTIONS_KEY, imaging_layer)
    for green_substrate in green_channel_substrates:
        add_option(
            options,
            GREEN_CHANNEL_SUBSTRATE_OPTIONS_KEY,
            green_substrate,
        )
    for red_substrate in red_channel_substrates:
        add_option(
            options,
            RED_CHANNEL_SUBSTRATE_OPTIONS_KEY,
            red_substrate,
        )

    updated_config[OPTIONS_KEY] = options
    return updated_config, options != original_options


def with_invivo2p_payload_options(
    config: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Return config updated with reusable options from an invivo2p payload."""
    (
        session_types,
        behavior_task_names,
        behavior_task_phases,
        imagers,
        invivo2p_system_ids,
        invivo2p_software_names,
        behavior_rigs,
        objectives,
        sensory_stimulus_types,
        camera_models,
        camera_acq_software,
        green_constructs,
        red_constructs,
        channels,
        imaging_regions,
        imaging_layers,
        green_channel_substrates,
        red_channel_substrates,
    ) = invivo2p_option_values(payload)

    return with_invivo2p_options(
        config,
        session_types=session_types,
        behavior_task_names=behavior_task_names,
        behavior_task_phases=behavior_task_phases,
        imagers=imagers,
        invivo2p_system_ids=invivo2p_system_ids,
        invivo2p_software_names=invivo2p_software_names,
        behavior_rigs=behavior_rigs,
        objectives=objectives,
        sensory_stimulus_types=sensory_stimulus_types,
        camera_models=camera_models,
        camera_acq_software=camera_acq_software,
        green_constructs=green_constructs,
        red_constructs=red_constructs,
        channels=channels,
        imaging_regions=imaging_regions,
        imaging_layers=imaging_layers,
        green_channel_substrates=green_channel_substrates,
        red_channel_substrates=red_channel_substrates,
    )


def with_invivo2p_imager_options(
    config: Mapping[str, Any],
    *,
    imager: str,
) -> tuple[dict[str, Any], bool]:
    """Return config with a reusable invivo2p imager option."""
    return with_invivo2p_options(config, imagers=[imager])