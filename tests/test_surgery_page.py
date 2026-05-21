from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
import streamlit as st

from muronto_app.subject import (
    ANIMAL_ID_KEY,
    EAR_TAG_KEY,
    SUBJECT_STATUS_INCOMPLETE,
    SUBJECT_STATUS_KEY,
)
from muronto_app.surgery import (
    CAPTION_KEY,
    ENTRY_ID_KEY,
    FILENAME_KEY,
    MIME_TYPE_KEY,
    NOTE_UPLOAD_TYPE,
    PHOTO_UPLOAD_TYPE,
    SURGERY_DATE_KEY,
    SURGERY_FILE_ATTACHMENT_CAPTION,
    TAKEN_PHOTO_UPLOAD_TYPE,
    UPLOAD_TYPE_KEY,
)


class FakeUpload:
    def __init__(
        self,
        payload: bytes,
        *,
        name: str,
        mime_type: str,
    ) -> None:
        self._payload = payload
        self.name = name
        self.type = mime_type

    def getvalue(self) -> bytes:
        return self._payload


def load_surgery_page_module(
    monkeypatch: pytest.MonkeyPatch,
) -> ModuleType:
    monkeypatch.setattr(st, "set_page_config", lambda *args, **kwargs: None)
    module_name = "surgery_page_for_tests"
    sys.modules.pop(module_name, None)
    module_path = Path(__file__).parents[1] / "pages" / "2_Surgery.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_taken_photo_slot_helpers_add_and_remove_widgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surgery_page = load_surgery_page_module(monkeypatch)
    state: dict[str, Any] = {}

    assert surgery_page.current_taken_photo_slot_ids(state) == []
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_COUNT_KEY] == 0
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_NEXT_SLOT_ID_KEY] == 1

    surgery_page.add_taken_photo_slot(state)

    assert state[surgery_page.SURGERY_TAKEN_PHOTO_SLOT_IDS_KEY] == [1]
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_COUNT_KEY] == 1
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_NEXT_SLOT_ID_KEY] == 2

    surgery_page.add_taken_photo_slot(state)

    assert state[surgery_page.SURGERY_TAKEN_PHOTO_SLOT_IDS_KEY] == [1, 2]
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_COUNT_KEY] == 2
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_NEXT_SLOT_ID_KEY] == 3

    state[surgery_page.taken_photo_widget_key(1)] = object()
    surgery_page.remove_taken_photo_slot(state, 1)

    assert state[surgery_page.SURGERY_TAKEN_PHOTO_SLOT_IDS_KEY] == [2]
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_COUNT_KEY] == 1
    assert surgery_page.taken_photo_widget_key(1) not in state

    surgery_page.remove_taken_photo_slot(state, 2)
    surgery_page.add_taken_photo_slot(state)

    assert state[surgery_page.SURGERY_TAKEN_PHOTO_SLOT_IDS_KEY] == [3]
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_COUNT_KEY] == 1
    assert state[surgery_page.SURGERY_TAKEN_PHOTO_NEXT_SLOT_ID_KEY] == 4


def test_subject_label_marks_incomplete_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surgery_page = load_surgery_page_module(monkeypatch)
    record = SimpleNamespace(
        payload={
            ANIMAL_ID_KEY: "123-4567",
            EAR_TAG_KEY: "123",
            SUBJECT_STATUS_KEY: SUBJECT_STATUS_INCOMPLETE,
        }
    )

    assert (
        surgery_page.subject_label(record)
        == "123-4567 - Ear Tag 123 (incomplete)"
    )


def test_save_general_surgery_attachments_supports_multiple_taken_photos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surgery_page = load_surgery_page_module(monkeypatch)
    calls: list[dict[str, Any]] = []

    def fake_save_surgery_file_attachment(
        page: object,
        *,
        payload: bytes,
        filename: str,
        mime_type: str,
        upload_type: str,
    ) -> SimpleNamespace:
        calls.append(
            {
                "page": page,
                "payload": payload,
                FILENAME_KEY: filename,
                MIME_TYPE_KEY: mime_type,
                UPLOAD_TYPE_KEY: upload_type,
            }
        )
        return SimpleNamespace(
            reference={
                UPLOAD_TYPE_KEY: upload_type,
                ENTRY_ID_KEY: f"entry-{len(calls)}",
                FILENAME_KEY: filename,
                CAPTION_KEY: SURGERY_FILE_ATTACHMENT_CAPTION,
                MIME_TYPE_KEY: mime_type,
            }
        )

    monkeypatch.setattr(
        surgery_page,
        "save_surgery_file_attachment",
        fake_save_surgery_file_attachment,
    )
    page = object()
    payload = {
        ANIMAL_ID_KEY: "123-4567",
        SURGERY_DATE_KEY: "20260511",
    }

    references = surgery_page.save_general_surgery_attachments(
        page=page,
        payload=payload,
        attachment_values={
            "general_notes": "",
            "note_uploads": [
                FakeUpload(
                    b"notes",
                    name="notes.pdf",
                    mime_type="application/pdf",
                )
            ],
            "photo_uploads": [
                FakeUpload(
                    b"upload",
                    name="field.jpg",
                    mime_type="image/jpeg",
                )
            ],
            "taken_photos": [
                FakeUpload(
                    b"capture-1",
                    name="ignored-1.jpg",
                    mime_type="image/jpeg",
                ),
                FakeUpload(
                    b"capture-2",
                    name="ignored-2.jpg",
                    mime_type="",
                ),
            ],
        },
    )

    assert [call["page"] for call in calls] == [page, page, page, page]
    assert [call["payload"] for call in calls] == [
        b"notes",
        b"upload",
        b"capture-1",
        b"capture-2",
    ]
    assert [call[UPLOAD_TYPE_KEY] for call in calls] == [
        NOTE_UPLOAD_TYPE,
        PHOTO_UPLOAD_TYPE,
        TAKEN_PHOTO_UPLOAD_TYPE,
        TAKEN_PHOTO_UPLOAD_TYPE,
    ]
    assert [call[FILENAME_KEY] for call in calls] == [
        "123-4567_surgery_20260511_note_upload_1_notes.pdf",
        "123-4567_surgery_20260511_photo_upload_1_field.jpg",
        "123-4567_surgery_20260511_taken_photo_1_camera_capture.jpg",
        "123-4567_surgery_20260511_taken_photo_2_camera_capture.jpg",
    ]
    assert [call[MIME_TYPE_KEY] for call in calls] == [
        "application/pdf",
        "image/jpeg",
        "image/jpeg",
        "image/jpeg",
    ]
    assert references == [
        {
            UPLOAD_TYPE_KEY: call[UPLOAD_TYPE_KEY],
            ENTRY_ID_KEY: f"entry-{index}",
            FILENAME_KEY: call[FILENAME_KEY],
            CAPTION_KEY: SURGERY_FILE_ATTACHMENT_CAPTION,
            MIME_TYPE_KEY: call[MIME_TYPE_KEY],
        }
        for index, call in enumerate(calls, start=1)
    ]
