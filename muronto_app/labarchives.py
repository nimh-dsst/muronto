"""Small LabArchives helpers used by the Streamlit pages."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from labapi import (
    ApiError,
    Attachment,
    AttachmentEntry,
    NodeExistsError,
    NotebookDirectory,
    NotebookPage,
    TextEntry,
)

from muronto_app.config import (
    CONFIG_CAPTION,
    CONFIG_FILENAME,
    CONFIG_PAGE_NAME,
    ConfigValidationError,
    clean_string,
    normalize_config,
)
from muronto_app.subject import (
    ANIMAL_ID_KEY,
    EAR_TAG_KEY,
    SUBJECT_ATTACHMENT_CAPTION,
    subject_json_filename,
)
from muronto_app.surgery import (
    CAPTION_KEY,
    ENTRY_ID_KEY,
    FILENAME_KEY,
    MIME_TYPE_KEY,
    SURGERY_ATTACHMENT_CAPTION,
    SURGERY_DATE_KEY,
    SURGERY_FILE_ATTACHMENT_CAPTION,
    SURGERY_FILE_UPLOAD_TYPES,
    UPLOAD_TYPE_KEY,
    surgery_json_filename,
)


@dataclass(frozen=True)
class ConfigReadResult:
    """Result of reading a config JSON attachment from a page."""

    entry: Any | None
    config: dict[str, Any] | None
    errors: list[str]


@dataclass(frozen=True)
class SubjectWriteResult:
    """Result of writing a subject page and JSON attachment."""

    page: Any
    attachment_entry: Any


@dataclass(frozen=True)
class SubjectRecord:
    """A subject JSON payload paired with its LabArchives page."""

    page: Any
    payload: dict[str, str]


@dataclass(frozen=True)
class SurgeryWriteResult:
    """Result of writing a surgery JSON attachment."""

    page: Any
    attachment_entry: Any
    created: bool


@dataclass(frozen=True)
class SurgeryFileAttachmentWriteResult:
    """Result of writing a surgery support-file attachment."""

    page: Any
    attachment_entry: Any
    reference: dict[str, str]
    created: bool


def find_root_config_page(notebook: Any) -> Any | None:
    """Return the root-level ``muronto_config`` page when it exists."""
    for child in notebook.children:
        if not child.is_dir() and child.name == CONFIG_PAGE_NAME:
            return child.as_page()
    return None


def create_root_config_page(notebook: Any) -> NotebookPage:
    """Create and return the root-level ``muronto_config`` page."""
    return notebook.create(NotebookPage, CONFIG_PAGE_NAME)


def is_attachment_entry(entry: object) -> bool:
    """Return whether an entry exposes the attachment API we need."""
    return isinstance(entry, AttachmentEntry) or hasattr(
        entry, "get_attachment"
    )


def _close_attachment(attachment: object) -> None:
    close = getattr(attachment, "close", None)
    if callable(close):
        close()


def _read_json_attachment(entry: Any) -> object:
    attachment = entry.get_attachment()
    try:
        raw_payload = attachment.read()
    finally:
        _close_attachment(attachment)

    return json.loads(raw_payload.decode("utf-8"))


def _json_attachment_content(
    payload: Mapping[str, Any],
    *,
    filename: str,
    caption: str,
) -> Attachment:
    raw_payload = json.dumps(
        dict(payload),
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    return Attachment(
        BytesIO(raw_payload),
        "application/json",
        filename,
        caption,
    )


def _json_reference_text_content(
    payload: Mapping[str, Any],
    *,
    attachment_entry_id: str,
    caption: str,
) -> str:
    preview_json = html.escape(json.dumps(dict(payload), indent=4))
    return f"""
