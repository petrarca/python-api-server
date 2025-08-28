#!/bin/bash

#==============================================================================
# dot-env.sh
#==============================================================================
# 
# DESCRIPTION:
#   This script resolves environment variables from .env files and the current
#   environment. It can be reused by other scripts that need to source
#   environment variables.
#
# FEATURES:
#   - Resolves variables from current environment
#   - Checks .env file in current directory
#   - Checks .env file in project root (if different)
#   - Supports specifying a custom .env file with --dot-env option
#   - Supports --force-dot-env option to make .env files override environment variables
#   - Returns resolved variables in the format VAR=VALUE
#   - Supports --verbose or -v option to show where variables are retrieved from
#
# USAGE:
#   dot-env.sh [--verbose|-v] [--dot-env <env-file>] [--force-dot-env] VAR1 VAR2 VAR3 ...
#
# EXAMPLES:
#   # Source variables directly
#   eval $(./dot-env.sh VAR1 VAR2)
#
#   # Store in array for processing
#   RESOLVED=($(./dot-env.sh VAR1 VAR2))
#
#   # Show where variables are retrieved from
#   ./dot-env.sh --verbose VAR1 VAR2
#
#   # Use a specific .env file
#   ./dot-env.sh --dot-env .env.prod VAR1 VAR2
#
#   # Force .env file to override existing environment variables
#   ./dot-env.sh --force-dot-env VAR1 VAR2
#
# AUTHOR:
#   Petrarca Lab Team
#
#==============================================================================

# Function to check if a path is a valid file and not a directory
is_valid_file() {
  [ -f "$1" ] && [ ! -d "$1" ]
}

# Function to find project root
find_project_root() {
  local current_dir="$(pwd)"
  local parent_dir="$(dirname "$current_dir")"
  
  # Check if we're in frontend or backend directory
  if [[ "$current_dir" == *"/frontend" || "$current_dir" == *"/backend" ]]; then
    echo "$parent_dir"
    return
  fi
  
  # Check for common project root indicators
  if [ -f "$current_dir/package.json" ] || [ -f "$current_dir/requirements.txt" ] || [ -f "$current_dir/Dockerfile" ]; then
    echo "$current_dir"
  elif [ -f "$parent_dir/package.json" ] || [ -f "$parent_dir/requirements.txt" ] || [ -f "$parent_dir/Dockerfile" ]; then
    echo "$parent_dir"
  else
    # Couldn't determine project root
    echo ""
  fi
}

# Check for verbose flag
VERBOSE=false
CUSTOM_ENV_FILE=""
FORCE_DOT_ENV=false
VARS=() # Array to hold the variables to resolve

# Process command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --dot-env)
      if [[ -z "$2" || "$2" == --* ]]; then
        echo "Error: --dot-env option requires an argument" >&2
        exit 1
      fi
      CUSTOM_ENV_FILE="$2"
      shift 2
      ;;
    --env)
      # For backward compatibility
      if [[ -z "$2" || "$2" == --* ]]; then
        echo "Error: --env option requires an argument" >&2
        exit 1
      fi
      echo "Warning: --env option is deprecated, use --dot-env instead" >&2
      CUSTOM_ENV_FILE="$2"
      shift 2
      ;;
    --force-dot-env)
      FORCE_DOT_ENV=true
      shift
      ;;
    --*)
      echo "Error: Unknown option: $1" >&2
      exit 1
      ;;
    *)
      VARS+=("$1")
      shift
      ;;
  esac
done

# Get project root
PROJECT_ROOT=$(find_project_root)
CURRENT_DIR="$(pwd)"
IS_ROOT=false

if [ -n "$PROJECT_ROOT" ]; then
  # Check if current directory is already the root
  if [ "$PROJECT_ROOT" = "$CURRENT_DIR" ]; then
    IS_ROOT=true
  fi
fi

# Output verbose information about the environment
if [ "$VERBOSE" = true ]; then
  echo "Current directory: $CURRENT_DIR" >&2
  echo "Project root: $PROJECT_ROOT" >&2
  echo "Is root directory: $IS_ROOT" >&2
  if [ -n "$CUSTOM_ENV_FILE" ]; then
    echo "Using custom env file: $CUSTOM_ENV_FILE" >&2
  fi
  if [ "$FORCE_DOT_ENV" = true ]; then
    echo "Force .env mode: ON (env files override environment variables)" >&2
  fi
  echo "---" >&2
fi

# Prepare environment file paths
ENV_FILES=()
ENV_FILE_LABELS=()

# If a custom env file is specified, use only that one
if [ -n "$CUSTOM_ENV_FILE" ]; then
  if is_valid_file "$CUSTOM_ENV_FILE"; then
    ENV_FILES+=("$CUSTOM_ENV_FILE")
    ENV_FILE_LABELS+=("custom env file")
  else
    echo "Error: Specified env file '$CUSTOM_ENV_FILE' does not exist or is not a valid file" >&2
    exit 1
  fi
else
  # Add project root .env file if not already in root
  if [ -n "$PROJECT_ROOT" ] && [ "$IS_ROOT" = false ]; then
    if is_valid_file "$PROJECT_ROOT/.env"; then
      ENV_FILES+=("$PROJECT_ROOT/.env")
      ENV_FILE_LABELS+=("project root .env")
    fi
  fi

  # Add local .env file
  if is_valid_file ".env"; then
    ENV_FILES+=(".env")
    ENV_FILE_LABELS+=("local .env")
  fi
fi

# Initialize error flag
ALL_DEFINED=true
MISSING_VARS=()

# Process each requested variable
for var in "${VARS[@]}"; do
  # If FORCE_DOT_ENV is false (default), check environment first
  # If FORCE_DOT_ENV is true, skip environment check and go straight to .env files
  if [ "$FORCE_DOT_ENV" = false ] && [ -n "${!var+x}" ]; then
    if [ "$VERBOSE" = true ]; then
      echo "$var: Found in environment" >&2
    fi
    echo "$var=${!var}"
    continue
  fi
  
  # Try to find in .env files
  found=false
  for ((i=0; i<${#ENV_FILES[@]}; i++)); do
    # Use grep to find the variable in the file
    value=$(grep -E "^$var=" "${ENV_FILES[$i]}" | cut -d= -f2-)
    if [ -n "$value" ]; then
      if [ "$VERBOSE" = true ]; then
        echo "$var: Found in ${ENV_FILE_LABELS[$i]} (${ENV_FILES[$i]})" >&2
      fi
      echo "$var=$value"
      found=true
      break
    fi
  done
  
  # If not found in .env files but exists in environment and we're in force mode
  if [ "$found" = false ] && [ "$FORCE_DOT_ENV" = true ] && [ -n "${!var+x}" ]; then
    if [ "$VERBOSE" = true ]; then
      echo "$var: Not found in .env files, using environment value" >&2
    fi
    echo "$var=${!var}"
    found=true
  fi
  
  # If not found anywhere, mark as missing
  if [ "$found" = false ]; then
    if [ "$VERBOSE" = true ]; then
      echo "$var: Not found in any environment file or environment" >&2
    fi
    echo "$var=" >&2
    ALL_DEFINED=false
    MISSING_VARS+=("$var")
  fi
done

# Exit with error if any variables are missing
if [ "$ALL_DEFINED" = false ]; then
  echo "Error: The following variables are not defined: ${MISSING_VARS[*]}" >&2
  exit 1
fi
