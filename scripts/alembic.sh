#!/bin/bash

# Define colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function for colored output
echo_status() {
  if [ "$2" = "error" ]; then
    printf "%b%s%b\n" "$RED" "$1" "$NC"
  elif [ "$2" = "warning" ]; then
    printf "%b%s%b\n" "$YELLOW" "$1" "$NC"
  elif [ "$2" = "success" ]; then
    printf "%b%s%b\n" "$GREEN" "$1" "$NC"
  elif [ "$2" = "info" ]; then
    printf "%b%s%b\n" "$BLUE" "$1" "$NC"
  elif [ "$2" = "command" ]; then
    printf "%b%s%b\n" "$CYAN" "$1" "$NC"
  else
    printf "%s\n" "$1"
  fi
}

# Default environment file
ENV_FILE="$(dirname "$0")/../.env.db-remote"
DOT_ENV_ARG="--dot-env"
YES_ARG="--yes"
AUTO_CONFIRM=false

# Process arguments to check for --dot-env parameter
ALEMBIC_ARGS=()
i=1
while [ $i -le $# ]; do
  arg="${!i}"
  
  if [ "$arg" = "$DOT_ENV_ARG" ] && [ $i -lt $# ]; then
    # Next argument is the env file
    i=$((i+1))
    ENV_FILE="${!i}"
    echo_status "Using custom environment file: $ENV_FILE" "info"
  elif [ "$arg" = "$YES_ARG" ]; then
    # Auto-confirm execution
    AUTO_CONFIRM=true
    echo_status "Auto-confirming execution" "info"
  else
    # Add to alembic arguments
    ALEMBIC_ARGS+=("$arg")
  fi
  
  i=$((i+1))
done

# Source the environment file if it exists
if [ -f "$ENV_FILE" ]; then
  echo_status "Sourcing environment file: $ENV_FILE" "info"
  source "$ENV_FILE"
else
  echo_status "Warning: Environment file not found: $ENV_FILE" "error"
  exit 1
fi

# Re-export environment variables to ensure they're available to subprocesses
export PG_URL
export API_SERVER_DATABASE_URL
export API_SERVER_PSQL_URL

# Print the database URL (masked password)
echo_status "Using database: ${API_SERVER_DATABASE_URL//:*@/:***@}" "info"

# Show the command that will be executed
ALEMBIC_CMD="alembic ${ALEMBIC_ARGS[*]}"
echo_status "About to execute: $ALEMBIC_CMD" "command"

# Ask for confirmation if not auto-confirmed
if [ "$AUTO_CONFIRM" = false ]; then
  # Use a different approach for confirmation
  printf "Continue? (y/N): "
  read -r confirm
  echo # Add a newline after input
  
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo_status "Operation cancelled by user" "warning"
    exit 0
  fi
fi

# Run Alembic with filtered arguments
echo_status "Executing Alembic command..." "success"
alembic "${ALEMBIC_ARGS[@]}"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo_status "Alembic command completed successfully" "success"
else
  echo_status "Alembic command failed with exit code $EXIT_CODE" "error"
fi

exit $EXIT_CODE
