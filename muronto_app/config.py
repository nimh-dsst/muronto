"""Configuration schema and normalization for ``muronto_config``."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any, Final, cast

CONFIG_PAGE_NAME: Final[str] = "muronto_config"
CONFIG_FILENAME: Final[str] = "muronto_config.json"
CONFIG_CAPTION: Final[str] = "muronto_config"
OTHER_CHOICE: Final[str] = "Other"

PROJECT_ID_KEY: Final[str] = "project_id"
PROJECT_NAME_KEY: Final[str] = "project_name"
LA_HOME_FOLDER_KEY: Final[str] = "LA_Home_Folder"
INVESTIGATOR_KEY: Final[str] = "Investigator"
PI_KEY: Final[str] = "PI"
SPECIES_KEY: Final[str] = "Species"
ASP_KEY: Final[str] = "ASP"
EMAIL_TO_INVESTIGATOR_KEY: Final[str] = "email_to_investigator"
OPTIONS_KEY: Final[str] = "options"
STRAIN_OPTIONS_KEY: Final[str] = "strain"
SOURCE_TYPE_OPTIONS_KEY: Final[str] = "source_type"

CONFIG_VALUE_KEYS: Final[tuple[str, ...]] = (
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    LA_HOME_FOLDER_KEY,
    INVESTIGATOR_KEY,
    PI_KEY,
    SPECIES_KEY,
    ASP_KEY,
)

SELECTABLE_VALUE_KEYS: Final[tuple[str, ...]] = (
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    INVESTIGATOR_KEY,
    SPECIES_KEY,
    ASP_KEY,
)

SUBJECT_OPTION_KEYS: Final[tuple[str, ...]] = (
    STRAIN_OPTIONS_KEY,
    SOURCE_TYPE_OPTIONS_KEY,
)

OPTION_KEYS: Final[tuple[str, ...]] = (
    *CONFIG_VALUE_KEYS,
    *SUBJECT_OPTION_KEYS,
)

DEFAULT_VALUES: Final[dict[str, str]] = {
    PROJECT_ID_KEY: "SEASIC",
    PROJECT_NAME_KEY: (
        "Sensory Evidence Accumulation Synaptic Integration in Cortex"
    ),
    LA_HOME_FOLDER_KEY: "",
    INVESTIGATOR_KEY: "APF",
    PI_KEY: "Soohyun Lee",
    SPECIES_KEY: "Mouse",
    ASP_KEY: "UFNC-01",
}

DEFAULT_STRAIN_OPTIONS: Final[list[str]] = [
    "N/A",
    "5HT3-eGFP",
    "Ai14",
    "Ai3",
    "Ai32",
    "Ai9",
    "Ai95",
    "Ai96",
    "C57BL/6J",
    "CaMKII-GCaMP6s",
    "DBH",
    "Drd1a-Cre",
    "Emx1-Cre",
    "GINGFP",
    "GPR26-Cre",
    "Grp-Cre",
    "LSL-TVA",
    "NP39-Cre",
    "Ntsr1-Cre",
    "PCP2-Cre",
    "PV-Cre",
    "Rbp4-Cre",
    "RCE-FRT",
    "ROSA-eGFP",
    "Sim1-Cre",
    "Vglut1-Cre",
    "SST-Cre",
    "SST-Flpo",
    "SynGAP1",
    "TH-Cre",
    "Tlx3-Cre",
    "VIP-Cre",
    "VIP-Flpo",
]

DEFAULT_OPTIONS: Final[dict[str, list[str]]] = {
    PROJECT_ID_KEY: ["SEASIC"],
    PROJECT_NAME_KEY: [
        "Sensory Evidence Accumulation Synaptic Integration in Cortex"
    ],
    LA_HOME_FOLDER_KEY: [],
    INVESTIGATOR_KEY: ["APF", "CY", "DK", "EP", "LZ", "MH", "SB", "SL"],
    PI_KEY: ["Soohyun Lee"],
    SPECIES_KEY: ["Mouse", "Marmoset"],
    ASP_KEY: ["UFNC-01"],
    STRAIN_OPTIONS_KEY: DEFAULT_STRAIN_OPTIONS,
    SOURCE_TYPE_OPTIONS_KEY: ["Breeding", "JAX"],
}


class ConfigValidationError(ValueError):
    """Raised when a loaded config JSON does not match the expected schema."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def clean_string(value: object) -> str:
    """Return a trimmed string or an empty string for non-string values."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def unique_strings(values: Iterable[object]) -> list[str]:
    """Return non-empty strings with order preserved and duplicates removed."""
    seen: set[str] = set()
    normalized: list[str] = []

    for raw_value in values:
        value = clean_string(raw_value)
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)

    return normalized


def add_option(options: dict[str, list[str]], key: str, value: str) -> None:
    """Add a non-empty option value to a known option list."""
    cleaned = clean_string(value)
    if cleaned and cleaned not in options[key]:
        options[key].append(cleaned)


def normalize_options(
    raw_options: object | None = None,
) -> dict[str, list[str]]:
    """Return option lists merged with built-in defaults."""
    options = deepcopy(DEFAULT_OPTIONS)

    if not isinstance(raw_options, Mapping):
        return options

    for key in OPTION_KEYS:
        raw_value = raw_options.get(key, [])
        if isinstance(raw_value, list):
            for value in unique_strings(raw_value):
                add_option(options, key, value)

    return options


def normalize_email_mapping(raw_mapping: object | None) -> dict[str, str]:
    """Return a clean email-to-investigator mapping."""
    if not isinstance(raw_mapping, Mapping):
        return {}

    normalized: dict[str, str] = {}
    for raw_email, raw_investigator in raw_mapping.items():
        email = clean_string(raw_email)
        investigator = clean_string(raw_investigator)
        if email and investigator:
            normalized[email] = investigator
    return normalized


def validate_config_payload(data: object) -> list[str]:
    """Return schema validation errors for a decoded JSON payload."""
    if not isinstance(data, Mapping):
        return ["Config JSON must be an object."]

    errors: list[str] = []
    required_keys = (
        *CONFIG_VALUE_KEYS,
        EMAIL_TO_INVESTIGATOR_KEY,
        OPTIONS_KEY,
    )

    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: {key}.")

    for key in CONFIG_VALUE_KEYS:
        if key in data and not clean_string(data[key]):
            errors.append(f"{key} must be a non-empty string.")

    if EMAIL_TO_INVESTIGATOR_KEY in data and not isinstance(
        data[EMAIL_TO_INVESTIGATOR_KEY], Mapping
    ):
        errors.append("email_to_investigator must be an object.")

    raw_options = data.get(OPTIONS_KEY)
    if OPTIONS_KEY in data and not isinstance(raw_options, Mapping):
        errors.append("options must be an object.")
    elif isinstance(raw_options, Mapping):
        for key in CONFIG_VALUE_KEYS:
            if key not in raw_options:
                errors.append(f"Missing required options key: {key}.")
            elif not isinstance(raw_options[key], list):
                errors.append(f"options.{key} must be a list.")
            elif any(not clean_string(value) for value in raw_options[key]):
                errors.append(f"options.{key} must contain only strings.")

        for key in SUBJECT_OPTION_KEYS:
            if key in raw_options and not isinstance(raw_options[key], list):
                errors.append(f"options.{key} must be a list.")
            elif key in raw_options and any(
                not clean_string(value) for value in raw_options[key]
            ):
                errors.append(f"options.{key} must contain only strings.")

    return errors


def normalize_config(data: object) -> dict[str, Any]:
    """Validate and normalize a loaded config JSON payload."""
    errors = validate_config_payload(data)
    if errors:
        raise ConfigValidationError(errors)

    raw_config = cast(Mapping[str, Any], data)
    options = normalize_options(raw_config[OPTIONS_KEY])

    config: dict[str, Any] = {}
    for key in CONFIG_VALUE_KEYS:
        value = clean_string(raw_config[key])
        config[key] = value
        add_option(options, key, value)

    config[EMAIL_TO_INVESTIGATOR_KEY] = normalize_email_mapping(
        raw_config[EMAIL_TO_INVESTIGATOR_KEY]
    )
    config[OPTIONS_KEY] = options
    return config


def build_config(
    selected_values: Mapping[str, str],
    *,
    options: Mapping[str, list[str]] | None = None,
    existing_email_mapping: Mapping[str, str] | None = None,
    user_email: str | None = None,
    remember_investigator: bool = False,
) -> dict[str, Any]:
    """Build a complete config JSON object from UI-selected values."""
    normalized_options = normalize_options(options)
    config: dict[str, Any] = {}

    for key in CONFIG_VALUE_KEYS:
        raw_value = (
            DEFAULT_VALUES[PI_KEY]
            if key == PI_KEY
            else selected_values.get(key)
        )
        value = clean_string(raw_value)
        if not value:
            raise ConfigValidationError([f"{key} must be provided."])
        config[key] = value
        add_option(normalized_options, key, value)

    email_mapping = normalize_email_mapping(existing_email_mapping)
    email = clean_string(user_email)
    if remember_investigator and email:
        email_mapping[email] = config[INVESTIGATOR_KEY]

    config[EMAIL_TO_INVESTIGATOR_KEY] = email_mapping
    config[OPTIONS_KEY] = normalized_options
    return config


def choice_options(options: Mapping[str, list[str]], key: str) -> list[str]:
    """Return selectbox options for a key, plus the UI-only Other choice."""
    values = unique_strings(options.get(key, []))
    return [*values, OTHER_CHOICE]
