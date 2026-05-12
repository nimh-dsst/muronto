from __future__ import annotations

from datetime import date, time
from typing import Any

import pytest

from muronto_app.config import (
    COVERSLIP_DIAMETER_OPTIONS_KEY,
    COVERSLIP_THICKNESS_OPTIONS_KEY,
    COVERSLIP_TYPE_OPTIONS_KEY,
    CRANIAL_WINDOW_REGION_OPTIONS_KEY,
    DEFAULT_OPTIONS,
    HEADPLATE_TYPE_OPTIONS_KEY,
    MEDICATION_OPTIONS_KEY,
    OPTIONS_KEY,
    SITE_OPTIONS_KEY,
    SURGEON_OPTIONS_KEY,
    VIRUS_OPTIONS_KEY,
    VIRUS_SOURCE_OPTIONS_KEY,
)
from muronto_app.surgery import (
    CRANIAL_WINDOW_IMPLANT_TYPE,
    CRYSTAL_SKULL_IMPLANT_TYPE,
    ELECTRODE_IMPLANT_TYPE,
    GRIN_LENS_IMPLANT_TYPE,
    IMPLANT_CATEGORY,
    VIRAL_INJECTION_CATEGORY,
    SurgeryValidationError,
    build_surgery_payload,
    format_surgery_date,
    format_surgery_time,
    medication_names,
    procedure_option_values,
    surgery_json_filename,
    with_surgeon_options,
    with_surgery_options,
)


def valid_viral_procedure() -> dict[str, object]:
    return {
        "surgery_category": VIRAL_INJECTION_CATEGORY,
        "injections": [
            {
                "site": "S1",
                "hemisphere": "LH",
                "viruses": [
                    {
                        "virus": "AAV1-hSynapsin1-axon-GCaMP6s",
                        "virus_source": "Addgene",
                        "virus_id": "123",
                        "virus_stock": "stock A",
                        "stock_titer": "2_10_13",
                        "dilution": "1:2",
                        "infusion_rate_nlmin": 50.0,
                    }
                ],
                "infusions": [
                    {
                        "ap": 1.0,
                        "ml": 2.0,
                        "dv": -3.0,
                        "infusion_volume_nl": 100.0,
                        "post_infusion_flow_test": "Pass",
                        "notes": "",
                    }
                ],
            }
        ],
    }


def valid_cranial_window_procedure() -> dict[str, object]:
    return {
        "surgery_category": IMPLANT_CATEGORY,
        "implant_type": CRANIAL_WINDOW_IMPLANT_TYPE,
        "cranial_window": {
            "headplate_type": "Standard_Y",
            "coverslip_type": "Standard Single",
            "coverslip_diameter": "3.5",
            "coverslip_thickness": "1.5",
            "region": "S1",
            "center_ap": 1.0,
            "center_ml": 2.0,
            "well_type": "Cement",
            "notes": "",
        },
    }


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
        "surgical_procedures": [valid_viral_procedure()],
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
        "surgical_procedures": [valid_viral_procedure()],
    }


def test_build_surgery_payload_supports_multiple_procedures() -> None:
    kwargs = valid_surgery_kwargs()
    second_procedure = valid_viral_procedure()
    second_procedure["injections"] = [
        {
            "site": "M1",
            "hemisphere": "RH",
            "viruses": [
                {
                    "virus": "AAV1-EF1a-fDIO-jRGECO1a",
                    "virus_source": "Addgene",
                    "virus_id": "456",
                    "virus_stock": "stock B",
                    "stock_titer": "3_10_12",
                    "dilution": "1:4",
                    "infusion_rate_nlmin": 25.0,
                }
            ],
            "infusions": [
                {
                    "ap": -1.0,
                    "ml": 1.5,
                    "dv": -2.5,
                    "infusion_volume_nl": 75.0,
                    "post_infusion_flow_test": "Pass",
                    "notes": "second site",
                }
            ],
        }
    ]
    kwargs["surgical_procedures"] = [
        valid_viral_procedure(),
        second_procedure,
    ]

    payload = build_surgery_payload(**kwargs)

    assert len(payload["surgical_procedures"]) == 2
    assert payload["surgical_procedures"][1]["injections"][0]["site"] == "M1"


def test_build_surgery_payload_supports_cranial_window_implant() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgical_procedures"] = [valid_cranial_window_procedure()]

    payload = build_surgery_payload(**kwargs)

    assert payload["surgical_procedures"] == [valid_cranial_window_procedure()]


