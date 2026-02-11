"""Common exceptions for the server.

This module contains reusable exception classes that can be used
across different services and modules.
"""

from uuid import UUID


class VersionConflictError(Exception):
    """Raised when optimistic locking fails due to version mismatch.

    This exception can be used by any service that implements optimistic locking
    with version numbers to prevent concurrent modification conflicts.
    """

    def __init__(self, expected_version: int, current_version: int):
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(f"Version conflict: expected {expected_version}, current is {current_version}")


class ResourceNotFoundError(Exception):
    """Raised when a resource doesn't exist.

    Generic exception for any resource that cannot be found by its identifier.
    """

    def __init__(self, resource_type: str, identifier: str | UUID | int):
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"{resource_type} not found: {identifier}")
