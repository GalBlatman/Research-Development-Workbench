"""Recursive public export boundary; private backups retain their storage authority."""

from typing import Any

STORAGE_AUTHORITY_FIELDS = frozenset(
    {
        "original_storage_reference",
        "storage_key",
        "local_path",
        "filesystem_path",
        "storage_path",
        "original_path",
        "storage_locator",
        "internal_storage_reference",
    }
)


def sanitize_export(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize_export(item)
            for key, item in value.items()
            if key not in STORAGE_AUTHORITY_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_export(item) for item in value]
    return value
