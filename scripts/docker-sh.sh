#!/bin/bash

#==============================================================================
# docker-sh.sh
#==============================================================================
# 
# DESCRIPTION:
#   This script connects to a running Docker container with a shell or runs a 
#   specified command. It finds containers matching a pattern, allows selection
#   if multiple matches are found, and then executes a shell or command.
#
# FEATURES:
#   - Finds containers by name pattern
#   - Handles multiple matching containers with interactive selection
#   - Automatically tries sh or bash for shell access
#   - Can run custom commands in the container
#   - Can extract container name from Dockerfile labels if no pattern is provided
#   - Supports --no-exec option to only show the docker commands without execution
#   - Supports --help option to display usage information
#
# USAGE:
#   docker-sh.sh [<container-name-pattern>] [command] [--no-exec] [--help] [-- <docker-exec-args>]
#
# EXAMPLES:
#   docker-sh.sh                            # Connects with a shell using name from Dockerfile
#   docker-sh.sh api-server                # Connects with a shell
#   docker-sh.sh api-server ls -la         # Runs 'ls -la' in the container
#   docker-sh.sh api-server --no-exec      # Shows commands without execution
#   docker-sh.sh --help                    # Shows usage information
#
# AUTHOR:
#   Petrarca Lab Team
#
#==============================================================================

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display usage information
show_usage() {
  echo "USAGE:"
  echo "  docker-sh.sh [<container-name-pattern>] [command] [--no-exec] [--help] [-- <docker-exec-args>]"
  echo ""
  echo "DESCRIPTION:"
  echo "  This script connects to a running Docker container with a shell or runs a"
  echo "  specified command. It finds containers matching a pattern, allows selection"
  echo "  if multiple matches are found, and then executes a shell or command."
  echo ""
  echo "ARGUMENTS:"
  echo "  <container-name-pattern>   Optional pattern to match container names"
  echo "                             If not provided, will be extracted from Dockerfile labels"
  echo "  [command]                  Optional command to run in the container"
  echo ""
  echo "OPTIONS:"
  echo "  --no-exec                  Show docker commands without executing them"
  echo "  --help                     Display this help message"
  echo "  -- <args>                  Any arguments after -- will be passed directly to docker exec"
  echo ""
  echo "EXAMPLES:"
  echo "  docker-sh.sh                            # Connects with a shell using name from Dockerfile"
  echo "  docker-sh.sh api-server            # Connects with a shell"
  echo "  docker-sh.sh api-server ls -la     # Runs 'ls -la' in the container"
  echo "  docker-sh.sh api-server --no-exec  # Shows commands without execution"
  echo "  docker-sh.sh -- -u root                 # Connect with a shell as root user"
  echo "  docker-sh.sh api-server -- -w /app # Run in the /app directory"
}

# Define colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if output is to a terminal
if [ -t 1 ]; then
  USE_COLOR=true
else
  USE_COLOR=false
  # Empty strings if no color
  GREEN='' YELLOW='' RED='' BLUE='' CYAN='' NC=''
fi

# Function for colored output
echo_status() {
  if [ "$USE_COLOR" = true ]; then
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
  else
    printf "%s\n" "$1"
  fi
}

# Parse arguments
CONTAINER_NAME_PATTERN=""
COMMAND_ARGS=()
DOCKER_ARGS=()
NO_EXEC=false
SHOW_HELP=false
PARSING_DOCKER_ARGS=false
PARSING_COMMAND=false

