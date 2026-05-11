from __future__ import annotations

import pytest

from muronto_app.config import (
    ASP_KEY,
    DEFAULT_OPTIONS,
    DEFAULT_PROJECT_ID_KEY,
    EMAIL_TO_INVESTIGATOR_KEY,
    EMAIL_TO_PROJECT_KEY,
    INVESTIGATOR_KEY,
    LA_HOME_FOLDER_KEY,
    OPTIONS_KEY,
    PI_KEY,
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    PROJECTS_KEY,
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    SOURCE_TYPE_OPTIONS_KEY,
    SPECIES_KEY,
    STRAIN_OPTIONS_KEY,
    ConfigValidationError,
    active_project,
    normalize_config,
    select_project_id,
    upsert_project_config,
    validate_config_payload,
)


def valid_project(project_id: str = "SEASIC") -> dict[str, str]:
    return {
        PROJECT_ID_KEY: project_id,
        PROJECT_NAME_KEY: (
            "Sensory Evidence Accumulation Synaptic Integration in Cortex"
        ),
        LA_HOME_FOLDER_KEY: f"/{project_id}",
        PI_KEY: "Soohyun Lee",
        SPECIES_KEY: "Mouse",
        ASP_KEY: "UFNC-01",
    }


def valid_payload() -> dict[str, object]:
    return {
        SCHEMA_VERSION_KEY: SCHEMA_VERSION,
        DEFAULT_PROJECT_ID_KEY: "SEASIC",
        PROJECTS_KEY: {"SEASIC": valid_project()},
        EMAIL_TO_INVESTIGATOR_KEY: {"user@example.org": "JGL"},
        EMAIL_TO_PROJECT_KEY: {"user@example.org": "SEASIC"},
        OPTIONS_KEY: {
            **DEFAULT_OPTIONS,
            INVESTIGATOR_KEY: ["APF", "JGL"],
        },
    }


def test_normalize_config_accepts_complete_v2_payload() -> None:
    config = normalize_config(valid_payload())

    assert config[SCHEMA_VERSION_KEY] == SCHEMA_VERSION
    assert config[DEFAULT_PROJECT_ID_KEY] == "SEASIC"
    assert config[PROJECTS_KEY]["SEASIC"][LA_HOME_FOLDER_KEY] == "/SEASIC"
    assert config[EMAIL_TO_INVESTIGATOR_KEY]["user@example.org"] == "JGL"
    assert config[EMAIL_TO_PROJECT_KEY]["user@example.org"] == "SEASIC"
    assert "JGL" in config[OPTIONS_KEY][INVESTIGATOR_KEY]


def test_validate_config_rejects_v1_payload() -> None:
    payload = {
        PROJECT_ID_KEY: "SEASIC",
        PROJECT_NAME_KEY: "Legacy project",
        LA_HOME_FOLDER_KEY: "/SEASIC",
        INVESTIGATOR_KEY: "JGL",
        PI_KEY: "Soohyun Lee",
        SPECIES_KEY: "Mouse",
        ASP_KEY: "UFNC-01",
        EMAIL_TO_INVESTIGATOR_KEY: {},
        OPTIONS_KEY: DEFAULT_OPTIONS,
    }

    errors = validate_config_payload(payload)

    assert any("schema_version must be 2" in error for error in errors)
    assert any("Missing required key: projects." in error for error in errors)


@pytest.mark.parametrize(
    ("schema_version", "expected_error"),
    [
        (None, "schema_version must be 2"),
        (1, "schema_version must be 2"),
        ("2", "schema_version must be 2"),
    ],
)
def test_validate_config_requires_schema_version_2(
    schema_version: object,
    expected_error: str,
) -> None:
    payload = valid_payload()
    if schema_version is None:
        del payload[SCHEMA_VERSION_KEY]
    else:
        payload[SCHEMA_VERSION_KEY] = schema_version

    errors = validate_config_payload(payload)

    assert any(expected_error in error for error in errors)


def test_validate_config_rejects_empty_projects() -> None:
    payload = valid_payload()
    payload[PROJECTS_KEY] = {}

    errors = validate_config_payload(payload)

    assert "projects must contain at least one project." in errors


def test_validate_config_rejects_project_key_mismatch() -> None:
    payload = valid_payload()
    payload[PROJECTS_KEY] = {"OTHER": valid_project("SEASIC")}

    errors = validate_config_payload(payload)

    assert "projects.OTHER.project_id must match the project key." in errors


