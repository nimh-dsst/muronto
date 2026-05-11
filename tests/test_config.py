from __future__ import annotations

import pytest

from muronto_app.config import (
    ASP_KEY,
    DEFAULT_OPTIONS,
    DEFAULT_STRAIN_OPTIONS,
    DEFAULT_VALUES,
    EMAIL_TO_INVESTIGATOR_KEY,
    INVESTIGATOR_KEY,
    LA_HOME_FOLDER_KEY,
    OPTIONS_KEY,
    PI_KEY,
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    SOURCE_TYPE_OPTIONS_KEY,
    SPECIES_KEY,
    STRAIN_OPTIONS_KEY,
    ConfigValidationError,
    build_config,
    normalize_config,
    validate_config_payload,
)


def valid_values() -> dict[str, str]:
    return {
        PROJECT_ID_KEY: "SEASIC",
        PROJECT_NAME_KEY: (
            "Sensory Evidence Accumulation Synaptic Integration in Cortex"
        ),
        LA_HOME_FOLDER_KEY: "/Experiments",
        INVESTIGATOR_KEY: "APF",
        PI_KEY: "Soohyun Lee",
        SPECIES_KEY: "Mouse",
        ASP_KEY: "UFNC-01",
    }


def test_build_config_adds_new_options_and_email_mapping() -> None:
    selected_values = valid_values()
    selected_values[PROJECT_ID_KEY] = "NEWPROJECT"
    selected_values[INVESTIGATOR_KEY] = "NEWINV"

    config = build_config(
        selected_values,
        options=DEFAULT_OPTIONS,
        user_email="user@example.org",
        remember_investigator=True,
    )

    assert config[PROJECT_ID_KEY] == "NEWPROJECT"
    assert config[INVESTIGATOR_KEY] == "NEWINV"
    assert "NEWPROJECT" in config[OPTIONS_KEY][PROJECT_ID_KEY]
    assert "NEWINV" in config[OPTIONS_KEY][INVESTIGATOR_KEY]
    assert config[EMAIL_TO_INVESTIGATOR_KEY] == {"user@example.org": "NEWINV"}


def test_build_config_requires_selected_values() -> None:
    selected_values = valid_values()
    selected_values[LA_HOME_FOLDER_KEY] = ""

    with pytest.raises(ConfigValidationError) as exc_info:
        build_config(selected_values, options=DEFAULT_OPTIONS)

    assert "LA_Home_Folder must be provided." in str(exc_info.value)


def test_normalize_config_accepts_complete_payload() -> None:
    payload = {
        **valid_values(),
        EMAIL_TO_INVESTIGATOR_KEY: {"user@example.org": "APF"},
        OPTIONS_KEY: DEFAULT_OPTIONS,
    }

    config = normalize_config(payload)

    assert config[PI_KEY] == DEFAULT_VALUES[PI_KEY]
    assert config[EMAIL_TO_INVESTIGATOR_KEY]["user@example.org"] == "APF"
    assert config[OPTIONS_KEY][LA_HOME_FOLDER_KEY] == ["/Experiments"]


def test_normalize_config_injects_subject_option_defaults() -> None:
    options_without_subject = {
        key: value
        for key, value in DEFAULT_OPTIONS.items()
        if key not in {STRAIN_OPTIONS_KEY, SOURCE_TYPE_OPTIONS_KEY}
    }
    payload = {
        **valid_values(),
        EMAIL_TO_INVESTIGATOR_KEY: {},
        OPTIONS_KEY: options_without_subject,
    }

    config = normalize_config(payload)

    assert config[OPTIONS_KEY][STRAIN_OPTIONS_KEY] == DEFAULT_STRAIN_OPTIONS
    assert config[OPTIONS_KEY][SOURCE_TYPE_OPTIONS_KEY] == ["Breeding", "JAX"]


def test_normalize_config_preserves_custom_subject_options() -> None:
    payload = {
        **valid_values(),
        EMAIL_TO_INVESTIGATOR_KEY: {},
        OPTIONS_KEY: {
            **DEFAULT_OPTIONS,
            STRAIN_OPTIONS_KEY: ["Custom-Strain"],
            SOURCE_TYPE_OPTIONS_KEY: ["Custom-Source"],
        },
    }

    config = normalize_config(payload)

    assert "Custom-Strain" in config[OPTIONS_KEY][STRAIN_OPTIONS_KEY]
    assert "Custom-Source" in config[OPTIONS_KEY][SOURCE_TYPE_OPTIONS_KEY]


def test_validate_config_rejects_partial_payload() -> None:
    payload = {
        PROJECT_ID_KEY: "SEASIC",
        EMAIL_TO_INVESTIGATOR_KEY: {},
        OPTIONS_KEY: {},
    }

    errors = validate_config_payload(payload)

    assert any(
        "Missing required key: project_name." in error for error in errors
    )
    assert any(
        "Missing required options key: project_id." in error
        for error in errors
    )


def test_validate_config_rejects_malformed_options() -> None:
    payload = {
        **valid_values(),
        EMAIL_TO_INVESTIGATOR_KEY: {},
        OPTIONS_KEY: {**DEFAULT_OPTIONS, SPECIES_KEY: ["Mouse", 12]},
    }

    errors = validate_config_payload(payload)

    assert errors == ["options.Species must contain only strings."]


def test_validate_config_rejects_malformed_subject_options() -> None:
    payload = {
        **valid_values(),
        EMAIL_TO_INVESTIGATOR_KEY: {},
        OPTIONS_KEY: {**DEFAULT_OPTIONS, STRAIN_OPTIONS_KEY: ["Ai14", 12]},
    }

    errors = validate_config_payload(payload)

    assert errors == ["options.strain must contain only strings."]
