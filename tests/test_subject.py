from __future__ import annotations

from datetime import date

import pytest

from muronto_app.config import (
    DEFAULT_OPTIONS,
    OPTIONS_KEY,
    SOURCE_TYPE_OPTIONS_KEY,
    STRAIN_OPTIONS_KEY,
)
from muronto_app.subject import (
    SubjectValidationError,
    build_subject_payload,
    with_subject_options,
)


def test_build_subject_payload_formats_dates_and_suffixes_pairs() -> None:
    payload = build_subject_payload(
        animal_id="123-4567",
        ear_tag="123",
        ccn="123456",
        sex="M",
        strain_genotypes=[("Ai14", "Het"), ("Custom-Strain", "Tg")],
        dob=date(2024, 1, 2),
        dow=date(2024, 1, 9),
        source_type="Breeding",
        parent_ccn="654321",
    )

    assert payload["animal_id"] == "123-4567"
    assert payload["sex"] == "M"
    assert payload["strain_1"] == "Ai14"
    assert payload["genotype_1"] == "Het"
    assert payload["strain_2"] == "Custom-Strain"
    assert payload["genotype_2"] == "Tg"
    assert payload["dob"] == "20240102"
    assert payload["dow"] == "20240109"
    assert payload["parent_ccn"] == "654321"


def test_build_subject_payload_requires_breeding_parent_ccn() -> None:
    with pytest.raises(SubjectValidationError) as exc_info:
        build_subject_payload(
            animal_id="123-4567",
            ear_tag="123",
            ccn="123456",
            sex="F",
            strain_genotypes=[("Ai14", "Het")],
            dob=date(2024, 1, 2),
            dow=date(2024, 1, 9),
            source_type="Breeding",
            parent_ccn="",
        )

    assert "parent_ccn is required." in exc_info.value.errors


def test_build_subject_payload_allows_blank_parent_for_jax() -> None:
    payload = build_subject_payload(
        animal_id="123-4567",
        ear_tag="123",
        ccn="123456",
        sex="F",
        strain_genotypes=[("Ai14", "Het")],
        dob=date(2024, 1, 2),
        dow=date(2024, 1, 9),
        source_type="JAX",
        parent_ccn="",
    )

    assert payload["source_type"] == "JAX"
    assert payload["parent_ccn"] == ""


def test_build_subject_payload_validates_optional_parent_ccn() -> None:
    with pytest.raises(SubjectValidationError) as exc_info:
        build_subject_payload(
            animal_id="123-4567",
            ear_tag="123",
            ccn="123456",
            sex="M",
            strain_genotypes=[("Ai14", "Het")],
            dob=date(2024, 1, 2),
            dow=date(2024, 1, 9),
            source_type="JAX",
            parent_ccn="12",
        )

    assert any(
        "parent_ccn must match" in error for error in exc_info.value.errors
    )


def test_build_subject_payload_validates_identity_patterns() -> None:
    with pytest.raises(SubjectValidationError) as exc_info:
        build_subject_payload(
            animal_id="1234567",
            ear_tag="12",
            ccn="12345",
            sex="M",
            strain_genotypes=[("Ai14", "Het")],
            dob=date(2024, 1, 2),
            dow=date(2024, 1, 9),
            source_type="JAX",
            parent_ccn="",
        )

    assert any(
        "animal_id must match" in error for error in exc_info.value.errors
    )
    assert any(
        "ear_tag must match" in error for error in exc_info.value.errors
    )
    assert any("ccn must match" in error for error in exc_info.value.errors)


def test_build_subject_payload_validates_sex_options() -> None:
    with pytest.raises(SubjectValidationError) as exc_info:
        build_subject_payload(
            animal_id="123-4567",
            ear_tag="123",
            ccn="123456",
            sex="U",
            strain_genotypes=[("Ai14", "Het")],
            dob=date(2024, 1, 2),
            dow=date(2024, 1, 9),
            source_type="JAX",
            parent_ccn="",
        )

    assert "sex must be one of M, F." in exc_info.value.errors


def test_with_subject_options_persists_custom_subject_values() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    updated_config, changed = with_subject_options(
        config,
        strains=["Ai14", "Custom-Strain"],
        source_type="Custom-Source",
    )

    assert changed
    assert "Custom-Strain" in updated_config[OPTIONS_KEY][STRAIN_OPTIONS_KEY]
    assert (
        "Custom-Source" in updated_config[OPTIONS_KEY][SOURCE_TYPE_OPTIONS_KEY]
    )


def test_with_subject_options_ignores_existing_values() -> None:
    config = {OPTIONS_KEY: DEFAULT_OPTIONS}

    _updated_config, changed = with_subject_options(
        config,
        strains=["Ai14"],
        source_type="JAX",
    )

    assert not changed
