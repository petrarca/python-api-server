"""Global constants for the API server.

This module defines constants used throughout the application to avoid
hardcoded strings and make the codebase more maintainable.
"""

# Profile names for conditional feature enabling
PROFILE_REST = "rest"
PROFILE_GRAPHQL = "graphql"

# Readiness pipeline stage names
STAGE_DATABASE = "database"
STAGE_DB_SCHEMA = "db_schema"

# Future stage constants (uncomment as needed):
# STAGE_CACHE = "cache"
# STAGE_MESSAGING = "messaging"
# STAGE_FILE_STORAGE = "file_storage"

# Future API constants (uncomment as needed):
# API_VERSION = "v1"
# DEFAULT_PAGE_SIZE = 50
# DEFAULT_TIMEOUT = 30
