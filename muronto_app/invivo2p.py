"""In Vivo 2P Imaging record validation and payload helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import date, time
from typing import Any, Final

from muronto_app.config import (
    COVERSLIP_DIAMETER_OPTIONS_KEY,
    COVERSLIP_THICKNESS_OPTIONS_KEY,
    COVERSLIP_TYPE_OPTIONS_KEY,
    CRANIAL_WINDOW_REGION_OPTIONS_KEY,
    CRYSTAL_SKULL_WELL_TYPE_OPTIONS_KEY,
    CS_TYPE_OPTIONS_KEY,
    ELECTRODE_SITE_OPTIONS_KEY,
    HEADPLATE_TYPE_OPTIONS_KEY,
    INVESTIGATOR_KEY,
    MEDICATION_OPTIONS_KEY,
    OPTIONS_KEY,
    PROBE_MODEL_OPTIONS_KEY,
    PROJECT_ID_KEY,
    SITE_OPTIONS_KEY,
    SURGEON_OPTIONS_KEY,
    VIRUS_OPTIONS_KEY,
    VIRUS_SOURCE_OPTIONS_KEY,
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
IMAGER_KEY: Final[str] = "imager"
INVIVO2P_DATE_KEY: Final[str] = "invivo2p_date"
GENERAL_NOTES_KEY: Final[str] = "general_notes"
ATTACHMENTS_KEY: Final[str] = "attachments"
UPLOAD_TYPE_KEY: Final[str] = "upload_type"
ENTRY_ID_KEY: Final[str] = "entry_id"
FILENAME_KEY: Final[str] = "filename"
CAPTION_KEY: Final[str] = "caption"
MIME_TYPE_KEY: Final[str] = "mime_type"




# PREOP_CNN_KEY: Final[str] = "preop_cnn"
# PREOP_CNN_LABEL: Final[str] = "PreOp Card Cage Number"
# POSTOP_CNN_KEY: Final[str] = "postop_cnn"
# POSTOP_CNN_LABEL: Final[str] = "PostOp Card Cage Number"
# WEIGHT_PRE_G_KEY: Final[str] = "weight_pre_g"
# WEIGHT_POST_G_KEY: Final[str] = "weight_post_g"
# MEDICATIONS_KEY: Final[str] = "medications"
# MEDICATION_KEY: Final[str] = "medication"
# CONC_MGML_KEY: Final[str] = "conc_mgml"
# VOLUME_KEY: Final[str] = "volume_ml"
# LEGACY_VOLUME_KEY: Final[str] = "volume"
# START_TIME_KEY: Final[str] = "start_time"
# END_TIME_KEY: Final[str] = "end_time"
# BREGMA_LAMBDA_DIST_MM_KEY: Final[str] = "bregma_lambda_dist_mm"
# SURGICAL_PROCEDURES_KEY: Final[str] = "surgical_procedures"
# SURGERY_CATEGORY_KEY: Final[str] = "surgery_category"
# INJECTIONS_KEY: Final[str] = "injections"
# SITE_KEY: Final[str] = "site"
# HEMISPHERE_KEY: Final[str] = "hemisphere"
# VIRUSES_KEY: Final[str] = "viruses"
# VIRUS_KEY: Final[str] = "virus"
# VIRUS_SOURCE_KEY: Final[str] = "virus_source"
# VIRUS_ID_KEY: Final[str] = "virus_id"
# VIRUS_STOCK_KEY: Final[str] = "virus_stock"
# STOCK_TITER_KEY: Final[str] = "stock_titer"
# DILUTION_KEY: Final[str] = "dilution"
# INFUSION_RATE_NLMIN_KEY: Final[str] = "infusion_rate_nlmin"
# INFUSIONS_KEY: Final[str] = "infusions"
# AP_KEY: Final[str] = "ap"
# ML_KEY: Final[str] = "ml"
# DV_KEY: Final[str] = "dv"
# INFUSION_VOLUME_NL_KEY: Final[str] = "infusion_volume_nl"
# POST_INFUSION_FLOW_TEST_KEY: Final[str] = "post_infusion_flow_test"
# NOTES_KEY: Final[str] = "notes"
# IMPLANT_TYPE_KEY: Final[str] = "implant_type"
# CRANIAL_WINDOW_KEY: Final[str] = "cranial_window"
# CRYSTAL_SKULL_KEY: Final[str] = "crystal_skull"
# HEADPLATE_TYPE_KEY: Final[str] = "headplate_type"
# CS_TYPE_KEY: Final[str] = "cs_type"
# COVERSLIP_TYPE_KEY: Final[str] = "coverslip_type"
# COVERSLIP_DIAMETER_KEY: Final[str] = "coverslip_diameter"
# COVERSLIP_THICKNESS_KEY: Final[str] = "coverslip_thickness"
# REGION_KEY: Final[str] = "region"
# CENTER_AP_KEY: Final[str] = "center_ap"
# CENTER_ML_KEY: Final[str] = "center_ml"
# FRONT_AP_KEY: Final[str] = "front_ap"
# LEFT_ML_KEY: Final[str] = "left_ml"
# WELL_TYPE_KEY: Final[str] = "well_type"
# ELECTRODES_KEY: Final[str] = "electrodes"
# ELECTRODE_TYPE_KEY: Final[str] = "electrode_type"
# PROBE_MODEL_KEY: Final[str] = "probe_model"
# PROBE_ID_KEY: Final[str] = "probe_id"
# ELECTRODE_SITE_KEY: Final[str] = "electrode_site"
# ELECTRODE_HEMISPHERE_KEY: Final[str] = "electrode_hemisphere"
# PITCH_KEY: Final[str] = "pitch"
# YAW_KEY: Final[str] = "yaw"
# ROLL_KEY: Final[str] = "roll"
# GROUND_KEY: Final[str] = "ground"
# REFERENCE_KEY: Final[str] = "reference"

IMAGING_CATEGORY: Final[str] = "2P Imaging"
IMAGING_WF_OPTO_CATEGORY: Final[str] = "2P Imaging + Widefield Opto"
IMAGING_SLM_OPTO_CATEGORY: Final[str] = "2P Imaging + SLM Opto"

SESSION_TYPE_CATEGORY_OPTIONS: Final[tuple[str, ...]] = (
    IMAGING_CATEGORY,
    IMAGING_WF_OPTO_CATEGORY,
    IMAGING_SLM_OPTO_CATEGORY,
)

VOLUN_RUNNING_CATEGORY: Final[str] = "Voluntary Running"
VOLUN_FORCED_RUNNING_CATEGORY: Final[str] = "Voluntary + Forced Running"
SEN_EVID_ACCUM_CATEGORY: Final[str] = "Sensory Evidence Accumulation"

BEHAV_TASK_NAME_CATEGORY_OPTIONS: Final[tuple[str, ...]] = (
    VOLUN_RUNNING_CATEGORY,
    VOLUN_FORCED_RUNNING_CATEGORY,
    SEN_EVID_ACCUM_CATEGORY,
)

BEHAV_TASK_PHASE_OPTIONS: Final[tuple[str, ...]] = (
    "Phase_0",
    "Phase_1A",
    "Phase_1B",
    "Phase_2A",
    "Phase_2B",
    "Phase_3A",
    "Phase_3B",
    "Phase_3C",
    "Phase_3D",
    "Phase_3E",
    "Phase_4A",
    "Phase_4B",
    "Phase_4C",
    "Phase_5",
    "Phase_6",
    "n/a",
)


IMAGING_SYSTEM_ID_OPTIONS: Final[tuple[str, ...]] = (
    "ORiON Bruker Ultima",
    "SLiM Bruker Investigator",
)

IMAGING_SOFTWARE_NAME_OPTIONS: Final[tuple[str, ...]] = (
    "???",
)

# Text box for IMAGING_SOFTWARE_VERSION: 

BEHAV_RIG_ID_OPTIONS: Final[tuple[str, ...]] = (
    "Wheel 1",
    "SEASIC 1",
    "n/a",
)




# MAKE THIS MULTI-SELECT
SENSORY_STIMULUS_TYPE_OPTIONS: Final[tuple[str, ...]] = (
    "Bar",
    "Air Puff",
    "n/a",
)




















HEMISPHERE_OPTIONS: Final[tuple[str, ...]] = ("LH", "RH")
POST_INFUSION_FLOW_TEST_OPTIONS: Final[tuple[str, ...]] = (
    "Pass",
    "Fail",
    "n/a",
)
ELECTRODE_TYPE_OPTIONS: Final[tuple[str, ...]] = (
    "NeuroPixels",
    "NeuroNexus",
)
CRANIAL_WINDOW_IMPLANT_TYPE: Final[str] = "Cranial Window"
CRYSTAL_SKULL_IMPLANT_TYPE: Final[str] = "Crystal Skull"
ELECTRODE_IMPLANT_TYPE: Final[str] = "Electrode"
GRIN_LENS_IMPLANT_TYPE: Final[str] = "GRIN Lens"
IMPLANT_TYPE_OPTIONS: Final[tuple[str, ...]] = (
    CRANIAL_WINDOW_IMPLANT_TYPE,
    CRYSTAL_SKULL_IMPLANT_TYPE,
    ELECTRODE_IMPLANT_TYPE,
    GRIN_LENS_IMPLANT_TYPE,
)
WELL_TYPE_OPTIONS: Final[tuple[str, ...]] = ("Cement", "3D Printed")
NOTE_UPLOAD_TYPE: Final[str] = "note_upload"
PHOTO_UPLOAD_TYPE: Final[str] = "photo_upload"
TAKEN_PHOTO_UPLOAD_TYPE: Final[str] = "taken_photo"
SURGERY_FILE_UPLOAD_TYPES: Final[tuple[str, ...]] = (
    NOTE_UPLOAD_TYPE,
    PHOTO_UPLOAD_TYPE,
    TAKEN_PHOTO_UPLOAD_TYPE,
)

CNN_PATTERN_TEXT: Final[str] = r"\d\d\d\d\d\d"
CNN_PATTERN: Final[re.Pattern[str]] = re.compile(rf"^{CNN_PATTERN_TEXT}$")
STOCK_TITER_PATTERN_TEXT: Final[str] = r"\d_\d\d_\d\d"
STOCK_TITER_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^{STOCK_TITER_PATTERN_TEXT}$"
)
SURGERY_TIME_PATTERN_TEXT: Final[str] = r"(?:[01]\d|2[0-3])[0-5]\d"
SURGERY_TIME_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^{SURGERY_TIME_PATTERN_TEXT}$"
)


class SurgeryValidationError(ValueError):
    """Raised when surgery form values do not make a valid payload."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def format_surgery_date(value: date) -> str:
    """Return a surgery date as ``YYYYMMDD``."""
    return value.strftime("%Y%m%d")


