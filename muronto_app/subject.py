"""Subject record validation and payload helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from datetime import date
from typing import Any, Final

from muronto_app.config import (
    OPTIONS_KEY,
    SOURCE_TYPE_OPTIONS_KEY,
    STRAIN_OPTIONS_KEY,
    add_option,
    clean_string,
    normalize_options,
)

ANIMAL_ID_KEY: Final[str] = "animal_id"
EAR_TAG_KEY: Final[str] = "ear_tag"
CCN_KEY: Final[str] = "ccn"
SEX_KEY: Final[str] = "sex"
GENOTYPE_KEY: Final[str] = "genotype"
DOB_KEY: Final[str] = "dob"
DOW_KEY: Final[str] = "dow"
SOURCE_TYPE_KEY: Final[str] = SOURCE_TYPE_OPTIONS_KEY
PARENT_CCN_KEY: Final[str] = "parent_ccn"

SUBJECT_ATTACHMENT_CAPTION: Final[str] = "muronto_subject"

ANIMAL_ID_PATTERN_TEXT: Final[str] = r"\d\d\d-\d\d\d\d"
EAR_TAG_PATTERN_TEXT: Final[str] = r"\d\d\d"
CCN_PATTERN_TEXT: Final[str] = r"\d\d\d\d\d\d"

ANIMAL_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^{ANIMAL_ID_PATTERN_TEXT}$"
)
EAR_TAG_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^{EAR_TAG_PATTERN_TEXT}$"
)
CCN_PATTERN: Final[re.Pattern[str]] = re.compile(rf"^{CCN_PATTERN_TEXT}$")

GENOTYPE_OPTIONS: Final[tuple[str, ...]] = ("WT", "Het", "Homo", "Tg")
SEX_OPTIONS: Final[tuple[str, ...]] = ("M", "F")
PARENT_REQUIRED_SOURCE_TYPE: Final[str] = "Breeding"


class SubjectValidationError(ValueError):
    """Raised when subject form values do not make a valid subject payload."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def subject_json_filename(animal_id: str) -> str:
    """Return the stable JSON filename for a subject page attachment."""
    return f"{animal_id}.json"


def format_subject_date(value: date) -> str:
    """Return a subject date as ``YYYYMMDD``."""
    return value.strftime("%Y%m%d")


def _validate_pattern(
    *,
    field_name: str,
    value: str,
    pattern: re.Pattern[str],
    pattern_text: str,
    example: str,
    errors: list[str],
) -> None:
    if not value:
        errors.append(f"{field_name} is required.")
        return

    if not pattern.fullmatch(value):
        errors.append(
            f"{field_name} must match {pattern_text}, for example {example}."
        )