def test_build_surgery_payload_supports_mixed_procedure_types() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgical_procedures"] = [
        valid_viral_procedure(),
        valid_cranial_window_procedure(),
    ]

    payload = build_surgery_payload(**kwargs)

    assert len(payload["surgical_procedures"]) == 2
    assert payload["surgical_procedures"][1]["implant_type"] == (
        CRANIAL_WINDOW_IMPLANT_TYPE
    )


def test_build_surgery_payload_supports_multiple_injections() -> None:
    kwargs = valid_surgery_kwargs()
    procedure = valid_viral_procedure()
    procedure["injections"] = [
        *procedure["injections"],  # type: ignore[misc]
        {
            "site": "BLA",
            "hemisphere": "RH",
            "viruses": [
                {
                    "virus": "AAV9-EF1a-DIO-FLPo-WPRE-hGHpA",
                    "virus_source": "Addgene",
                    "virus_id": "789",
                    "virus_stock": "stock C",
                    "stock_titer": "1_10_11",
                    "dilution": "undiluted",
                    "infusion_rate_nlmin": 40.0,
                }
            ],
            "infusions": [
                {
                    "ap": 0.5,
                    "ml": -1.5,
                    "dv": -4.0,
                    "infusion_volume_nl": 125.0,
                    "post_infusion_flow_test": "Fail",
                    "notes": "",
                }
            ],
        },
    ]
    kwargs["surgical_procedures"] = [procedure]

    payload = build_surgery_payload(**kwargs)

    injections = payload["surgical_procedures"][0]["injections"]
    assert len(injections) == 2
    assert injections[1]["site"] == "BLA"


def test_build_surgery_payload_supports_multiple_viruses() -> None:
    kwargs = valid_surgery_kwargs()
    procedure = valid_viral_procedure()
    injection = procedure["injections"][0]  # type: ignore[index]
    injection["viruses"] = [  # type: ignore[index]
        *injection["viruses"],  # type: ignore[index]
        {
            "virus": "AAV1-EF1a-fDIO-jRGECO1a",
            "virus_source": "Custom Source",
            "virus_id": "456",
            "virus_stock": "stock B",
            "stock_titer": "3_10_12",
            "dilution": "1:3",
            "infusion_rate_nlmin": 30.0,
        },
    ]
    injection["infusions"] = [  # type: ignore[index]
        *injection["infusions"],  # type: ignore[index]
        {
            "ap": 2.0,
            "ml": -2.0,
            "dv": -1.0,
            "infusion_volume_nl": 50.0,
            "post_infusion_flow_test": "Pass",
            "notes": "second infusion",
        },
    ]
    kwargs["surgical_procedures"] = [procedure]

    payload = build_surgery_payload(**kwargs)

    injection_payload = payload["surgical_procedures"][0]["injections"][0]
    assert len(injection_payload["viruses"]) == 2
    assert len(injection_payload["infusions"]) == 2
    assert procedure_option_values(payload) == (
        ["S1"],
        ["AAV1-hSynapsin1-axon-GCaMP6s", "AAV1-EF1a-fDIO-jRGECO1a"],
        ["Addgene", "Custom Source"],
        [],
        [],
        [],
        [],
        [],
    )


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


def test_build_surgery_payload_requires_surgical_procedures() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgical_procedures"] = []

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert (
        "surgical_procedures must include at least one entry."
        in exc_info.value.errors
    )


@pytest.mark.parametrize(
    "implant_type",
    [
        CRYSTAL_SKULL_IMPLANT_TYPE,
        ELECTRODE_IMPLANT_TYPE,
        GRIN_LENS_IMPLANT_TYPE,
        "Custom Implant",
    ],
)
def test_build_surgery_payload_rejects_unsupported_implants(
    implant_type: str,
) -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgical_procedures"] = [
        {"surgery_category": IMPLANT_CATEGORY, "implant_type": implant_type},
    ]

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert (
        f"{implant_type} implant procedures are not implemented yet."
        in exc_info.value.errors
    )


def test_build_surgery_payload_requires_implant_type() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgical_procedures"] = [
        {"surgery_category": IMPLANT_CATEGORY},
    ]

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert "surgical_procedures_1.implant_type is required." in (
        exc_info.value.errors
    )


