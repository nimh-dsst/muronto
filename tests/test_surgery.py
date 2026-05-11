from __future__ import annotations

from datetime import date

import pytest

from muronto_app.config import (
    DEFAULT_OPTIONS,
    OPTIONS_KEY,
    SURGEON_OPTIONS_KEY,
)
from muronto_app.surgery import (
    SurgeryValidationError,
    build_surgery_payload,
    format_surgery_date,
    surgery_json_filename,
    with_surgeon_options,
)


def test_format_surgery_date_uses_yyyymmdd() -> None:
    assert format_surgery_date(date(2026, 5, 11)) == "20260511"


def test_surgery_json_filename_uses_animal_id_and_date() -> None:
    assert (
        surgery_json_filename("123-4567", "20260511")
        == "123-4567_surgery_20260511.json"
    )


def test_build_surgery_payload_formats_date_and_values() -> None:
    payload = build_surgery_payload(
        project_id="SEASIC",
        investigator="APF",
        animal_id="123-4567",
        ear_tag="123",
        surgeon="SL",
        surgery_date=date(2026, 5, 11),
        preop_cnn="123456",
        postop_cnn="654321",
    )

    assert payload == {
        "project_id": "SEASIC",
        "investigator": "APF",
        "animal_id": "123-4567",
        "ear_tag": "123",
        "surgeon": "SL",
        "surgery_date": "20260511",
        "preop_cnn": "123456",
        "postop_cnn": "654321",
    }


def test_build_surgery_payload_validates_cnn_patterns() -> None:
    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(
            project_id="SEASIC",
            investigator="APF",
            animal_id="123-4567",
            ear_tag="123",
            surgeon="SL",
            surgery_date=date(2026, 5, 11),
            preop_cnn="12345",
            postop_cnn="abcdef",
        )

    assert any(
        "preop_cnn must match" in error for error in exc_info.value.errors
    )
    assert any(
        "postop_cnn must match" in error for error in exc_info.value.errors
    )


def test_build_surgery_payload_requires_date() -> None:
    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(
            project_id="SEASIC",
            investigator="APF",
            animal_id="123-4567",
            ear_tag="123",
            surgeon="SL",
            surgery_date=None,
            preop_cnn="123456",
            postop_cnn="654321",
        )

    assert "surgery_date must be selected." in exc_info.value.errors


def test_with_surgeon_options_persists_custom_surgeon() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    updated_config, changed = with_surgeon_options(
        config,
        surgeon="JGL",
    )

    assert changed
    assert "JGL" in updated_config[OPTIONS_KEY][SURGEON_OPTIONS_KEY]


def test_with_surgeon_options_ignores_existing_surgeon() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    _updated_config, changed = with_surgeon_options(
        config,
        surgeon="APF",
    )

    assert not changed