<p>Reference Attachment: {html.escape(caption)}</p>
<p>Entry ID: {html.escape(attachment_entry_id)}</p>
<pre>
{preview_json}
</pre>
"""


def _is_text_entry(entry: object) -> bool:
    return isinstance(entry, TextEntry) or (
        getattr(entry, "content_type", "") == "text entry"
    )


def _find_json_reference_text_entry(
    page: Any,
    attachment_entry: Any,
) -> Any | None:
    attachment_entry_id = clean_string(getattr(attachment_entry, "id", ""))
    if not attachment_entry_id:
        return None

    entry_id_markers = (
        f"Entry ID: {attachment_entry_id}",
        f"Entry ID: {html.escape(attachment_entry_id)}",
    )
    for entry in page.entries:
        if not _is_text_entry(entry):
            continue

        content = getattr(entry, "content", None)
        if isinstance(content, str) and any(
            marker in content for marker in entry_id_markers
        ):
            return entry

    return None


def _sync_json_reference_text_entry(
    page: Any,
    payload: Mapping[str, Any],
    *,
    attachment_entry: Any,
    caption: str,
) -> None:
    text_entry = _find_json_reference_text_entry(page, attachment_entry)
    if text_entry is None:
        return

    attachment_entry_id = clean_string(getattr(attachment_entry, "id", ""))
    if not attachment_entry_id:
        return

    text_entry.content = _json_reference_text_content(
        payload,
        attachment_entry_id=attachment_entry_id,
        caption=caption,
    )


def _file_attachment_content(
    payload: bytes,
    *,
    filename: str,
    caption: str,
    mime_type: str,
) -> Attachment:
    return Attachment(
        BytesIO(payload),
        mime_type,
        filename,
        caption,
    )


def attachment_matches_config(entry: object) -> bool:
    """Return whether an attachment entry looks like ``muronto_config``."""
    if getattr(entry, "caption", None) == CONFIG_CAPTION:
        return True

    get_attachment = getattr(entry, "get_attachment", None)
    if not callable(get_attachment):
        return False

    attachment = get_attachment()
    try:
        filename = getattr(attachment, "filename", "")
        caption = getattr(attachment, "caption", "")
        return filename == CONFIG_FILENAME or caption == CONFIG_CAPTION
    finally:
        _close_attachment(attachment)


def attachment_matches_caption(entry: object, caption: str) -> bool:
    """Return whether an attachment entry has the expected caption."""
    if getattr(entry, "caption", None) == caption:
        return True

    get_attachment = getattr(entry, "get_attachment", None)
    if not callable(get_attachment):
        return False

    attachment = get_attachment()
    try:
        return getattr(attachment, "caption", "") == caption
    finally:
        _close_attachment(attachment)


def attachment_matches_filename_and_caption(
    entry: object,
    *,
    filename: str,
    caption: str,
) -> bool:
    """Return whether an attachment entry matches a filename and caption."""
    entry_filename = getattr(entry, "filename", "")
    entry_caption = getattr(entry, "caption", "")
    if entry_filename == filename and entry_caption == caption:
        return True

    get_attachment = getattr(entry, "get_attachment", None)
    if not callable(get_attachment):
        return False

    attachment = get_attachment()
    try:
        return (
            getattr(attachment, "filename", "") == filename
            and getattr(attachment, "caption", "") == caption
        )
    finally:
        _close_attachment(attachment)


def find_config_attachment(page: Any) -> Any | None:
    """Return the config JSON attachment entry from a page when present."""
    for entry in page.entries:
        if is_attachment_entry(entry) and attachment_matches_config(entry):
            return entry
    return None


def read_config_attachment(page: Any) -> ConfigReadResult:
    """Read, decode, and validate the page's config JSON attachment."""
    entry = find_config_attachment(page)
    if entry is None:
        return ConfigReadResult(
            None,
            None,
            ["No config JSON attachment found."],
        )

    try:
        decoded = _read_json_attachment(entry)
        config = normalize_config(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ConfigReadResult(
            entry,
            None,
            [f"Config JSON could not be decoded: {exc}"],
        )
    except ConfigValidationError as exc:
        return ConfigReadResult(entry, None, exc.errors)

    return ConfigReadResult(entry, config, [])


def save_config_attachment(
    page: Any,
    config: dict[str, Any],
    *,
    existing_entry: Any | None = None,
) -> Any:
    """Create or update the config JSON attachment entry."""
    if existing_entry is not None:
        existing_entry.content = _json_attachment_content(
            config,
            filename=CONFIG_FILENAME,
            caption=CONFIG_CAPTION,
        )
        _sync_json_reference_text_entry(
            page,
            config,
            attachment_entry=existing_entry,
            caption=CONFIG_CAPTION,
        )
        return existing_entry

    attachment_entry, _text_entry = page.entries.create_json_entry(
        config,
        filename=CONFIG_FILENAME,
        caption=CONFIG_CAPTION,
    )
    return attachment_entry


def resolve_notebook_folder(notebook: Any, folder_path: str) -> Any:
    """Return the folder-like notebook node for an absolute folder path."""
    cleaned_path = clean_string(folder_path)
    if not cleaned_path or cleaned_path == "/":
        return notebook

    node = notebook.traverse(cleaned_path)
    if not node.is_dir():
        raise ValueError(
            f"LabArchives home folder `{cleaned_path}` is not a folder."
        )
    return node.as_dir()


def child_named(container: Any, name: str) -> Any | None:
    """Return the first direct child with an exact display-name match."""
    for child in container.children:
        if child.name == name:
            return child
    return None


def create_subject_page_with_json(
    container: Any,
    subject_payload: Mapping[str, Any],
) -> SubjectWriteResult:
    """Create a subject page and attach the flat subject JSON payload."""
    animal_id = clean_string(subject_payload.get(ANIMAL_ID_KEY))
    if not animal_id:
        raise ValueError("animal_id is required.")

    container.refresh()
    if child_named(container, animal_id) is not None:
        raise ValueError(
            f"A LabArchives item named `{animal_id}` already exists in the "
            "selected home folder."
        )

    try:
        page = container.create(NotebookPage, animal_id)
    except NodeExistsError:
        raise ValueError(
            f"A LabArchives item named `{animal_id}` already exists in the "
            "selected home folder."
        ) from None

    attachment_entry, _text_entry = page.entries.create_json_entry(
        dict(subject_payload),
        filename=subject_json_filename(animal_id),
        caption=SUBJECT_ATTACHMENT_CAPTION,
    )
    container.refresh()
    return SubjectWriteResult(page, attachment_entry)


def find_subject_attachment(page: Any) -> Any | None:
    """Return the subject JSON attachment entry from a page when present."""
    for entry in page.entries:
        if is_attachment_entry(entry) and attachment_matches_caption(
            entry,
            SUBJECT_ATTACHMENT_CAPTION,
        ):
            return entry
    return None


def save_subject_attachment(
    page: Any,
    subject_payload: Mapping[str, Any],
) -> SubjectWriteResult:
    """Create or update the subject JSON attachment on a subject page."""
    animal_id = clean_string(subject_payload.get(ANIMAL_ID_KEY))
    if not animal_id:
        raise ValueError("animal_id is required.")

    filename = subject_json_filename(animal_id)
    existing_entry = find_subject_attachment(page)
    if existing_entry is not None:
        existing_entry.content = _json_attachment_content(
            subject_payload,
            filename=filename,
            caption=SUBJECT_ATTACHMENT_CAPTION,
        )
        _sync_json_reference_text_entry(
            page,
            subject_payload,
            attachment_entry=existing_entry,
            caption=SUBJECT_ATTACHMENT_CAPTION,
        )
        return SubjectWriteResult(page=page, attachment_entry=existing_entry)

    attachment_entry, _text_entry = page.entries.create_json_entry(
        dict(subject_payload),
        filename=filename,
        caption=SUBJECT_ATTACHMENT_CAPTION,
    )
    return SubjectWriteResult(page=page, attachment_entry=attachment_entry)


def read_subject_attachment(page: Any) -> dict[str, str] | None:
    """Read a page's subject JSON attachment when it is valid enough for UI."""
    entry = find_subject_attachment(page)
    if entry is None:
        return None

    try:
        decoded = _read_json_attachment(entry)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(decoded, Mapping):
        return None

    payload = {
        clean_string(key): clean_string(value)
        for key, value in decoded.items()
        if clean_string(key)
    }
    if not payload.get(ANIMAL_ID_KEY):
        return None
    return payload


def discover_subject_records(container: Any) -> list[SubjectRecord]:
    """Recursively return subject records below a folder-like container."""
    refresh = getattr(container, "refresh", None)
    if callable(refresh):
        refresh()

    records: list[SubjectRecord] = []
    for child in container.children:
        if child.is_dir():
            records.extend(discover_subject_records(child.as_dir()))
            continue

        page = child.as_page()
        payload = read_subject_attachment(page)
        if payload is not None:
            records.append(SubjectRecord(page=page, payload=payload))

    return sorted(
        records,
        key=lambda record: (
            record.payload.get(ANIMAL_ID_KEY, "").lower(),
            record.payload.get(EAR_TAG_KEY, "").lower(),
        ),
    )


def find_surgery_attachment(page: Any, filename: str) -> Any | None:
    """Return an existing surgery JSON attachment by filename."""
    for entry in page.entries:
        if not is_attachment_entry(entry):
            continue
        if attachment_matches_filename_and_caption(
            entry,
            filename=filename,
            caption=SURGERY_ATTACHMENT_CAPTION,
        ):
            return entry
    return None


def save_surgery_attachment(
    page: Any,
    surgery_payload: Mapping[str, Any],
) -> SurgeryWriteResult:
    """Create or update a surgery JSON attachment on a subject page."""
    animal_id = clean_string(surgery_payload.get(ANIMAL_ID_KEY))
    surgery_date = clean_string(surgery_payload.get(SURGERY_DATE_KEY))
    if not animal_id:
        raise ValueError("animal_id is required.")
    if not surgery_date:
        raise ValueError("surgery_date is required.")

    filename = surgery_json_filename(animal_id, surgery_date)
    existing_entry = find_surgery_attachment(page, filename)
    if existing_entry is not None:
        existing_entry.content = _json_attachment_content(
            surgery_payload,
            filename=filename,
            caption=SURGERY_ATTACHMENT_CAPTION,
        )
        _sync_json_reference_text_entry(
            page,
            surgery_payload,
            attachment_entry=existing_entry,
            caption=SURGERY_ATTACHMENT_CAPTION,
        )
        return SurgeryWriteResult(
            page=page,
            attachment_entry=existing_entry,
            created=False,
        )

    attachment_entry, _text_entry = page.entries.create_json_entry(
        dict(surgery_payload),
        filename=filename,
        caption=SURGERY_ATTACHMENT_CAPTION,
    )
    return SurgeryWriteResult(
        page=page,
        attachment_entry=attachment_entry,
        created=True,
    )


def find_surgery_file_attachment(page: Any, filename: str) -> Any | None:
    """Return an existing surgery support-file attachment by filename."""
    for entry in page.entries:
        if not is_attachment_entry(entry):
            continue
        if attachment_matches_filename_and_caption(
            entry,
            filename=filename,
            caption=SURGERY_FILE_ATTACHMENT_CAPTION,
        ):
            return entry
    return None


def save_surgery_file_attachment(
    page: Any,
    *,
    payload: bytes,
    filename: str,
    mime_type: str,
    upload_type: str,
) -> SurgeryFileAttachmentWriteResult:
    """Create or update a surgery support-file attachment on a subject page."""
    cleaned_filename = clean_string(filename)
    cleaned_mime_type = clean_string(mime_type)
    cleaned_upload_type = clean_string(upload_type)
    if not cleaned_filename:
        raise ValueError("filename is required.")
    if not cleaned_mime_type:
        raise ValueError("mime_type is required.")
    if cleaned_upload_type not in SURGERY_FILE_UPLOAD_TYPES:
        raise ValueError(
            "upload_type must be one of "
            + ", ".join(SURGERY_FILE_UPLOAD_TYPES)
            + "."
        )

    attachment = _file_attachment_content(
        payload,
        filename=cleaned_filename,
        caption=SURGERY_FILE_ATTACHMENT_CAPTION,
        mime_type=cleaned_mime_type,
    )
    existing_entry = find_surgery_file_attachment(page, cleaned_filename)
    if existing_entry is not None:
        existing_entry.content = attachment
        entry = existing_entry
        created = False
    else:
        entry = page.entries.create(AttachmentEntry, attachment)
        created = True

    entry_id = clean_string(getattr(entry, "id", ""))
    if not entry_id:
        raise ValueError("Uploaded attachment entry did not include an id.")

    return SurgeryFileAttachmentWriteResult(
        page=page,
        attachment_entry=entry,
        reference={
            UPLOAD_TYPE_KEY: cleaned_upload_type,
            ENTRY_ID_KEY: entry_id,
            FILENAME_KEY: cleaned_filename,
            CAPTION_KEY: SURGERY_FILE_ATTACHMENT_CAPTION,
            MIME_TYPE_KEY: cleaned_mime_type,
        },
        created=created,
    )


def sorted_directories(container: Any) -> list[Any]:
    """Return child folders sorted by display name."""
    return sorted(
        [child for child in container.children if child.is_dir()],
        key=lambda child: (child.name.lower(), child.id),
    )


def absolute_path(node: Any) -> str:
    """Return an absolute LabArchives notebook path for a folder-like node."""
    path = node.path.to_string()
    return path or "/"


def clean_child_name(raw_name: str) -> str:
    """Validate and return a new notebook child name."""
    name = raw_name.strip()
    if not name:
        raise ValueError("Enter a folder name.")
    if "/" in name:
        raise ValueError("Folder names cannot contain `/`.")
    if name in {".", ".."}:
        raise ValueError("Folder names cannot be `.` or `..`.")
    return name


def create_directory(
    container: Any,
    raw_name: str,
) -> NotebookDirectory:
    """Create a folder directly inside ``container``."""
    name = clean_child_name(raw_name)
    try:
        directory = container.create(NotebookDirectory, name)
    except NodeExistsError:
        raise ValueError(f"A folder named `{name}` already exists.") from None
    except ApiError:
        raise

    container.refresh()
    return directory
