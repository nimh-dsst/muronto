"""Surgery record validation and payload helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import date, time
from typing import Any, Final

from muronto_app.config import (
    INVESTIGATOR_KEY,
    MEDICATION_OPTIONS_KEY,
    OPTIONS_KEY,
    PROJECT_ID_KEY,
    SURGEON_OPTIONS_KEY,
    add_option,
    clean_string,
    normalize_options,
)
from muronto_app.subject import ANIMAL_ID_KEY, EAR_TAG_KEY

SURGERY_ATTACHMENT_CAPTION: Final[str] = "muronto_surgery"

SURGEON_KEY: Final[str] = "surgeon"
SURGERY_DATE_KEY: Final[str] = "surgery_date"
PREOP_CNN_KEY: Final[str] = "preop_cnn"
POSTOP_CNN_KEY: Final[str] = "postop_cnn"
WEIGHT_PRE_G_KEY: Final[str] = "weight_pre_g"
WEIGHT_POST_G_KEY: Final[str] = "weight_post_g"
MEDICATIONS_KEY: Final[str] = "medications"
MEDICATION_KEY: Final[str] = "medication"
CONC_MGML_KEY: Final[str] = "conc_mgml"
VOLUME_KEY: Final[str] = "volume"
START_TIME_KEY: Final[str] = "start_time"
END_TIME_KEY: Final[str] = "end_time"
BREGMA_LAMBDA_DIST_MM_KEY: Final[str] = "bregma_lambda_dist_mm"

CNN_PATTERN_TEXT: Final[str] = r"\d\d\d\d\d\d"
CNN_PATTERN: Final[re.Pattern[str]] = re.compile(rf"^{CNN_PATTERN_TEXT}$")


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


def surgery_json_filename(animal_id: str, surgery_date: str) -> str:
    """Return the stable JSON filename for a surgery attachment."""
    return f"{animal_id}_surgery_{surgery_date}.json"


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
) -> float:
    if value is None:
        errors.append(f"{field_name} is required.")
        return 0.0
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{field_name} must be a number.")
        return 0.0

    numeric_value = float(value)
    if numeric_value < 0:
        errors.append(f"{field_name} must be non-negative.")
    return numeric_value


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


def _validate_medications(
    raw_medications: Iterable[Mapping[str, object]],
    errors: list[str],
) -> list[dict[str, str | float]]:
    medications: list[dict[str, str | float]] = []

    for index, raw_medication in enumerate(raw_medications, start=1):
        medication = clean_string(raw_medication.get(MEDICATION_KEY))
        if not medication:
            errors.append(f"{MEDICATION_KEY}_{index} is required.")

        conc_mgml = _validate_non_negative_number(
            field_name=f"{CONC_MGML_KEY}_{index}",
            value=raw_medication.get(CONC_MGML_KEY),
            errors=errors,
        )
        volume = _validate_non_negative_number(
            field_name=f"{VOLUME_KEY}_{index}",
            value=raw_medication.get(VOLUME_KEY),
            errors=errors,
        )
        medications.append(
            {
                MEDICATION_KEY: medication,
                CONC_MGML_KEY: conc_mgml,
                VOLUME_KEY: volume,
            }
        )

    if not medications:
        errors.append(f"{MEDICATIONS_KEY} must include at least one entry.")

    return medications


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
    weight_pre_g: int | float | None,
    weight_post_g: int | float | None,
    medications: Iterable[Mapping[str, object]],
    start_time: time | None,
    end_time: time | None,
    bregma_lambda_dist_mm: int | float | None,
) -> dict[str, Any]:
    """Validate form values and return the flat surgery JSON payload."""
    cleaned_project_id = clean_string(project_id)
    cleaned_investigator = clean_string(investigator)
    cleaned_animal_id = clean_string(animal_id)
    cleaned_ear_tag = clean_string(ear_tag)
    cleaned_surgeon = clean_string(surgeon)
    cleaned_preop_cnn = clean_string(preop_cnn)
    cleaned_postop_cnn = clean_string(postop_cnn)
    errors: list[str] = []

    for field_name, value in (
        (PROJECT_ID_KEY, cleaned_project_id),
        (INVESTIGATOR_KEY, cleaned_investigator),
        (ANIMAL_ID_KEY, cleaned_animal_id),
        (EAR_TAG_KEY, cleaned_ear_tag),
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
        field_name=PREOP_CNN_KEY,
        value=cleaned_preop_cnn,
        errors=errors,
    )
    _validate_cnn(
        field_name=POSTOP_CNN_KEY,
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
    )
    cleaned_weight_post_g = _validate_non_negative_number(
        field_name=WEIGHT_POST_G_KEY,
        value=weight_post_g,
        errors=errors,
    )
    cleaned_bregma_lambda_dist_mm = _validate_non_negative_number(
        field_name=BREGMA_LAMBDA_DIST_MM_KEY,
        value=bregma_lambda_dist_mm,
        errors=errors,
    )
    cleaned_medications = _validate_medications(medications, errors)

    if errors:
        raise SurgeryValidationError(errors)

    return {
        PROJECT_ID_KEY: cleaned_project_id,
        "investigator": cleaned_investigator,
        ANIMAL_ID_KEY: cleaned_animal_id,
        EAR_TAG_KEY: cleaned_ear_tag,
        SURGEON_KEY: cleaned_surgeon,
        SURGERY_DATE_KEY: formatted_surgery_date,
        PREOP_CNN_KEY: cleaned_preop_cnn,
        POSTOP_CNN_KEY: cleaned_postop_cnn,
        WEIGHT_PRE_G_KEY: cleaned_weight_pre_g,
        WEIGHT_POST_G_KEY: cleaned_weight_post_g,
        MEDICATIONS_KEY: cleaned_medications,
        START_TIME_KEY: formatted_start_time,
        END_TIME_KEY: formatted_end_time,
        BREGMA_LAMBDA_DIST_MM_KEY: cleaned_bregma_lambda_dist_mm,
    }


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


def with_surgery_options(
    config: Mapping[str, Any],
    *,
    surgeon: str,
    medications: Iterable[str] = (),
) -> tuple[dict[str, Any], bool]:
    """Return config with reusable surgery options and whether it changed."""
    updated_config = deepcopy(dict(config))
    options = normalize_options(updated_config.get(OPTIONS_KEY))
    original_options = deepcopy(options)

    add_option(options, SURGEON_OPTIONS_KEY, surgeon)
    for medication in medications:
        add_option(options, MEDICATION_OPTIONS_KEY, medication)

    updated_config[OPTIONS_KEY] = options
    return updated_config, options != original_options


def with_surgeon_options(
    config: Mapping[str, Any],
    *,
    surgeon: str,
) -> tuple[dict[str, Any], bool]:
    """Return config with a reusable surgeon option and whether it changed."""
    return with_surgery_options(config, surgeon=surgeon)
