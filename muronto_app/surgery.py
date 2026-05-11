"""Surgery record validation and payload helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from datetime import date
from typing import Any, Final

from muronto_app.config import (
    INVESTIGATOR_KEY,
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
) -> dict[str, str]:
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
    }


def with_surgeon_options(
    config: Mapping[str, Any],
    *,
    surgeon: str,
) -> tuple[dict[str, Any], bool]:
    """Return config with a reusable surgeon option and whether it changed."""
    updated_config = deepcopy(dict(config))
    options = normalize_options(updated_config.get(OPTIONS_KEY))
    original_options = deepcopy(options)

    add_option(options, SURGEON_OPTIONS_KEY, surgeon)

    updated_config[OPTIONS_KEY] = options
    return updated_config, options != original_options
