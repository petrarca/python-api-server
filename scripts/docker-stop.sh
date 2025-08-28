#!/bin/bash

#==============================================================================
# docker-stop.sh
#==============================================================================
# 
# DESCRIPTION:
#   This script stops all running Docker containers that match a given name
#   pattern. It provides a simple way to clean up multiple containers at once.
#
# FEATURES:
#   - Finds and stops all containers matching a name pattern
#   - Shows a summary of stopped containers
#   - Can optionally remove containers after stopping them
#   - Can extract container name from Dockerfile labels if no pattern is provided
#   - Supports --no-exec option to only show the docker commands without execution
#   - Supports --help option to display usage information
#
# USAGE:
#   docker-stop.sh [<container-name-pattern>] [--rm] [--no-exec] [--help]
#
# EXAMPLES:
#   docker-stop.sh                   # Stops container using the image name from Dockerfile
#   docker-stop.sh api-server        # Stops all containers with 'api-server' in the name
#   docker-stop.sh frontend --rm     # Stops and removes all containers with 'frontend' in the name
#   docker-stop.sh api-server --no-exec # Shows commands without executing them
#   docker-stop.sh --help            # Shows usage information
#
# AUTHOR:
#   Petrarca Lab Team
#
#==============================================================================

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display usage information
show_usage() {
  echo "USAGE:"
  echo "  docker-stop.sh [<container-name-pattern>] [--rm] [--no-exec] [--help]"
  echo ""
  echo "DESCRIPTION:"
  echo "  This script stops all running Docker containers that match a given name"
  echo "  pattern. It provides a simple way to clean up multiple containers at once."
  echo ""
  echo "ARGUMENTS:"
  echo "  <container-name-pattern>   Optional pattern to match image names"
  echo "                             If not provided, will be extracted from Dockerfile labels"
  echo ""
  echo "OPTIONS:"
  echo "  --rm, --remove          Remove containers after stopping them"
  echo "  --no-exec               Show docker commands without executing them"
  echo "  --help                  Display this help message"
  echo ""
  echo "EXAMPLES:"
  echo "  docker-stop.sh                   # Stops container using name from Dockerfile"
  echo "  docker-stop.sh api-server            # Stops all containers with 'api-server' in the name"
  echo "  docker-stop.sh api-server --rm     # Stops and removes all containers with 'frontend' in the name"
  echo "  docker-stop.sh api-server --no-exec  # Shows commands without executing them"
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

# Parse command line arguments
REMOVE_CONTAINERS=false
CONTAINER_NAME_PATTERN=""
NO_EXEC=false
SHOW_HELP=false

for arg in "$@"; do
  if [ "$arg" = "--rm" ] || [ "$arg" = "--remove" ]; then
    REMOVE_CONTAINERS=true
  elif [ "$arg" = "--no-exec" ]; then
    NO_EXEC=true
  elif [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
    SHOW_HELP=true
  elif [ -z "$CONTAINER_NAME_PATTERN" ]; then
    CONTAINER_NAME_PATTERN="$arg"
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
    # We use image name as container name pattern
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

# Show what will be done
if [ "$REMOVE_CONTAINERS" = true ]; then
  echo_status "Will stop and remove containers matching: $CONTAINER_NAME_PATTERN" "info"
else
  echo_status "Will stop containers matching: $CONTAINER_NAME_PATTERN" "info"
fi

if [ "$NO_EXEC" = true ]; then
  echo_status "--no-exec option specified. Commands will be shown but not executed." "info"
fi

# Find running containers matching the pattern
echo_status "Finding running containers matching pattern: $CONTAINER_NAME_PATTERN" "info"
FIND_CMD="docker ps -q --filter \"name=$CONTAINER_NAME_PATTERN\""
echo_status "Command to execute:" "info"
echo_status "$FIND_CMD" "command"

if [ "$NO_EXEC" = false ]; then
  RUNNING_CONTAINER_IDS=$(eval "$FIND_CMD")
else
  echo_status "Command would return IDs of running containers matching the pattern." "info"
  RUNNING_CONTAINER_IDS=""
fi

# Find exited containers matching the pattern
echo_status "Finding exited containers matching pattern: $CONTAINER_NAME_PATTERN" "info"
FIND_EXITED_CMD="docker ps -a -q --filter \"name=$CONTAINER_NAME_PATTERN\" --filter \"status=exited\""
echo_status "Command to execute:" "info"
echo_status "$FIND_EXITED_CMD" "command"

if [ "$NO_EXEC" = false ]; then
  EXITED_CONTAINER_IDS=$(eval "$FIND_EXITED_CMD")
else
  echo_status "Command would return IDs of exited containers matching the pattern." "info"
  EXITED_CONTAINER_IDS=""
fi

# Find all containers (including stopped ones) if --rm is specified
if [ "$REMOVE_CONTAINERS" = true ]; then
  FIND_ALL_CMD="docker ps -a -q --filter \"name=$CONTAINER_NAME_PATTERN\""
  echo_status "Command to execute:" "info"
  echo_status "$FIND_ALL_CMD" "command"
  
  if [ "$NO_EXEC" = false ]; then
    ALL_CONTAINER_IDS=$(eval "$FIND_ALL_CMD")
  else
    echo_status "Command would return IDs of all containers (including stopped) matching the pattern." "info"
    ALL_CONTAINER_IDS=""
  fi
fi

# Check if any running containers were found (only if not in no-exec mode)
if [ "$NO_EXEC" = false ] && [ -z "$RUNNING_CONTAINER_IDS" ]; then
  echo_status "Warning: No running containers found matching pattern: $CONTAINER_NAME_PATTERN" "warning"
  
  # If --rm is specified but no running containers, still try to remove stopped containers
  if [ "$REMOVE_CONTAINERS" = true ] && [ -n "$ALL_CONTAINER_IDS" ]; then
    echo_status "Found stopped containers to remove." "info"
  # If exited containers were found, report them
  elif [ -n "$EXITED_CONTAINER_IDS" ]; then
    EXITED_COUNT=$(echo "$EXITED_CONTAINER_IDS" | wc -l | tr -d ' ')
    echo_status "Found $EXITED_COUNT exited container(s) matching pattern: $CONTAINER_NAME_PATTERN" "info"
  else
    # If no containers at all, exit
    if [ "$REMOVE_CONTAINERS" = true ] && [ -z "$ALL_CONTAINER_IDS" ] && [ -z "$EXITED_CONTAINER_IDS" ]; then
      echo_status "Warning: No containers (running or stopped) found matching pattern: $CONTAINER_NAME_PATTERN" "warning"
      exit 0
    elif [ "$REMOVE_CONTAINERS" = false ] && [ -z "$EXITED_CONTAINER_IDS" ]; then
      exit 0
    fi
  fi
fi

# Process running containers if any were found or if in no-exec mode
if [ "$NO_EXEC" = true ] || [ -n "$RUNNING_CONTAINER_IDS" ]; then
  # Count number of matching running containers if not in no-exec mode
  if [ "$NO_EXEC" = false ]; then
    RUNNING_COUNT=$(echo "$RUNNING_CONTAINER_IDS" | wc -l | tr -d ' ')
    echo_status "Stopping $RUNNING_COUNT container(s) matching pattern: $CONTAINER_NAME_PATTERN" "info"
  else
    echo_status "Would stop containers matching pattern: $CONTAINER_NAME_PATTERN" "info"
  fi

  # Display containers that will be stopped
  echo_status "Containers to stop:" "info"
  LIST_CMD="docker ps --filter \"name=$CONTAINER_NAME_PATTERN\" --format \"table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\""
  echo_status "Command to execute:" "info"
  echo_status "$LIST_CMD" "command"
  
  if [ "$NO_EXEC" = false ]; then
    eval "$LIST_CMD"
  fi

  # Stop all matching containers
  echo_status "Stopping containers..." "info"
  
  if [ "$NO_EXEC" = false ]; then
    for container_id in $RUNNING_CONTAINER_IDS; do
      STOP_CMD="docker stop \"$container_id\""
      echo_status "Command to execute:" "info"
      echo_status "$STOP_CMD" "command"
      eval "$STOP_CMD"
    done
    echo_status "Successfully stopped $RUNNING_COUNT container(s)." "success"
    
    # Update the list of exited containers after stopping
    if [ -n "$RUNNING_CONTAINER_IDS" ]; then
      echo_status "Updating list of exited containers after stopping..." "info"
      FIND_EXITED_CMD="docker ps -a -q --filter \"name=$CONTAINER_NAME_PATTERN\" --filter \"status=exited\""
      echo_status "Command to execute:" "info"
      echo_status "$FIND_EXITED_CMD" "command"
      EXITED_CONTAINER_IDS=$(eval "$FIND_EXITED_CMD")
    fi
  else
    echo_status "Would execute: docker stop <container_id> for each matching container" "info"
  fi
fi

# Remove containers if --rm flag is provided or if exited containers were found
if [ "$REMOVE_CONTAINERS" = true ] || [ -n "$EXITED_CONTAINER_IDS" ]; then
  if [ "$REMOVE_CONTAINERS" = true ]; then
    echo_status "Removing all containers..." "info"
    CONTAINER_IDS_TO_REMOVE="$ALL_CONTAINER_IDS"
  else
    echo_status "Removing exited containers..." "info"
    CONTAINER_IDS_TO_REMOVE="$EXITED_CONTAINER_IDS"
  fi
  
  # Count number of containers to remove if not in no-exec mode
  if [ "$NO_EXEC" = false ]; then
    REMOVE_COUNT=$(echo "$CONTAINER_IDS_TO_REMOVE" | wc -l | tr -d ' ')
  fi
  
  # Display containers that will be removed
  echo_status "Containers to remove:" "info"
  if [ "$REMOVE_CONTAINERS" = true ]; then
    LIST_ALL_CMD="docker ps -a --filter \"name=$CONTAINER_NAME_PATTERN\" --format \"table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\""
  else
    LIST_ALL_CMD="docker ps -a --filter \"name=$CONTAINER_NAME_PATTERN\" --filter \"status=exited\" --format \"table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\""
  fi
  echo_status "Command to execute:" "info"
  echo_status "$LIST_ALL_CMD" "command"
  
  if [ "$NO_EXEC" = false ]; then
    eval "$LIST_ALL_CMD"
  fi
  
  # Remove all matching containers
  if [ "$NO_EXEC" = false ]; then
    for container_id in $CONTAINER_IDS_TO_REMOVE; do
      RM_CMD="docker rm \"$container_id\""
      echo_status "Command to execute:" "info"
      echo_status "$RM_CMD" "command"
      eval "$RM_CMD"
    done
    echo_status "Successfully removed $REMOVE_COUNT container(s)." "success"
  else
    echo_status "Would execute: docker rm <container_id> for each matching container" "info"
  fi
fi

# If --rm was specified, also show if any containers with the pattern still exist
if [ "$REMOVE_CONTAINERS" = true ]; then
  CHECK_REMAINING_CMD="docker ps -a -q --filter \"name=$CONTAINER_NAME_PATTERN\""
  echo_status "Command to execute:" "info"
  echo_status "$CHECK_REMAINING_CMD" "command"
  REMAINING=$(eval "$CHECK_REMAINING_CMD")
  
  if [ -n "$REMAINING" ]; then
    echo_status "Warning: Some containers matching '$CONTAINER_NAME_PATTERN' still exist:" "warning"
    SHOW_REMAINING_CMD="docker ps -a --filter \"name=$CONTAINER_NAME_PATTERN\" --format \"table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\""
    echo_status "Command to execute:" "info"
    echo_status "$SHOW_REMAINING_CMD" "command"
    eval "$SHOW_REMAINING_CMD"
  else
    echo_status "No containers matching '$CONTAINER_NAME_PATTERN' remain." "success"
  fi
fi
