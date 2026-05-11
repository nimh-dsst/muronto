"""Small LabArchives helpers used by the Streamlit pages."""

from __future__ import annotations

import json
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
)

from muronto_app.config import (
    CONFIG_CAPTION,
    CONFIG_FILENAME,
    CONFIG_PAGE_NAME,
    ConfigValidationError,
    normalize_config,
)


@dataclass(frozen=True)
class ConfigReadResult:
    """Result of reading a config JSON attachment from a page."""

    entry: Any | None
    config: dict[str, Any] | None
    errors: list[str]


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
        attachment = entry.get_attachment()
        try:
            raw_payload = attachment.read()
        finally:
            _close_attachment(attachment)

        decoded = json.loads(raw_payload.decode("utf-8"))
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
    payload = json.dumps(config, indent=2, sort_keys=True).encode("utf-8")

    if existing_entry is not None:
        existing_entry.content = Attachment(
            BytesIO(payload),
            "application/json",
            CONFIG_FILENAME,
            CONFIG_CAPTION,
        )
        return existing_entry

    attachment_entry, _text_entry = page.entries.create_json_entry(
        config,
        filename=CONFIG_FILENAME,
        caption=CONFIG_CAPTION,
    )
    return attachment_entry


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
