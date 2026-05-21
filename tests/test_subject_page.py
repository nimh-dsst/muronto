from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import streamlit as st


def load_subject_page_module(
    monkeypatch: pytest.MonkeyPatch,
) -> ModuleType:
    monkeypatch.setattr(st, "set_page_config", lambda *args, **kwargs: None)
    module_name = "subject_page_for_tests"
    sys.modules.pop(module_name, None)
    module_path = Path(__file__).parents[1] / "pages" / "1_Subject.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_render_parent_ccn_hides_for_non_breeding_source_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject_page = load_subject_page_module(monkeypatch)
    markdown_calls: list[str] = []
    text_input_calls: list[str] = []

    monkeypatch.setattr(
        st,
        "markdown",
        lambda text: markdown_calls.append(text),
    )
    monkeypatch.setattr(
        st,
        "text_input",
        lambda label, *args, **kwargs: text_input_calls.append(label) or "",
    )

    assert subject_page.render_parent_ccn("JAX") == ""
    assert markdown_calls == []
    assert text_input_calls == []


def test_render_parent_ccn_shows_for_breeding_source_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject_page = load_subject_page_module(monkeypatch)
    markdown_calls: list[str] = []
    text_input_calls: list[str] = []

    monkeypatch.setattr(
        st,
        "markdown",
        lambda text: markdown_calls.append(text),
    )
    monkeypatch.setattr(
        st,
        "text_input",
        lambda label, *args, **kwargs: text_input_calls.append(label)
        or "654321",
    )

    assert subject_page.render_parent_ccn("Breeding") == "654321"
    assert len(markdown_calls) == 1
    assert "parent_ccn must match" in markdown_calls[0]
    assert text_input_calls == ["parent_ccn"]
