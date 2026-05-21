"""Configuration schema and normalization for ``muronto_config``."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any, Final, cast

CONFIG_PAGE_NAME: Final[str] = "muronto_config"
CONFIG_FILENAME: Final[str] = "muronto_config.json"
CONFIG_CAPTION: Final[str] = "muronto_config"
OTHER_CHOICE: Final[str] = "Other"
SCHEMA_VERSION: Final[int] = 2

SCHEMA_VERSION_KEY: Final[str] = "schema_version"
DEFAULT_PROJECT_ID_KEY: Final[str] = "default_project_id"
PROJECTS_KEY: Final[str] = "projects"
PROJECT_ID_KEY: Final[str] = "project_id"
PROJECT_NAME_KEY: Final[str] = "project_name"
LA_HOME_FOLDER_KEY: Final[str] = "LA_Home_Folder"
INVESTIGATOR_KEY: Final[str] = "Investigator"
PI_KEY: Final[str] = "PI"
SPECIES_KEY: Final[str] = "Species"
ASP_KEY: Final[str] = "ASP"
EMAIL_TO_INVESTIGATOR_KEY: Final[str] = "email_to_investigator"
EMAIL_TO_PROJECT_KEY: Final[str] = "email_to_project"
OPTIONS_KEY: Final[str] = "options"
STRAIN_OPTIONS_KEY: Final[str] = "strain"
SOURCE_TYPE_OPTIONS_KEY: Final[str] = "source_type"
SURGEON_OPTIONS_KEY: Final[str] = "Surgeon"
MEDICATION_OPTIONS_KEY: Final[str] = "medications"
SITE_OPTIONS_KEY: Final[str] = "sites"
VIRUS_OPTIONS_KEY: Final[str] = "viruses"
VIRUS_SOURCE_OPTIONS_KEY: Final[str] = "virus_sources"
HEADPLATE_TYPE_OPTIONS_KEY: Final[str] = "headplate_types"
COVERSLIP_TYPE_OPTIONS_KEY: Final[str] = "coverslip_types"
COVERSLIP_DIAMETER_OPTIONS_KEY: Final[str] = "coverslip_diameters"
COVERSLIP_THICKNESS_OPTIONS_KEY: Final[str] = "coverslip_thicknesses"
CRANIAL_WINDOW_REGION_OPTIONS_KEY: Final[str] = "cranial_window_regions"
CS_TYPE_OPTIONS_KEY: Final[str] = "cs_types"
CRYSTAL_SKULL_WELL_TYPE_OPTIONS_KEY: Final[str] = "crystal_skill_well_types"
PROBE_MODEL_OPTIONS_KEY: Final[str] = "probe_models"
ELECTRODE_SITE_OPTIONS_KEY: Final[str] = "electrode_sites"

PROJECT_VALUE_KEYS: Final[tuple[str, ...]] = (
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    LA_HOME_FOLDER_KEY,
    PI_KEY,
    SPECIES_KEY,
    ASP_KEY,
)

OPTION_VALUE_KEYS: Final[tuple[str, ...]] = (
    INVESTIGATOR_KEY,
    PI_KEY,
    SPECIES_KEY,
    ASP_KEY,
)

SUBJECT_OPTION_KEYS: Final[tuple[str, ...]] = (
    STRAIN_OPTIONS_KEY,
    SOURCE_TYPE_OPTIONS_KEY,
)

SURGERY_OPTION_KEYS: Final[tuple[str, ...]] = (
    SURGEON_OPTIONS_KEY,
    MEDICATION_OPTIONS_KEY,
    SITE_OPTIONS_KEY,
    VIRUS_OPTIONS_KEY,
    VIRUS_SOURCE_OPTIONS_KEY,
    HEADPLATE_TYPE_OPTIONS_KEY,
    COVERSLIP_TYPE_OPTIONS_KEY,
    COVERSLIP_DIAMETER_OPTIONS_KEY,
    COVERSLIP_THICKNESS_OPTIONS_KEY,
    CRANIAL_WINDOW_REGION_OPTIONS_KEY,
    CS_TYPE_OPTIONS_KEY,
    CRYSTAL_SKULL_WELL_TYPE_OPTIONS_KEY,
    PROBE_MODEL_OPTIONS_KEY,
    ELECTRODE_SITE_OPTIONS_KEY,
)

OPTION_KEYS: Final[tuple[str, ...]] = (
    *OPTION_VALUE_KEYS,
    *SUBJECT_OPTION_KEYS,
    *SURGERY_OPTION_KEYS,
)

REQUIRED_OPTION_KEYS: Final[tuple[str, ...]] = (
    *OPTION_VALUE_KEYS,
    *SUBJECT_OPTION_KEYS,
)

OPTIONAL_OPTION_KEYS: Final[tuple[str, ...]] = SURGERY_OPTION_KEYS

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
    INVESTIGATOR_KEY: ["APF", "CY", "DK", "EP", "LZ", "MH", "SB", "SL"],
    PI_KEY: ["Soohyun Lee"],
    SPECIES_KEY: ["Mouse", "Marmoset"],
    ASP_KEY: ["UFNC-01"],
    STRAIN_OPTIONS_KEY: DEFAULT_STRAIN_OPTIONS,
    SOURCE_TYPE_OPTIONS_KEY: ["Breeding", "JAX"],
    SURGEON_OPTIONS_KEY: ["APF", "CY", "DK", "EP", "LZ", "MH", "SB", "SL"],
    MEDICATION_OPTIONS_KEY: ["Meloxicam", "Ethiqa XR", "Dexamethasone"],
    SITE_OPTIONS_KEY: [
        "S1",
        "M1",
        "M2",
        "vlOFC",
        "vmThal",
        "Claustrum",
        "BLA",
    ],
    VIRUS_OPTIONS_KEY: [
        "AAV1-hSynapsin1-axon-GCaMP6s",
        "AAV1-Syn-Flex-NES-jRGECO1a-WPRE-SV40",
        "AAV9-EF1a-DIO-FLPo-WPRE-hGHpA",
        "AAV1-EF1a-fDIO-jRGECO1a",
    ],
    VIRUS_SOURCE_OPTIONS_KEY: ["Addgene"],
    HEADPLATE_TYPE_OPTIONS_KEY: ["Standard_Y", "Standard_0"],
    COVERSLIP_TYPE_OPTIONS_KEY: [
        "Standard Single",
        "Standard Double",
        "Electropor Single",
        "Electropor Double",
    ],
    COVERSLIP_DIAMETER_OPTIONS_KEY: ["3.5", "3_3.5"],
    COVERSLIP_THICKNESS_OPTIONS_KEY: ["1.5", "1.5_1.5"],
    CRANIAL_WINDOW_REGION_OPTIONS_KEY: ["S1"],
    CS_TYPE_OPTIONS_KEY: ["Standard", "Electropor_S1"],
    CRYSTAL_SKULL_WELL_TYPE_OPTIONS_KEY: ["Cement", "3D Printed"],
    PROBE_MODEL_OPTIONS_KEY: ["Alpha", "Beta"],
    ELECTRODE_SITE_OPTIONS_KEY: [
        "S1",
        "M1",
        "M2",
        "vlOFC",
        "vmThal",
        "Claustrum",
        "BLA",
    ],
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
    """Return a clean string-to-string email mapping."""
    if not isinstance(raw_mapping, Mapping):
        return {}

    normalized: dict[str, str] = {}
    for raw_email, raw_value in raw_mapping.items():
        email = clean_string(raw_email)
        value = clean_string(raw_value)
        if email and value:
            normalized[email] = value
    return normalized


def _validate_email_mapping(
    *,
    raw_mapping: object,
    key: str,
    errors: list[str],
    project_ids: set[str] | None = None,
) -> None:
    if not isinstance(raw_mapping, Mapping):
        errors.append(f"{key} must be an object.")
        return

    for raw_email, raw_value in raw_mapping.items():
        email = clean_string(raw_email)
        value = clean_string(raw_value)
        if not email or not value:
            errors.append(
                f"{key} must map non-empty email strings to strings."
            )
            continue
        if project_ids is not None and value not in project_ids:
            errors.append(f"{key}.{email} must reference a project.")


def _validate_options(raw_options: object, errors: list[str]) -> None:
    if not isinstance(raw_options, Mapping):
        errors.append("options must be an object.")
        return

    for key in REQUIRED_OPTION_KEYS:
        if key not in raw_options:
            errors.append(f"Missing required options key: {key}.")
            continue
        _validate_option_list(raw_options[key], key, errors)

    for key in OPTIONAL_OPTION_KEYS:
        if key in raw_options:
            _validate_option_list(raw_options[key], key, errors)


def _validate_option_list(
    raw_value: object,
    key: str,
    errors: list[str],
) -> None:
    if not isinstance(raw_value, list):
        errors.append(f"options.{key} must be a list.")
    elif any(not clean_string(value) for value in raw_value):
        errors.append(f"options.{key} must contain only strings.")


def _validate_projects(raw_projects: object, errors: list[str]) -> set[str]:
    project_ids: set[str] = set()
    if not isinstance(raw_projects, Mapping):
        errors.append("projects must be an object.")
        return project_ids

    if not raw_projects:
        errors.append("projects must contain at least one project.")
        return project_ids

    for raw_project_key, raw_project in raw_projects.items():
        project_key = clean_string(raw_project_key)
        if not project_key:
            errors.append("projects keys must be non-empty strings.")
            continue

        project_ids.add(project_key)
        if not isinstance(raw_project, Mapping):
            errors.append(f"projects.{project_key} must be an object.")
            continue

        for key in PROJECT_VALUE_KEYS:
            if key not in raw_project:
                errors.append(
                    f"Missing required project key: "
                    f"projects.{project_key}.{key}."
                )
            elif not clean_string(raw_project[key]):
                errors.append(
                    f"projects.{project_key}.{key} must be a non-empty string."
                )

        project_id = clean_string(raw_project.get(PROJECT_ID_KEY))
        if project_id and project_id != project_key:
            errors.append(
                f"projects.{project_key}.project_id must match the "
                "project key."
            )

    return project_ids


def validate_config_payload(data: object) -> list[str]:
    """Return schema validation errors for a decoded JSON payload."""
    if not isinstance(data, Mapping):
        return ["Config JSON must be an object."]

    errors: list[str] = []
    required_keys = (
        SCHEMA_VERSION_KEY,
        DEFAULT_PROJECT_ID_KEY,
        PROJECTS_KEY,
        EMAIL_TO_INVESTIGATOR_KEY,
        EMAIL_TO_PROJECT_KEY,
        OPTIONS_KEY,
    )

    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: {key}.")

    if data.get(SCHEMA_VERSION_KEY) != SCHEMA_VERSION:
        errors.append(
            "schema_version must be 2; replace existing single-project "
            "configs with a v2 muronto_config."
        )

    project_ids: set[str] = set()
    if PROJECTS_KEY in data:
        project_ids = _validate_projects(data[PROJECTS_KEY], errors)

    if DEFAULT_PROJECT_ID_KEY in data:
        default_project_id = clean_string(data[DEFAULT_PROJECT_ID_KEY])
        if not default_project_id:
            errors.append("default_project_id must be a non-empty string.")
        elif project_ids and default_project_id not in project_ids:
            errors.append("default_project_id must reference a project.")

    if EMAIL_TO_INVESTIGATOR_KEY in data:
        _validate_email_mapping(
            raw_mapping=data[EMAIL_TO_INVESTIGATOR_KEY],
            key=EMAIL_TO_INVESTIGATOR_KEY,
            errors=errors,
        )

    if EMAIL_TO_PROJECT_KEY in data:
        _validate_email_mapping(
            raw_mapping=data[EMAIL_TO_PROJECT_KEY],
            key=EMAIL_TO_PROJECT_KEY,
            errors=errors,
            project_ids=project_ids,
        )

    if OPTIONS_KEY in data:
        _validate_options(data[OPTIONS_KEY], errors)

    return errors


def build_project(selected_values: Mapping[str, str]) -> dict[str, str]:
    """Build a normalized project record from UI-selected values."""
    project: dict[str, str] = {}
    errors: list[str] = []

    for key in PROJECT_VALUE_KEYS:
        value = clean_string(selected_values.get(key))
        if not value:
            errors.append(f"{key} must be provided.")
        else:
            project[key] = value

    if errors:
        raise ConfigValidationError(errors)

    return project


def add_project_options(
    options: dict[str, list[str]],
    project: Mapping[str, str],
) -> None:
    """Remember reusable project values in config options."""
    for key in (PI_KEY, SPECIES_KEY, ASP_KEY):
        add_option(options, key, project.get(key, ""))


def normalize_project(raw_project: Mapping[str, Any]) -> dict[str, str]:
    """Return a clean project record."""
    return {key: clean_string(raw_project[key]) for key in PROJECT_VALUE_KEYS}


def normalize_config(data: object) -> dict[str, Any]:
    """Validate and normalize a loaded v2 config JSON payload."""
    errors = validate_config_payload(data)
    if errors:
        raise ConfigValidationError(errors)

    raw_config = cast(Mapping[str, Any], data)
    raw_projects = cast(
        Mapping[str, Mapping[str, Any]],
        raw_config[PROJECTS_KEY],
    )
    options = normalize_options(raw_config[OPTIONS_KEY])
    projects: dict[str, dict[str, str]] = {}

    for raw_project_key, raw_project in raw_projects.items():
        project_key = clean_string(raw_project_key)
        project = normalize_project(raw_project)
        projects[project_key] = project
        add_project_options(options, project)

    email_to_investigator = normalize_email_mapping(
        raw_config[EMAIL_TO_INVESTIGATOR_KEY]
    )
    for investigator in email_to_investigator.values():
        add_option(options, INVESTIGATOR_KEY, investigator)

    config: dict[str, Any] = {
        SCHEMA_VERSION_KEY: SCHEMA_VERSION,
        DEFAULT_PROJECT_ID_KEY: clean_string(
            raw_config[DEFAULT_PROJECT_ID_KEY]
        ),
        PROJECTS_KEY: projects,
        EMAIL_TO_INVESTIGATOR_KEY: email_to_investigator,
        EMAIL_TO_PROJECT_KEY: normalize_email_mapping(
            raw_config[EMAIL_TO_PROJECT_KEY]
        ),
        OPTIONS_KEY: options,
    }
    return config


def upsert_project_config(
    existing_config: Mapping[str, Any] | None,
    project_values: Mapping[str, str],
    *,
    investigator: str,
    user_email: str | None = None,
    remember_investigator: bool = False,
    remember_project: bool = True,
    make_default: bool = False,
    options: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Return a v2 config with one project added or updated."""
    project = build_project(project_values)
    project_id = project[PROJECT_ID_KEY]

    existing = (
        normalize_config(existing_config)
        if existing_config is not None
        else None
    )
    normalized_options = normalize_options(
        existing[OPTIONS_KEY] if existing is not None else options
    )
    projects = deepcopy(existing[PROJECTS_KEY]) if existing is not None else {}
    projects[project_id] = project

    for saved_project in projects.values():
        add_project_options(normalized_options, saved_project)

    cleaned_investigator = clean_string(investigator)
    if cleaned_investigator:
        add_option(
            normalized_options,
            INVESTIGATOR_KEY,
            cleaned_investigator,
        )

    email = clean_string(user_email)
    email_to_investigator = (
        normalize_email_mapping(existing[EMAIL_TO_INVESTIGATOR_KEY])
        if existing is not None
        else {}
    )
    if remember_investigator and email and cleaned_investigator:
        email_to_investigator[email] = cleaned_investigator

    email_to_project = (
        normalize_email_mapping(existing[EMAIL_TO_PROJECT_KEY])
        if existing is not None
        else {}
    )
    if remember_project and email:
        email_to_project[email] = project_id

    existing_default = (
        clean_string(existing[DEFAULT_PROJECT_ID_KEY])
        if existing is not None
        else ""
    )
    default_project_id = (
        project_id
        if make_default
        or not existing_default
        or existing_default not in projects
        else existing_default
    )

    return normalize_config(
        {
            SCHEMA_VERSION_KEY: SCHEMA_VERSION,
            DEFAULT_PROJECT_ID_KEY: default_project_id,
            PROJECTS_KEY: projects,
            EMAIL_TO_INVESTIGATOR_KEY: email_to_investigator,
            EMAIL_TO_PROJECT_KEY: email_to_project,
            OPTIONS_KEY: normalized_options,
        }
    )