def _validate_optional_ccn(
    *,
    field_name: str,
    value: str,
    required: bool,
    errors: list[str],
) -> None:
    if required or value:
        _validate_pattern(
            field_name=field_name,
            value=value,
            pattern=CCN_PATTERN,
            pattern_text=CCN_PATTERN_TEXT,
            example="123456",
            errors=errors,
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
    return format_subject_date(value)


def build_subject_payload(
    *,
    animal_id: str,
    ear_tag: str,
    ccn: str,
    sex: str,
    strain_genotypes: Sequence[tuple[str, str]],
    dob: date | None,
    dow: date | None,
    source_type: str,
    parent_ccn: str = "",
) -> dict[str, str]:
    """Validate form values and return the flat subject JSON payload."""
    cleaned_animal_id = clean_string(animal_id)
    cleaned_ear_tag = clean_string(ear_tag)
    cleaned_ccn = clean_string(ccn)
    cleaned_sex = clean_string(sex)
    cleaned_source_type = clean_string(source_type)
    cleaned_parent_ccn = clean_string(parent_ccn)
    errors: list[str] = []

    _validate_pattern(
        field_name=ANIMAL_ID_KEY,
        value=cleaned_animal_id,
        pattern=ANIMAL_ID_PATTERN,
        pattern_text=ANIMAL_ID_PATTERN_TEXT,
        example="123-4567",
        errors=errors,
    )
    _validate_pattern(
        field_name=EAR_TAG_KEY,
        value=cleaned_ear_tag,
        pattern=EAR_TAG_PATTERN,
        pattern_text=EAR_TAG_PATTERN_TEXT,
        example="123",
        errors=errors,
    )
    _validate_pattern(
        field_name=CCN_KEY,
        value=cleaned_ccn,
        pattern=CCN_PATTERN,
        pattern_text=CCN_PATTERN_TEXT,
        example="123456",
        errors=errors,
    )

    if not cleaned_sex:
        errors.append(f"{SEX_KEY} is required.")
    elif cleaned_sex not in SEX_OPTIONS:
        errors.append(
            f"{SEX_KEY} must be one of " + ", ".join(SEX_OPTIONS) + "."
        )

    if not cleaned_source_type:
        errors.append(f"{SOURCE_TYPE_KEY} is required.")

    _validate_optional_ccn(
        field_name=PARENT_CCN_KEY,
        value=cleaned_parent_ccn,
        required=cleaned_source_type == PARENT_REQUIRED_SOURCE_TYPE,
        errors=errors,
    )

    if not strain_genotypes:
        errors.append("At least one strain/genotype pair is required.")

    cleaned_pairs: list[tuple[str, str]] = []
    for index, (raw_strain, raw_genotype) in enumerate(
        strain_genotypes,
        start=1,
    ):
        strain = clean_string(raw_strain)
        genotype = clean_string(raw_genotype)
        if not strain:
            errors.append(f"{STRAIN_OPTIONS_KEY}_{index} is required.")
        if not genotype:
            errors.append(f"{GENOTYPE_KEY}_{index} is required.")
        elif genotype not in GENOTYPE_OPTIONS:
            errors.append(
                f"{GENOTYPE_KEY}_{index} must be one of "
                + ", ".join(GENOTYPE_OPTIONS)
                + "."
            )
        cleaned_pairs.append((strain, genotype))

    formatted_dob = _format_date_or_error(
        field_name=DOB_KEY,
        value=dob,
        errors=errors,
    )
    formatted_dow = _format_date_or_error(
        field_name=DOW_KEY,
        value=dow,
        errors=errors,
    )

    if errors:
        raise SubjectValidationError(errors)

    payload = {
        ANIMAL_ID_KEY: cleaned_animal_id,
        EAR_TAG_KEY: cleaned_ear_tag,
        CCN_KEY: cleaned_ccn,
        SEX_KEY: cleaned_sex,
    }
    for index, (strain, genotype) in enumerate(cleaned_pairs, start=1):
        payload[f"{STRAIN_OPTIONS_KEY}_{index}"] = strain
        payload[f"{GENOTYPE_KEY}_{index}"] = genotype

    payload[DOB_KEY] = formatted_dob
    payload[DOW_KEY] = formatted_dow
    payload[SOURCE_TYPE_KEY] = cleaned_source_type
    payload[PARENT_CCN_KEY] = cleaned_parent_ccn
    return payload


def subject_strains(payload: Mapping[str, str]) -> list[str]:
    """Return strain values from a flat subject payload in suffix order."""
    strains: list[str] = []
    index = 1
    while f"{STRAIN_OPTIONS_KEY}_{index}" in payload:
        strains.append(payload[f"{STRAIN_OPTIONS_KEY}_{index}"])
        index += 1
    return strains


def with_subject_options(
    config: Mapping[str, Any],
    *,
    strains: Iterable[str],
    source_type: str,
) -> tuple[dict[str, Any], bool]:
    """Return config with subject options remembered and whether it changed."""
    updated_config = deepcopy(dict(config))
    options = normalize_options(updated_config.get(OPTIONS_KEY))
    original_options = deepcopy(options)

    for strain in strains:
        add_option(options, STRAIN_OPTIONS_KEY, strain)
    add_option(options, SOURCE_TYPE_OPTIONS_KEY, source_type)

    updated_config[OPTIONS_KEY] = options
    return updated_config, options != original_options
