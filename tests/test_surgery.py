from __future__ import annotations

from datetime import date, time
from typing import Any

import pytest

from muronto_app.config import (
    DEFAULT_OPTIONS,
    MEDICATION_OPTIONS_KEY,
    OPTIONS_KEY,
    SURGEON_OPTIONS_KEY,
)
from muronto_app.surgery import (
    SurgeryValidationError,
    build_surgery_payload,
    format_surgery_date,
    format_surgery_time,
    medication_names,
    surgery_json_filename,
    with_surgeon_options,
    with_surgery_options,
)


def valid_surgery_kwargs() -> dict[str, Any]:
    return {
        "project_id": "SEASIC",
        "investigator": "APF",
        "animal_id": "123-4567",
        "ear_tag": "123",
        "surgeon": "SL",
        "surgery_date": date(2026, 5, 11),
        "preop_cnn": "123456",
        "postop_cnn": "654321",
        "weight_pre_g": 25.1,
        "weight_post_g": 24.8,
        "medications": [
            {"medication": "Meloxicam", "conc_mgml": 5.0, "volume": 0.1}
        ],
        "start_time": time(9, 0),
        "end_time": time(14, 0),
        "bregma_lambda_dist_mm": 4.2,
    }


def test_format_surgery_date_uses_yyyymmdd() -> None:
    assert format_surgery_date(date(2026, 5, 11)) == "20260511"


def test_format_surgery_time_uses_hhmm_with_leading_zeroes() -> None:
    assert format_surgery_time(time(9, 5)) == "0905"


def test_surgery_json_filename_uses_animal_id_and_date() -> None:
    assert (
        surgery_json_filename("123-4567", "20260511")
        == "123-4567_surgery_20260511.json"
    )


def test_build_surgery_payload_formats_date_and_values() -> None:
    payload = build_surgery_payload(**valid_surgery_kwargs())

    assert payload == {
        "project_id": "SEASIC",
        "investigator": "APF",
        "animal_id": "123-4567",
        "ear_tag": "123",
        "surgeon": "SL",
        "surgery_date": "20260511",
        "preop_cnn": "123456",
        "postop_cnn": "654321",
        "weight_pre_g": 25.1,
        "weight_post_g": 24.8,
        "medications": [
            {"medication": "Meloxicam", "conc_mgml": 5.0, "volume": 0.1}
        ],
        "start_time": "0900",
        "end_time": "1400",
        "bregma_lambda_dist_mm": 4.2,
    }


def test_build_surgery_payload_supports_multiple_medications() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["medications"] = [
        {"medication": "Meloxicam", "conc_mgml": 5.0, "volume": 0.1},
        {"medication": "Dexamethasone", "conc_mgml": 2.0, "volume": 0.05},
    ]

    payload = build_surgery_payload(**kwargs)

    assert payload["medications"] == [
        {"medication": "Meloxicam", "conc_mgml": 5.0, "volume": 0.1},
        {"medication": "Dexamethasone", "conc_mgml": 2.0, "volume": 0.05},
    ]
    assert medication_names(payload) == ["Meloxicam", "Dexamethasone"]


def test_build_surgery_payload_validates_cnn_patterns() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["preop_cnn"] = "12345"
    kwargs["postop_cnn"] = "abcdef"

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert any(
        "preop_cnn must match" in error for error in exc_info.value.errors
    )
    assert any(
        "postop_cnn must match" in error for error in exc_info.value.errors
    )


def test_build_surgery_payload_requires_date() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgery_date"] = None

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert "surgery_date must be selected." in exc_info.value.errors


def test_build_surgery_payload_requires_perioperative_fields() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["weight_pre_g"] = None
    kwargs["weight_post_g"] = None
    kwargs["start_time"] = None
    kwargs["end_time"] = None
    kwargs["bregma_lambda_dist_mm"] = None
    kwargs["medications"] = []

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert "weight_pre_g is required." in exc_info.value.errors
    assert "weight_post_g is required." in exc_info.value.errors
    assert "start_time must be selected." in exc_info.value.errors
    assert "end_time must be selected." in exc_info.value.errors
    assert "bregma_lambda_dist_mm is required." in exc_info.value.errors
    assert (
        "medications must include at least one entry." in exc_info.value.errors
    )


def test_build_surgery_payload_validates_medication_rows() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["medications"] = [
        {"medication": "", "conc_mgml": None, "volume": -1}
    ]

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert "medication_1 is required." in exc_info.value.errors
    assert "conc_mgml_1 is required." in exc_info.value.errors
    assert "volume_1 must be non-negative." in exc_info.value.errors


def test_build_surgery_payload_requires_end_after_start() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["start_time"] = time(14, 0)
    kwargs["end_time"] = time(14, 0)

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert "end_time must be later than start_time." in exc_info.value.errors


def test_with_surgeon_options_persists_custom_surgeon() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    updated_config, changed = with_surgeon_options(
        config,
        surgeon="JGL",
    )

    assert changed
    assert "JGL" in updated_config[OPTIONS_KEY][SURGEON_OPTIONS_KEY]


def test_with_surgery_options_persists_custom_medications() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    updated_config, changed = with_surgery_options(
        config,
        surgeon="APF",
        medications=["Meloxicam", "Custom-Med"],
    )

    assert changed
    assert "Custom-Med" in updated_config[OPTIONS_KEY][MEDICATION_OPTIONS_KEY]


def test_with_surgeon_options_ignores_existing_surgeon() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    _updated_config, changed = with_surgeon_options(
        config,
        surgeon="APF",
    )

    assert not changed