def project_ids(config: Mapping[str, Any]) -> list[str]:
    """Return configured project IDs in config order."""
    raw_projects = config.get(PROJECTS_KEY)
    if not isinstance(raw_projects, Mapping):
        return []
    return [
        project_id
        for raw_project_id in raw_projects
        if (project_id := clean_string(raw_project_id))
    ]


def get_project(
    config: Mapping[str, Any],
    project_id: str,
) -> dict[str, str] | None:
    """Return a project record from a normalized config."""
    raw_projects = config.get(PROJECTS_KEY)
    if not isinstance(raw_projects, Mapping):
        return None

    raw_project = raw_projects.get(clean_string(project_id))
    if not isinstance(raw_project, Mapping):
        return None
    return {
        key: clean_string(raw_project.get(key)) for key in PROJECT_VALUE_KEYS
    }


def select_project_id(
    config: Mapping[str, Any],
    user_email: str | None,
    session_project_id: str | None = None,
) -> str:
    """Return the best active project ID for a user/session."""
    available_project_ids = project_ids(config)
    if not available_project_ids:
        return ""

    email_to_project = normalize_email_mapping(
        config.get(EMAIL_TO_PROJECT_KEY)
    )
    candidates = [
        session_project_id,
        email_to_project.get(clean_string(user_email)),
        config.get(DEFAULT_PROJECT_ID_KEY),
        available_project_ids[0],
    ]
    for candidate in candidates:
        project_id = clean_string(candidate)
        if project_id in available_project_ids:
            return project_id

    return available_project_ids[0]


def active_project(
    config: Mapping[str, Any],
    user_email: str | None,
    session_project_id: str | None = None,
) -> dict[str, str] | None:
    """Return the selected project record for a user/session."""
    selected_project_id = select_project_id(
        config,
        user_email,
        session_project_id,
    )
    if not selected_project_id:
        return None
    return get_project(config, selected_project_id)


def investigator_for_user(
    config: Mapping[str, Any],
    user_email: str | None,
) -> str:
    """Return the user's remembered investigator or the default."""
    email_to_investigator = normalize_email_mapping(
        config.get(EMAIL_TO_INVESTIGATOR_KEY)
    )
    investigator = email_to_investigator.get(clean_string(user_email))
    return investigator or DEFAULT_VALUES[INVESTIGATOR_KEY]


def choice_options(options: Mapping[str, list[str]], key: str) -> list[str]:
    """Return selectbox options for a key, plus the UI-only Other choice."""
    values = unique_strings(options.get(key, []))
    return [*values, OTHER_CHOICE]