# First pass: extract special flags like --no-exec and --help
for arg in "$@"; do
  if [ "$arg" = "--no-exec" ]; then
    NO_EXEC=true
  elif [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
    SHOW_HELP=true
  fi
done

# Process all arguments
while [ $# -gt 0 ]; do
  if [ "$PARSING_DOCKER_ARGS" = true ]; then
    # After -- all arguments go directly to docker exec
    DOCKER_ARGS+=("$1")
    shift
  elif [ "$1" = "--" ]; then
    # Start parsing docker arguments
    PARSING_DOCKER_ARGS=true
    shift
  elif [ "$1" = "--no-exec" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    # Skip these flags as they've already been processed
    shift
  elif [ -z "$CONTAINER_NAME_PATTERN" ]; then
    CONTAINER_NAME_PATTERN="$1"
    shift
  else
    # All remaining arguments are treated as the command to run
    COMMAND_ARGS+=("$1")
    shift
  fi
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
  show_usage
  exit 0
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKERFILE_INFO_SCRIPT="$SCRIPT_DIR/dockerfile-info.sh"

# If container name pattern is not provided, try to extract it from Dockerfile
if [ -z "$CONTAINER_NAME_PATTERN" ]; then
  if [ -f "Dockerfile" ]; then
    if [ ! -f "$DOCKERFILE_INFO_SCRIPT" ]; then
      echo_status "Error: dockerfile-info.sh script not found at $DOCKERFILE_INFO_SCRIPT" "error"
      exit 1
    fi
    
    # Make sure dockerfile-info.sh is executable
    chmod +x "$DOCKERFILE_INFO_SCRIPT" 2>/dev/null || true
    
    # Try to extract image name from Dockerfile
    if ! CONTAINER_NAME_PATTERN=$($DOCKERFILE_INFO_SCRIPT image-name "Dockerfile"); then
      echo_status "Error: Could not extract image name from Dockerfile and no container name pattern provided." "error"
      echo ""
      show_usage
      exit 1
    fi
    echo_status "Using container name from Dockerfile: $CONTAINER_NAME_PATTERN" "info"
  else
    echo_status "Error: No container name pattern provided and no Dockerfile found in the current directory." "error"
    echo ""
    show_usage
    exit 1
  fi
fi

# Determine if command was provided
if [ ${#COMMAND_ARGS[@]} -gt 0 ]; then
  COMMAND_PROVIDED=true
else
  COMMAND_PROVIDED=false
fi



# Find running containers matching the pattern
echo_status "Finding running containers matching pattern: $CONTAINER_NAME_PATTERN" "info"
FIND_CMD="docker ps --format \"{{.ID}}|{{.Names}}|{{.Image}}\" | grep -i \"$CONTAINER_NAME_PATTERN\" || true"
echo_status "Command to execute:" "info"
echo_status "$FIND_CMD" "command"

if [ "$NO_EXEC" = false ]; then
  CONTAINERS=$(eval "$FIND_CMD")
else
  echo_status "--no-exec option specified. Command will not be executed." "info"
  exit 0
fi

# Check if any containers were found
if [ -z "$CONTAINERS" ]; then
  echo_status "Error: No running containers found matching pattern: $CONTAINER_NAME_PATTERN" "error"
  echo_status "Available running containers:" "info"
  docker ps --format "{{.Names}}" | sed 's/^/  - /'
  exit 1
fi

# Count number of matching containers
CONTAINER_COUNT=$(echo "$CONTAINERS" | wc -l | tr -d ' ')

if [ "$CONTAINER_COUNT" -eq 1 ]; then
  # Only one container found, use it directly
  CONTAINER_ID=$(echo "$CONTAINERS" | cut -d'|' -f1)
  CONTAINER_NAME=$(echo "$CONTAINERS" | cut -d'|' -f2)
  CONTAINER_IMAGE=$(echo "$CONTAINERS" | cut -d'|' -f3)
  
  echo_status "Found container: $CONTAINER_NAME (ID: $CONTAINER_ID, Image: $CONTAINER_IMAGE)" "success"
else
  # Multiple containers found, let user select one
  echo_status "Found $CONTAINER_COUNT containers matching pattern: $CONTAINER_NAME_PATTERN" "info"
  echo_status "Please select a container:" "info"
  
  # Display containers with numbers
  COUNTER=1
  while IFS= read -r CONTAINER_LINE; do
    CONTAINER_ID=$(echo "$CONTAINER_LINE" | cut -d'|' -f1)
    CONTAINER_NAME=$(echo "$CONTAINER_LINE" | cut -d'|' -f2)
    CONTAINER_IMAGE=$(echo "$CONTAINER_LINE" | cut -d'|' -f3)
    
    echo_status "  $COUNTER) $CONTAINER_NAME (ID: $CONTAINER_ID, Image: $CONTAINER_IMAGE)" "info"
    COUNTER=$((COUNTER + 1))
  done <<< "$CONTAINERS"
  
  # Get user selection
  SELECTION=""
  while [[ ! "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -lt 1 ] || [ "$SELECTION" -gt "$CONTAINER_COUNT" ]; do
    echo -n "Enter selection [1-$CONTAINER_COUNT]: "
    read SELECTION
    
    if [[ ! "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -lt 1 ] || [ "$SELECTION" -gt "$CONTAINER_COUNT" ]; then
      echo_status "Invalid selection. Please enter a number between 1 and $CONTAINER_COUNT." "error"
    fi
  done
  
  # Get the selected container
  SELECTED_CONTAINER=$(echo "$CONTAINERS" | sed -n "${SELECTION}p")
  CONTAINER_ID=$(echo "$SELECTED_CONTAINER" | cut -d'|' -f1)
  CONTAINER_NAME=$(echo "$SELECTED_CONTAINER" | cut -d'|' -f2)
  CONTAINER_IMAGE=$(echo "$SELECTED_CONTAINER" | cut -d'|' -f3)
  
  echo_status "Selected container: $CONTAINER_NAME (ID: $CONTAINER_ID, Image: $CONTAINER_IMAGE)" "success"
fi

# Execute the command or connect with a shell
if [ "$COMMAND_PROVIDED" = true ]; then
  # Construct docker exec command with any additional arguments
  DOCKER_ARGS_STR=""
  if [ ${#DOCKER_ARGS[@]} -gt 0 ]; then
    for arg in "${DOCKER_ARGS[@]}"; do
      DOCKER_ARGS_STR="$DOCKER_ARGS_STR $arg"
    done
    echo_status "Additional docker exec arguments: $DOCKER_ARGS_STR" "info"
  fi

  # Run the specified command
  echo_status "Running command in container: ${COMMAND_ARGS[*]}" "info"
  EXEC_CMD="docker exec -it $DOCKER_ARGS_STR \"$CONTAINER_ID\" ${COMMAND_ARGS[*]}"
  echo_status "Command to execute:" "info"
  echo_status "$EXEC_CMD" "command"
  eval "$EXEC_CMD"
  echo_status "Command execution completed" "success"
else
  # Construct docker exec command with any additional arguments
  DOCKER_ARGS_STR=""
  if [ ${#DOCKER_ARGS[@]} -gt 0 ]; then
    for arg in "${DOCKER_ARGS[@]}"; do
      DOCKER_ARGS_STR="$DOCKER_ARGS_STR $arg"
    done
    echo_status "Additional docker exec arguments: $DOCKER_ARGS_STR" "info"
  fi

  # Try to exec into the container with sh or bash
  echo_status "Connecting to container with shell..." "info"

  # First try sh, then bash if sh fails
  SH_CHECK_CMD="docker exec -it $DOCKER_ARGS_STR \"$CONTAINER_ID\" sh -c \"command -v sh\" &>/dev/null"
  BASH_CHECK_CMD="docker exec -it $DOCKER_ARGS_STR \"$CONTAINER_ID\" sh -c \"command -v bash\" &>/dev/null"
  
  echo_status "Checking for available shells..." "info"
  if eval "$SH_CHECK_CMD"; then
    echo_status "Using sh shell" "info"
    echo_status "Type 'exit' to leave the container shell" "info"
    docker exec -it $DOCKER_ARGS_STR "$CONTAINER_ID" sh
  elif eval "$BASH_CHECK_CMD"; then
    echo_status "Using bash shell" "info"
    echo_status "Type 'exit' to leave the container shell" "info"
    docker exec -it $DOCKER_ARGS_STR "$CONTAINER_ID" bash
  else
    echo_status "Neither sh nor bash found in container. Trying direct exec..." "warning"
    docker exec -it $DOCKER_ARGS_STR "$CONTAINER_ID" /bin/sh || docker exec -it $DOCKER_ARGS_STR "$CONTAINER_ID" /bin/bash || {
      echo_status "Error: Failed to find a usable shell in the container." "error"
      exit 1
    }
  fi

  echo_status "Exited container shell" "info"
fi