def test_validate_config_rejects_missing_project_field() -> None:
    payload = valid_payload()
    project = valid_project()
    del project[LA_HOME_FOLDER_KEY]
    payload[PROJECTS_KEY] = {"SEASIC": project}

    errors = validate_config_payload(payload)

    assert (
        "Missing required project key: projects.SEASIC.LA_Home_Folder."
        in errors
    )


def test_validate_config_rejects_invalid_default_project() -> None:
    payload = valid_payload()
    payload[DEFAULT_PROJECT_ID_KEY] = "UNKNOWN"

    errors = validate_config_payload(payload)

    assert "default_project_id must reference a project." in errors


def test_validate_config_rejects_invalid_email_project() -> None:
    payload = valid_payload()
    payload[EMAIL_TO_PROJECT_KEY] = {"user@example.org": "UNKNOWN"}

    errors = validate_config_payload(payload)

    assert (
        "email_to_project.user@example.org must reference a project." in errors
    )


def test_validate_config_rejects_malformed_options() -> None:
    payload = valid_payload()
    payload[OPTIONS_KEY] = {**DEFAULT_OPTIONS, SPECIES_KEY: ["Mouse", 12]}

    errors = validate_config_payload(payload)

    assert errors == ["options.Species must contain only strings."]


def test_upsert_project_config_creates_initial_config_and_mappings() -> None:
    config = upsert_project_config(
        None,
        {
            **valid_project("NEWPROJECT"),
            SPECIES_KEY: "Marmoset",
            ASP_KEY: "UFNC-02",
        },
        investigator="JGL",
        user_email="user@example.org",
        remember_investigator=True,
        make_default=True,
        options=DEFAULT_OPTIONS,
    )

    assert config[DEFAULT_PROJECT_ID_KEY] == "NEWPROJECT"
    assert config[PROJECTS_KEY]["NEWPROJECT"][SPECIES_KEY] == "Marmoset"
    assert config[EMAIL_TO_INVESTIGATOR_KEY] == {"user@example.org": "JGL"}
    assert config[EMAIL_TO_PROJECT_KEY] == {"user@example.org": "NEWPROJECT"}
    assert "UFNC-02" in config[OPTIONS_KEY][ASP_KEY]


def test_upsert_project_config_updates_existing_project() -> None:
    existing = normalize_config(valid_payload())
    updated = upsert_project_config(
        existing,
        {**valid_project(), PROJECT_NAME_KEY: "Updated name"},
        investigator="JGL",
        user_email="user@example.org",
        remember_investigator=True,
    )

    assert updated[PROJECTS_KEY]["SEASIC"][PROJECT_NAME_KEY] == "Updated name"
    assert updated[DEFAULT_PROJECT_ID_KEY] == "SEASIC"
    assert updated[EMAIL_TO_PROJECT_KEY]["user@example.org"] == "SEASIC"


def test_upsert_project_config_preserves_subject_options() -> None:
    existing = valid_payload()
    existing[OPTIONS_KEY] = {
        **DEFAULT_OPTIONS,
        STRAIN_OPTIONS_KEY: ["Custom-Strain"],
        SOURCE_TYPE_OPTIONS_KEY: ["Custom-Source"],
    }

    config = upsert_project_config(
        existing,
        valid_project("OTHER"),
        investigator="JGL",
        user_email="user@example.org",
    )

    assert "Custom-Strain" in config[OPTIONS_KEY][STRAIN_OPTIONS_KEY]
    assert "Custom-Source" in config[OPTIONS_KEY][SOURCE_TYPE_OPTIONS_KEY]


def test_select_project_prefers_session_then_user_then_default() -> None:
    payload = valid_payload()
    payload[PROJECTS_KEY] = {
        "SEASIC": valid_project(),
        "OTHER": valid_project("OTHER"),
    }
    payload[EMAIL_TO_PROJECT_KEY] = {"user@example.org": "OTHER"}
    config = normalize_config(payload)
    selected_project = active_project(config, "other@example.org")

    assert select_project_id(config, "user@example.org", "SEASIC") == "SEASIC"
    assert select_project_id(config, "user@example.org") == "OTHER"
    assert selected_project is not None
    assert selected_project[PROJECT_ID_KEY] == "SEASIC"


def test_normalize_config_rejects_invalid_payload() -> None:
    payload = valid_payload()
    payload[PROJECTS_KEY] = {}

    with pytest.raises(ConfigValidationError):
        normalize_config(payload)
