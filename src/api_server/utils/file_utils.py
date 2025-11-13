"""File utilities for MIME type detection and content handling."""

from pathlib import Path


def get_content_type_from_path(file_path: str | Path) -> tuple[str, str]:
    """Get content type and MIME type based on file extension.

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (content_type, mime_type)

    Examples:
        >>> get_content_type_from_path("template.jinja2")
        ('text', 'text/x-jinja2')
        >>> get_content_type_from_path("template.md.jinja2")
        ('text', 'text/markdown+jinja2')
        >>> get_content_type_from_path("data.json")
        ('json', 'application/json')
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    suffix = file_path.suffix.lower()
    suffixes = file_path.suffixes  # All suffixes in order

    # Handle compound extensions (e.g., .md.jinja2)
    if len(suffixes) >= 2:
        compound_suffix = "".join(suffixes[-2:]).lower()
        if compound_suffix == ".md.jinja2" or compound_suffix == ".md.jinja" or compound_suffix == ".md.j2":
            return "text", "text/markdown+jinja2"

    if suffix == ".json":
        return "json", "application/json"
    elif suffix in [".jinja", ".jinja2", ".j2"]:
        return "text", "text/x-jinja2"
    elif suffix == ".py":
        return "text", "text/x-python"
    elif suffix == ".md":
        return "text", "text/markdown"
    elif suffix == ".yaml" or suffix == ".yml":
        return "text", "text/x-yaml"
    elif suffix == ".txt":
        return "text", "text/plain"
    else:
        # Default to binary for unknown types
        return "binary", "application/octet-stream"


def get_mime_type_from_path(file_path: str | Path) -> str:
    """Get MIME type based on file extension.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string
    """
    _, mime_type = get_content_type_from_path(file_path)
    return mime_type