def test_build_surgery_payload_validates_cranial_window_fields() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgical_procedures"] = [
        {
            "surgery_category": IMPLANT_CATEGORY,
            "implant_type": CRANIAL_WINDOW_IMPLANT_TYPE,
            "cranial_window": {
                "headplate_type": "",
                "coverslip_type": "",
                "coverslip_diameter": "",
                "coverslip_thickness": "",
                "region": "",
                "center_ap": None,
                "center_ml": None,
                "well_type": "Water",
                "notes": "",
            },
        }
    ]

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    errors = exc_info.value.errors
    assert (
        "surgical_procedures_1.cranial_window.headplate_type is required."
        in errors
    )
    assert (
        "surgical_procedures_1.cranial_window.coverslip_type is required."
        in errors
    )
    assert (
        "surgical_procedures_1.cranial_window.coverslip_diameter is required."
        in errors
    )
    assert (
        "surgical_procedures_1.cranial_window.coverslip_thickness is required."
        in errors
    )
    assert "surgical_procedures_1.cranial_window.region is required." in errors
    assert "surgical_procedures_1.cranial_window.center_ap is required." in (
        errors
    )
    assert "surgical_procedures_1.cranial_window.center_ml is required." in (
        errors
    )
    expected_well_error = (
        "surgical_procedures_1.cranial_window.well_type must be one of "
        "Cement, 3D Printed."
    )
    assert expected_well_error in errors


def test_build_surgery_payload_validates_viral_required_fields() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgical_procedures"] = [
        {
            "surgery_category": VIRAL_INJECTION_CATEGORY,
            "injections": [
                {
                    "site": "",
                    "hemisphere": "Both",
                    "viruses": [],
                    "infusions": [],
                }
            ],
        }
    ]

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    errors = exc_info.value.errors
    assert "surgical_procedures_1.injections_1.site is required." in errors
    assert (
        "surgical_procedures_1.injections_1.hemisphere must be one of LH, RH."
        in errors
    )
    assert (
        "surgical_procedures_1.injections_1.viruses must include at least one "
        "entry."
    ) in errors
    assert (
        "surgical_procedures_1.injections_1.infusions must include at least "
        "one entry."
    ) in errors


def test_build_surgery_payload_validates_stock_titer_pattern() -> None:
    kwargs = valid_surgery_kwargs()
    procedure = valid_viral_procedure()
    injection = procedure["injections"][0]  # type: ignore[index]
    virus = injection["viruses"][0]  # type: ignore[index]
    virus["stock_titer"] = "2x10x13"  # type: ignore[index]
    kwargs["surgical_procedures"] = [procedure]

    with pytest.raises(SurgeryValidationError) as exc_info:
        build_surgery_payload(**kwargs)

    assert any(
        "stock_titer must match" in error for error in exc_info.value.errors
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


def test_with_surgery_options_persists_custom_procedure_options() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    updated_config, changed = with_surgery_options(
        config,
        surgeon="APF",
        sites=["Custom-Site"],
        viruses=["Custom-Virus"],
        virus_sources=["Custom-Source"],
    )

    assert changed
    assert "Custom-Site" in updated_config[OPTIONS_KEY][SITE_OPTIONS_KEY]
    assert "Custom-Virus" in updated_config[OPTIONS_KEY][VIRUS_OPTIONS_KEY]
    assert (
        "Custom-Source"
        in updated_config[OPTIONS_KEY][VIRUS_SOURCE_OPTIONS_KEY]
    )


def test_with_surgery_options_persists_custom_implant_options() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    updated_config, changed = with_surgery_options(
        config,
        surgeon="APF",
        headplate_types=["Custom-Headplate"],
        coverslip_types=["Custom-Coverslip"],
        coverslip_diameters=["4.0"],
        coverslip_thicknesses=["2.0"],
        cranial_window_regions=["Custom-Region"],
    )

    assert changed
    assert (
        "Custom-Headplate"
        in updated_config[OPTIONS_KEY][HEADPLATE_TYPE_OPTIONS_KEY]
    )
    assert (
        "Custom-Coverslip"
        in updated_config[OPTIONS_KEY][COVERSLIP_TYPE_OPTIONS_KEY]
    )
    assert "4.0" in updated_config[OPTIONS_KEY][COVERSLIP_DIAMETER_OPTIONS_KEY]
    assert (
        "2.0" in updated_config[OPTIONS_KEY][COVERSLIP_THICKNESS_OPTIONS_KEY]
    )
    assert (
        "Custom-Region"
        in updated_config[OPTIONS_KEY][CRANIAL_WINDOW_REGION_OPTIONS_KEY]
    )


def test_procedure_option_values_returns_implant_options() -> None:
    kwargs = valid_surgery_kwargs()
    kwargs["surgical_procedures"] = [valid_cranial_window_procedure()]
    payload = build_surgery_payload(**kwargs)

    assert procedure_option_values(payload) == (
        [],
        [],
        [],
        ["Standard_Y"],
        ["Standard Single"],
        ["3.5"],
        ["1.5"],
        ["S1"],
    )


def test_with_surgeon_options_ignores_existing_surgeon() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    _updated_config, changed = with_surgeon_options(
        config,
        surgeon="APF",
    )

    assert not changed