def format_surgery_time(value: time) -> str:
    """Return a surgery time as zero-padded ``HHMM``."""
    return value.strftime("%H%M")


def format_surgery_time_display(value: time) -> str:
    """Return a surgery time for display as ``HH:MM AM/PM``."""
    return value.strftime("%I:%M %p").lstrip("0")


def surgery_json_filename(animal_id: str, surgery_date: str) -> str:
    """Return the stable JSON filename for a surgery attachment."""
    return f"{animal_id}_surgery_{surgery_date}.json"


def surgery_record_file_token(payload: Mapping[str, Any]) -> str:
    """Return the dated or draft token used in surgery attachment filenames."""
    surgery_date = clean_string(payload.get(SURGERY_DATE_KEY))
    if surgery_date:
        return surgery_date

    draft_id = clean_string(payload.get(SURGERY_DRAFT_ID_KEY))
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


def _validate_cnn(
    *,
    field_name: str,
    value: str,
    errors: list[str],
) -> None:
    if not value:
        errors.append(f"{field_name} is required.")
        return

    if not CNN_PATTERN.fullmatch(value):
        errors.append(
            f"{field_name} must match {CNN_PATTERN_TEXT}, for example 123456."
        )


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


def _validate_number(
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
    return float(value)


def _format_date_or_error(
    *,
    field_name: str,
    value: date | None,
    errors: list[str],
) -> str:
    if not isinstance(value, date):
        errors.append(f"{field_name} must be selected.")
        return ""
    return format_surgery_date(value)


def _format_time_or_error(
    *,
    field_name: str,
    value: time | None,
    errors: list[str],
) -> str:
    if not isinstance(value, time):
        errors.append(f"{field_name} must be selected.")
        return ""
    return format_surgery_time(value)


def medication_volume_value(raw_medication: Mapping[str, object]) -> object:
    """Return the medication volume, accepting the legacy ``volume`` key."""
    if VOLUME_KEY in raw_medication:
        return raw_medication.get(VOLUME_KEY)
    return raw_medication.get(LEGACY_VOLUME_KEY)


def normalize_surgery_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a surgery payload with current medication field names."""
    normalized = dict(payload)
    raw_medications = normalized.get(MEDICATIONS_KEY)
    if not isinstance(raw_medications, list):
        return normalized

    medications: list[Any] = []
    for raw_medication in raw_medications:
        if not isinstance(raw_medication, Mapping):
            medications.append(raw_medication)
            continue

        medication = dict(raw_medication)
        if VOLUME_KEY not in medication and LEGACY_VOLUME_KEY in medication:
            medication[VOLUME_KEY] = medication[LEGACY_VOLUME_KEY]
        medication.pop(LEGACY_VOLUME_KEY, None)
        medications.append(medication)

    normalized[MEDICATIONS_KEY] = medications
    return normalized


def _validate_medications(
    raw_medications: Iterable[Mapping[str, object]],
    errors: list[str],
    *,
    allow_incomplete: bool = False,
) -> list[dict[str, str | float | None]]:
    medications: list[dict[str, str | float | None]] = []

    for index, raw_medication in enumerate(raw_medications, start=1):
        medication = clean_string(raw_medication.get(MEDICATION_KEY))
        if not medication:
            errors.append(f"{MEDICATION_KEY}_{index} is required.")

        conc_mgml = _validate_non_negative_number(
            field_name=f"{CONC_MGML_KEY}_{index}",
            value=raw_medication.get(CONC_MGML_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        volume = _validate_non_negative_number(
            field_name=f"{VOLUME_KEY}_{index}",
            value=medication_volume_value(raw_medication),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        medications.append(
            {
                MEDICATION_KEY: medication,
                CONC_MGML_KEY: conc_mgml,
                VOLUME_KEY: volume,
            }
        )

    return medications


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

        if upload_type and upload_type not in SURGERY_FILE_UPLOAD_TYPES:
            errors.append(
                f"{ATTACHMENTS_KEY}_{index}.{UPLOAD_TYPE_KEY} must be one of "
                + ", ".join(SURGERY_FILE_UPLOAD_TYPES)
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


def _validate_stock_titer(
    *,
    field_name: str,
    value: str,
    errors: list[str],
) -> None:
    if not value:
        errors.append(f"{field_name} is required.")
        return

    if not STOCK_TITER_PATTERN.fullmatch(value):
        errors.append(
            f"{field_name} must match {STOCK_TITER_PATTERN_TEXT}, "
            "for example 2_10_13."
        )


def _validate_virus_entries(
    raw_viruses: object,
    *,
    field_prefix: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> list[dict[str, str | float | None]]:
    viruses: list[dict[str, str | float | None]] = []
    for virus_index, raw_virus in enumerate(
        _raw_list(
            raw_viruses,
            field_name=f"{field_prefix}.{VIRUSES_KEY}",
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{field_prefix}.{VIRUSES_KEY}_{virus_index}"
        virus_payload = _raw_mapping(
            raw_virus,
            field_name=field_name,
            errors=errors,
        )
        if virus_payload is None:
            continue

        virus = clean_string(virus_payload.get(VIRUS_KEY))
        virus_source = clean_string(virus_payload.get(VIRUS_SOURCE_KEY))
        virus_id = clean_string(virus_payload.get(VIRUS_ID_KEY))
        virus_stock = clean_string(virus_payload.get(VIRUS_STOCK_KEY))
        stock_titer = clean_string(virus_payload.get(STOCK_TITER_KEY))
        dilution = clean_string(virus_payload.get(DILUTION_KEY))

        for required_key, value in (
            (VIRUS_KEY, virus),
            (VIRUS_SOURCE_KEY, virus_source),
            (VIRUS_ID_KEY, virus_id),
            (VIRUS_STOCK_KEY, virus_stock),
            (DILUTION_KEY, dilution),
        ):
            _validate_required(
                field_name=f"{field_name}.{required_key}",
                value=value,
                errors=errors,
            )
        _validate_stock_titer(
            field_name=f"{field_name}.{STOCK_TITER_KEY}",
            value=stock_titer,
            errors=errors,
        )
        infusion_rate_nlmin = _validate_non_negative_number(
            field_name=f"{field_name}.{INFUSION_RATE_NLMIN_KEY}",
            value=virus_payload.get(INFUSION_RATE_NLMIN_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        viruses.append(
            {
                VIRUS_KEY: virus,
                VIRUS_SOURCE_KEY: virus_source,
                VIRUS_ID_KEY: virus_id,
                VIRUS_STOCK_KEY: virus_stock,
                STOCK_TITER_KEY: stock_titer,
                DILUTION_KEY: dilution,
                INFUSION_RATE_NLMIN_KEY: infusion_rate_nlmin,
            }
        )
    return viruses


def _validate_infusion_entries(
    raw_infusions: object,
    *,
    field_prefix: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> list[dict[str, str | float | None]]:
    infusions: list[dict[str, str | float | None]] = []
    for infusion_index, raw_infusion in enumerate(
        _raw_list(
            raw_infusions,
            field_name=f"{field_prefix}.{INFUSIONS_KEY}",
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{field_prefix}.{INFUSIONS_KEY}_{infusion_index}"
        infusion_payload = _raw_mapping(
            raw_infusion,
            field_name=field_name,
            errors=errors,
        )
        if infusion_payload is None:
            continue

        ap = _validate_number(
            field_name=f"{field_name}.{AP_KEY}",
            value=infusion_payload.get(AP_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        ml = _validate_number(
            field_name=f"{field_name}.{ML_KEY}",
            value=infusion_payload.get(ML_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        dv = _validate_number(
            field_name=f"{field_name}.{DV_KEY}",
            value=infusion_payload.get(DV_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        infusion_volume_nl = _validate_non_negative_number(
            field_name=f"{field_name}.{INFUSION_VOLUME_NL_KEY}",
            value=infusion_payload.get(INFUSION_VOLUME_NL_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        post_infusion_flow_test = clean_string(
            infusion_payload.get(POST_INFUSION_FLOW_TEST_KEY)
        )
        if post_infusion_flow_test not in POST_INFUSION_FLOW_TEST_OPTIONS:
            errors.append(
                f"{field_name}.{POST_INFUSION_FLOW_TEST_KEY} must be one of "
                + ", ".join(POST_INFUSION_FLOW_TEST_OPTIONS)
                + "."
            )
        infusions.append(
            {
                AP_KEY: ap,
                ML_KEY: ml,
                DV_KEY: dv,
                INFUSION_VOLUME_NL_KEY: infusion_volume_nl,
                POST_INFUSION_FLOW_TEST_KEY: post_infusion_flow_test,
                NOTES_KEY: clean_string(infusion_payload.get(NOTES_KEY)),
            }
        )
    return infusions


def _validate_injection_entries(
    raw_injections: object,
    *,
    field_prefix: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> list[dict[str, object]]:
    injections: list[dict[str, object]] = []
    for injection_index, raw_injection in enumerate(
        _raw_list(
            raw_injections,
            field_name=f"{field_prefix}.{INJECTIONS_KEY}",
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{field_prefix}.{INJECTIONS_KEY}_{injection_index}"
        injection_payload = _raw_mapping(
            raw_injection,
            field_name=field_name,
            errors=errors,
        )
        if injection_payload is None:
            continue

        site = clean_string(injection_payload.get(SITE_KEY))
        hemisphere = clean_string(injection_payload.get(HEMISPHERE_KEY))
        _validate_required(
            field_name=f"{field_name}.{SITE_KEY}",
            value=site,
            errors=errors,
        )
        if hemisphere not in HEMISPHERE_OPTIONS:
            errors.append(
                f"{field_name}.{HEMISPHERE_KEY} must be one of "
                + ", ".join(HEMISPHERE_OPTIONS)
                + "."
            )

        injections.append(
            {
                SITE_KEY: site,
                HEMISPHERE_KEY: hemisphere,
                VIRUSES_KEY: _validate_virus_entries(
                    injection_payload.get(VIRUSES_KEY),
                    field_prefix=field_name,
                    errors=errors,
                    allow_incomplete=allow_incomplete,
                ),
                INFUSIONS_KEY: _validate_infusion_entries(
                    injection_payload.get(INFUSIONS_KEY),
                    field_prefix=field_name,
                    errors=errors,
                    allow_incomplete=allow_incomplete,
                ),
            }
        )
    return injections


def _validate_cranial_window(
    raw_cranial_window: object,
    *,
    field_prefix: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> dict[str, str | float | None]:
    cranial_window = _raw_mapping(
        raw_cranial_window,
        field_name=f"{field_prefix}.{CRANIAL_WINDOW_KEY}",
        errors=errors,
    )
    if cranial_window is None:
        return {}

    headplate_type = clean_string(cranial_window.get(HEADPLATE_TYPE_KEY))
    coverslip_type = clean_string(cranial_window.get(COVERSLIP_TYPE_KEY))
    coverslip_diameter = clean_string(
        cranial_window.get(COVERSLIP_DIAMETER_KEY)
    )
    coverslip_thickness = clean_string(
        cranial_window.get(COVERSLIP_THICKNESS_KEY)
    )
    region = clean_string(cranial_window.get(REGION_KEY))
    for required_key, value in (
        (HEADPLATE_TYPE_KEY, headplate_type),
        (COVERSLIP_TYPE_KEY, coverslip_type),
        (COVERSLIP_DIAMETER_KEY, coverslip_diameter),
        (COVERSLIP_THICKNESS_KEY, coverslip_thickness),
        (REGION_KEY, region),
    ):
        _validate_required(
            field_name=f"{field_prefix}.{CRANIAL_WINDOW_KEY}.{required_key}",
            value=value,
            errors=errors,
        )

    center_ap = _validate_number(
        field_name=f"{field_prefix}.{CRANIAL_WINDOW_KEY}.{CENTER_AP_KEY}",
        value=cranial_window.get(CENTER_AP_KEY),
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    center_ml = _validate_number(
        field_name=f"{field_prefix}.{CRANIAL_WINDOW_KEY}.{CENTER_ML_KEY}",
        value=cranial_window.get(CENTER_ML_KEY),
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    well_type = clean_string(cranial_window.get(WELL_TYPE_KEY))
    if well_type not in WELL_TYPE_OPTIONS:
        errors.append(
            f"{field_prefix}.{CRANIAL_WINDOW_KEY}.{WELL_TYPE_KEY} "
            "must be one of " + ", ".join(WELL_TYPE_OPTIONS) + "."
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
        NOTES_KEY: clean_string(cranial_window.get(NOTES_KEY)),
    }


def _validate_crystal_skull(
    raw_crystal_skull: object,
    *,
    field_prefix: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> dict[str, str | float | None]:
    crystal_skull = _raw_mapping(
        raw_crystal_skull,
        field_name=f"{field_prefix}.{CRYSTAL_SKULL_KEY}",
        errors=errors,
    )
    if crystal_skull is None:
        return {}

    headplate_type = clean_string(crystal_skull.get(HEADPLATE_TYPE_KEY))
    cs_type = clean_string(crystal_skull.get(CS_TYPE_KEY))
    well_type = clean_string(crystal_skull.get(WELL_TYPE_KEY))
    for required_key, value in (
        (HEADPLATE_TYPE_KEY, headplate_type),
        (CS_TYPE_KEY, cs_type),
        (WELL_TYPE_KEY, well_type),
    ):
        _validate_required(
            field_name=f"{field_prefix}.{CRYSTAL_SKULL_KEY}.{required_key}",
            value=value,
            errors=errors,
        )

    front_ap = _validate_number(
        field_name=f"{field_prefix}.{CRYSTAL_SKULL_KEY}.{FRONT_AP_KEY}",
        value=crystal_skull.get(FRONT_AP_KEY),
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    left_ml = _validate_number(
        field_name=f"{field_prefix}.{CRYSTAL_SKULL_KEY}.{LEFT_ML_KEY}",
        value=crystal_skull.get(LEFT_ML_KEY),
        errors=errors,
        allow_incomplete=allow_incomplete,
    )

    return {
        HEADPLATE_TYPE_KEY: headplate_type,
        CS_TYPE_KEY: cs_type,
        FRONT_AP_KEY: front_ap,
        LEFT_ML_KEY: left_ml,
        WELL_TYPE_KEY: well_type,
    }


def _validate_electrode_entries(
    raw_electrodes: object,
    *,
    field_prefix: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> list[dict[str, str | float | None]]:
    electrodes: list[dict[str, str | float | None]] = []
    for electrode_index, raw_electrode in enumerate(
        _raw_list(
            raw_electrodes,
            field_name=f"{field_prefix}.{ELECTRODES_KEY}",
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{field_prefix}.{ELECTRODES_KEY}_{electrode_index}"
        electrode_payload = _raw_mapping(
            raw_electrode,
            field_name=field_name,
            errors=errors,
        )
        if electrode_payload is None:
            continue

        electrode_type = clean_string(
            electrode_payload.get(ELECTRODE_TYPE_KEY)
        )
        if electrode_type not in ELECTRODE_TYPE_OPTIONS:
            errors.append(
                f"{field_name}.{ELECTRODE_TYPE_KEY} must be one of "
                + ", ".join(ELECTRODE_TYPE_OPTIONS)
                + "."
            )

        probe_model = clean_string(electrode_payload.get(PROBE_MODEL_KEY))
        probe_id = clean_string(electrode_payload.get(PROBE_ID_KEY))
        electrode_site = clean_string(
            electrode_payload.get(ELECTRODE_SITE_KEY)
        )
        electrode_hemisphere = clean_string(
            electrode_payload.get(ELECTRODE_HEMISPHERE_KEY)
        )
        pitch = clean_string(electrode_payload.get(PITCH_KEY))
        yaw = clean_string(electrode_payload.get(YAW_KEY))
        roll = clean_string(electrode_payload.get(ROLL_KEY))
        ground = clean_string(electrode_payload.get(GROUND_KEY))
        reference = clean_string(electrode_payload.get(REFERENCE_KEY))
        for required_key, value in (
            (PROBE_MODEL_KEY, probe_model),
            (PROBE_ID_KEY, probe_id),
            (ELECTRODE_SITE_KEY, electrode_site),
            (PITCH_KEY, pitch),
            (YAW_KEY, yaw),
            (ROLL_KEY, roll),
            (GROUND_KEY, ground),
            (REFERENCE_KEY, reference),
        ):
            _validate_required(
                field_name=f"{field_name}.{required_key}",
                value=value,
                errors=errors,
            )

        if electrode_hemisphere not in HEMISPHERE_OPTIONS:
            errors.append(
                f"{field_name}.{ELECTRODE_HEMISPHERE_KEY} must be one of "
                + ", ".join(HEMISPHERE_OPTIONS)
                + "."
            )

        ap = _validate_number(
            field_name=f"{field_name}.{AP_KEY}",
            value=electrode_payload.get(AP_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        ml = _validate_number(
            field_name=f"{field_name}.{ML_KEY}",
            value=electrode_payload.get(ML_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        dv = _validate_number(
            field_name=f"{field_name}.{DV_KEY}",
            value=electrode_payload.get(DV_KEY),
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        electrodes.append(
            {
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
                NOTES_KEY: clean_string(electrode_payload.get(NOTES_KEY)),
            }
        )
    return electrodes


def _unsupported_implant_message(implant_type: str) -> str:
    label = implant_type or "Implant"
    return f"{label} implant procedures are not implemented yet."


def _validate_implant_procedure(
    procedure_payload: Mapping[str, object],
    *,
    field_name: str,
    surgery_category: str,
    errors: list[str],
    allow_incomplete: bool = False,
) -> dict[str, object]:
    implant_type = clean_string(procedure_payload.get(IMPLANT_TYPE_KEY))
    if not implant_type:
        errors.append(f"{field_name}.{IMPLANT_TYPE_KEY} is required.")
        return {
            SURGERY_CATEGORY_KEY: surgery_category,
            IMPLANT_TYPE_KEY: implant_type,
        }

    procedure: dict[str, object] = {
        SURGERY_CATEGORY_KEY: surgery_category,
        IMPLANT_TYPE_KEY: implant_type,
    }
    if implant_type == CRANIAL_WINDOW_IMPLANT_TYPE:
        procedure[CRANIAL_WINDOW_KEY] = _validate_cranial_window(
            procedure_payload.get(CRANIAL_WINDOW_KEY),
            field_prefix=field_name,
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        return procedure

    if implant_type == CRYSTAL_SKULL_IMPLANT_TYPE:
        procedure[CRYSTAL_SKULL_KEY] = _validate_crystal_skull(
            procedure_payload.get(CRYSTAL_SKULL_KEY),
            field_prefix=field_name,
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        return procedure

    if implant_type == ELECTRODE_IMPLANT_TYPE:
        procedure[ELECTRODES_KEY] = _validate_electrode_entries(
            procedure_payload.get(ELECTRODES_KEY),
            field_prefix=field_name,
            errors=errors,
            allow_incomplete=allow_incomplete,
        )
        return procedure

    errors.append(_unsupported_implant_message(implant_type))
    return procedure


def _validate_surgical_procedures(
    raw_procedures: object,
    errors: list[str],
    *,
    allow_incomplete: bool = False,
) -> list[dict[str, object]]:
    procedures: list[dict[str, object]] = []
    for procedure_index, raw_procedure in enumerate(
        _raw_list(
            raw_procedures,
            field_name=SURGICAL_PROCEDURES_KEY,
            errors=errors,
        ),
        start=1,
    ):
        field_name = f"{SURGICAL_PROCEDURES_KEY}_{procedure_index}"
        procedure_payload = _raw_mapping(
            raw_procedure,
            field_name=field_name,
            errors=errors,
        )
        if procedure_payload is None:
            continue

        surgery_category = clean_string(
            procedure_payload.get(SURGERY_CATEGORY_KEY)
        )
        if surgery_category == IMPLANT_CATEGORY:
            procedures.append(
                _validate_implant_procedure(
                    procedure_payload,
                    field_name=field_name,
                    surgery_category=surgery_category,
                    errors=errors,
                    allow_incomplete=allow_incomplete,
                )
            )
            continue
        if surgery_category != VIRAL_INJECTION_CATEGORY:
            errors.append(
                f"{field_name}.{SURGERY_CATEGORY_KEY} must be one of "
                + ", ".join(SURGERY_CATEGORY_OPTIONS)
                + "."
            )
            procedures.append({SURGERY_CATEGORY_KEY: surgery_category})
            continue

        procedures.append(
            {
                SURGERY_CATEGORY_KEY: surgery_category,
                INJECTIONS_KEY: _validate_injection_entries(
                    procedure_payload.get(INJECTIONS_KEY),
                    field_prefix=field_name,
                    errors=errors,
                    allow_incomplete=allow_incomplete,
                ),
            }
        )
    return procedures


def build_surgery_payload(
    *,
    project_id: str,
    investigator: str,
    animal_id: str,
    ear_tag: str,
    surgeon: str,
    surgery_date: date | None,
    preop_cnn: str,
    postop_cnn: str,
    general_notes: str = "",
    attachments: Iterable[Mapping[str, object]] = (),
    weight_pre_g: int | float | None,
    weight_post_g: int | float | None,
    medications: Iterable[Mapping[str, object]],
    start_time: time | None,
    end_time: time | None,
    bregma_lambda_dist_mm: int | float | None,
    surgical_procedures: object,
    allow_incomplete: bool = False,
    draft_id: str = "",
) -> dict[str, Any]:
    """Validate form values and return the flat surgery JSON payload."""
    cleaned_project_id = clean_string(project_id)
    cleaned_investigator = clean_string(investigator)
    cleaned_animal_id = clean_string(animal_id)
    cleaned_ear_tag = clean_string(ear_tag)
    cleaned_surgeon = clean_string(surgeon)
    cleaned_preop_cnn = clean_string(preop_cnn)
    cleaned_postop_cnn = clean_string(postop_cnn)
    cleaned_general_notes = clean_string(general_notes)
    cleaned_draft_id = clean_string(draft_id)
    errors: list[str] = []

    for field_name, value in (
        (PROJECT_ID_KEY, cleaned_project_id),
        (INVESTIGATOR_KEY, cleaned_investigator),
        (ANIMAL_ID_LABEL, cleaned_animal_id),
        (EAR_TAG_LABEL, cleaned_ear_tag),
        (SURGEON_KEY, cleaned_surgeon),
    ):
        _validate_required(
            field_name=field_name,
            value=value,
            errors=errors,
        )

    formatted_surgery_date = _format_date_or_error(
        field_name=SURGERY_DATE_KEY,
        value=surgery_date,
        errors=errors,
    )
    _validate_cnn(
        field_name=PREOP_CNN_LABEL,
        value=cleaned_preop_cnn,
        errors=errors,
    )
    _validate_cnn(
        field_name=POSTOP_CNN_LABEL,
        value=cleaned_postop_cnn,
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

    cleaned_weight_pre_g = _validate_non_negative_number(
        field_name=WEIGHT_PRE_G_KEY,
        value=weight_pre_g,
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    cleaned_weight_post_g = _validate_non_negative_number(
        field_name=WEIGHT_POST_G_KEY,
        value=weight_post_g,
        errors=errors,
        allow_incomplete=allow_incomplete,
    )
    cleaned_bregma_lambda_dist_mm = _validate_optional_non_negative_number(
        field_name=BREGMA_LAMBDA_DIST_MM_KEY,
        value=bregma_lambda_dist_mm,
        errors=errors,
    )
    cleaned_medications = _validate_medications(
        medications,
        errors,
        allow_incomplete=allow_incomplete,
    )
    cleaned_surgical_procedures = _validate_surgical_procedures(
        surgical_procedures,
        errors,
        allow_incomplete=allow_incomplete,
    )
    cleaned_attachments = _validate_attachment_references(
        attachments,
        errors,
    )

    if errors and not allow_incomplete:
        raise SurgeryValidationError(errors)

    payload: dict[str, Any] = {
        PROJECT_ID_KEY: cleaned_project_id,
        "investigator": cleaned_investigator,
        ANIMAL_ID_KEY: cleaned_animal_id,
        EAR_TAG_KEY: cleaned_ear_tag,
        SURGEON_KEY: cleaned_surgeon,
        SURGERY_DATE_KEY: formatted_surgery_date,
        GENERAL_NOTES_KEY: cleaned_general_notes,
        ATTACHMENTS_KEY: cleaned_attachments,
        PREOP_CNN_KEY: cleaned_preop_cnn,
        POSTOP_CNN_KEY: cleaned_postop_cnn,
        WEIGHT_PRE_G_KEY: cleaned_weight_pre_g,
        WEIGHT_POST_G_KEY: cleaned_weight_post_g,
        MEDICATIONS_KEY: cleaned_medications,
        START_TIME_KEY: formatted_start_time,
        END_TIME_KEY: formatted_end_time,
        BREGMA_LAMBDA_DIST_MM_KEY: cleaned_bregma_lambda_dist_mm,
        SURGICAL_PROCEDURES_KEY: cleaned_surgical_procedures,
    }

    if not allow_incomplete:
        return payload

    payload[SURGERY_STATUS_KEY] = (
        SURGERY_STATUS_INCOMPLETE if errors else SURGERY_STATUS_COMPLETE
    )
    payload[SURGERY_VALIDATION_ERRORS_KEY] = list(errors)
    if errors and cleaned_draft_id and not formatted_surgery_date:
        payload[SURGERY_DRAFT_ID_KEY] = cleaned_draft_id
    return payload


def medication_names(payload: Mapping[str, Any]) -> list[str]:
    """Return medication names from a surgery payload in entry order."""
    raw_medications = payload.get(MEDICATIONS_KEY, [])
    if not isinstance(raw_medications, list):
        return []

    names: list[str] = []
    for raw_medication in raw_medications:
        if isinstance(raw_medication, Mapping):
            medication = clean_string(raw_medication.get(MEDICATION_KEY))
            if medication:
                names.append(medication)
    return names


def procedure_option_values(
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
]:
    """Return reusable surgery option values from a payload."""
    raw_procedures = payload.get(SURGICAL_PROCEDURES_KEY, [])
    if not isinstance(raw_procedures, list):
        return [], [], [], [], [], [], [], [], [], [], [], []

    sites: list[str] = []
    viruses: list[str] = []
    virus_sources: list[str] = []
    headplate_types: list[str] = []
    coverslip_types: list[str] = []
    coverslip_diameters: list[str] = []
    coverslip_thicknesses: list[str] = []
    cranial_window_regions: list[str] = []
    cs_types: list[str] = []
    crystal_skull_well_types: list[str] = []
    probe_models: list[str] = []
    electrode_sites: list[str] = []
    for raw_procedure in raw_procedures:
        if not isinstance(raw_procedure, Mapping):
            continue
        raw_cranial_window = raw_procedure.get(CRANIAL_WINDOW_KEY)
        if isinstance(raw_cranial_window, Mapping):
            headplate_type = clean_string(
                raw_cranial_window.get(HEADPLATE_TYPE_KEY)
            )
            coverslip_type = clean_string(
                raw_cranial_window.get(COVERSLIP_TYPE_KEY)
            )
            coverslip_diameter = clean_string(
                raw_cranial_window.get(COVERSLIP_DIAMETER_KEY)
            )
            coverslip_thickness = clean_string(
                raw_cranial_window.get(COVERSLIP_THICKNESS_KEY)
            )
            region = clean_string(raw_cranial_window.get(REGION_KEY))
            if headplate_type:
                headplate_types.append(headplate_type)
            if coverslip_type:
                coverslip_types.append(coverslip_type)
            if coverslip_diameter:
                coverslip_diameters.append(coverslip_diameter)
            if coverslip_thickness:
                coverslip_thicknesses.append(coverslip_thickness)
            if region:
                cranial_window_regions.append(region)

        raw_crystal_skull = raw_procedure.get(CRYSTAL_SKULL_KEY)
        if isinstance(raw_crystal_skull, Mapping):
            headplate_type = clean_string(
                raw_crystal_skull.get(HEADPLATE_TYPE_KEY)
            )
            cs_type = clean_string(raw_crystal_skull.get(CS_TYPE_KEY))
            well_type = clean_string(raw_crystal_skull.get(WELL_TYPE_KEY))
            if headplate_type:
                headplate_types.append(headplate_type)
            if cs_type:
                cs_types.append(cs_type)
            if well_type:
                crystal_skull_well_types.append(well_type)

        raw_electrodes = raw_procedure.get(ELECTRODES_KEY, [])
        if isinstance(raw_electrodes, list):
            for raw_electrode in raw_electrodes:
                if not isinstance(raw_electrode, Mapping):
                    continue
                probe_model = clean_string(raw_electrode.get(PROBE_MODEL_KEY))
                electrode_site = clean_string(
                    raw_electrode.get(ELECTRODE_SITE_KEY)
                )
                if probe_model:
                    probe_models.append(probe_model)
                if electrode_site:
                    electrode_sites.append(electrode_site)

        raw_injections = raw_procedure.get(INJECTIONS_KEY, [])
        if not isinstance(raw_injections, list):
            continue
        for raw_injection in raw_injections:
            if not isinstance(raw_injection, Mapping):
                continue
            site = clean_string(raw_injection.get(SITE_KEY))
            if site:
                sites.append(site)
            raw_viruses = raw_injection.get(VIRUSES_KEY, [])
            if not isinstance(raw_viruses, list):
                continue
            for raw_virus in raw_viruses:
                if not isinstance(raw_virus, Mapping):
                    continue
                virus = clean_string(raw_virus.get(VIRUS_KEY))
                virus_source = clean_string(raw_virus.get(VIRUS_SOURCE_KEY))
                if virus:
                    viruses.append(virus)
                if virus_source:
                    virus_sources.append(virus_source)
    return (
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
    )


def with_surgery_options(
    config: Mapping[str, Any],
    *,
    surgeon: str,
    medications: Iterable[str] = (),
    sites: Iterable[str] = (),
    viruses: Iterable[str] = (),
    virus_sources: Iterable[str] = (),
    headplate_types: Iterable[str] = (),
    coverslip_types: Iterable[str] = (),
    coverslip_diameters: Iterable[str] = (),
    coverslip_thicknesses: Iterable[str] = (),
    cranial_window_regions: Iterable[str] = (),
    cs_types: Iterable[str] = (),
    crystal_skull_well_types: Iterable[str] = (),
    probe_models: Iterable[str] = (),
    electrode_sites: Iterable[str] = (),
) -> tuple[dict[str, Any], bool]:
    """Return config with reusable surgery options and whether it changed."""
    updated_config = deepcopy(dict(config))
    options = normalize_options(updated_config.get(OPTIONS_KEY))
    original_options = deepcopy(options)

    add_option(options, SURGEON_OPTIONS_KEY, surgeon)
    for medication in medications:
        add_option(options, MEDICATION_OPTIONS_KEY, medication)
    for site in sites:
        add_option(options, SITE_OPTIONS_KEY, site)
    for virus in viruses:
        add_option(options, VIRUS_OPTIONS_KEY, virus)
    for virus_source in virus_sources:
        add_option(options, VIRUS_SOURCE_OPTIONS_KEY, virus_source)
    for headplate_type in headplate_types:
        add_option(options, HEADPLATE_TYPE_OPTIONS_KEY, headplate_type)
    for coverslip_type in coverslip_types:
        add_option(options, COVERSLIP_TYPE_OPTIONS_KEY, coverslip_type)
    for coverslip_diameter in coverslip_diameters:
        add_option(
            options,
            COVERSLIP_DIAMETER_OPTIONS_KEY,
            coverslip_diameter,
        )
    for coverslip_thickness in coverslip_thicknesses:
        add_option(
            options,
            COVERSLIP_THICKNESS_OPTIONS_KEY,
            coverslip_thickness,
        )
    for cranial_window_region in cranial_window_regions:
        add_option(
            options,
            CRANIAL_WINDOW_REGION_OPTIONS_KEY,
            cranial_window_region,
        )
    for cs_type in cs_types:
        add_option(options, CS_TYPE_OPTIONS_KEY, cs_type)
    for crystal_skull_well_type in crystal_skull_well_types:
        add_option(
            options,
            CRYSTAL_SKULL_WELL_TYPE_OPTIONS_KEY,
            crystal_skull_well_type,
        )
    for probe_model in probe_models:
        add_option(options, PROBE_MODEL_OPTIONS_KEY, probe_model)
    for electrode_site in electrode_sites:
        add_option(options, ELECTRODE_SITE_OPTIONS_KEY, electrode_site)

    updated_config[OPTIONS_KEY] = options
    return updated_config, options != original_options


def with_surgeon_options(
    config: Mapping[str, Any],
    *,
    surgeon: str,
) -> tuple[dict[str, Any], bool]:
    """Return config with a reusable surgeon option and whether it changed."""
    return with_surgery_options(config, surgeon=surgeon)
