#!/bin/bash

#==============================================================================
# docker-rebuild.sh
#==============================================================================
# 
# DESCRIPTION:
#   This script rebuilds a Docker container locally with build arguments.
#   It checks for a Dockerfile in the current directory, stops and removes any
#   existing container with the provided name, and builds the container.
#
# FEATURES:
#   - Checks for Dockerfile in the current directory
#   - Stops and removes existing container if it exists
#   - Uses dot-env.sh to resolve build arguments from environment files
#   - Builds the container with proper configuration
#   - Supports --no-exec option to only show the docker commands without execution
#   - Supports --verbose option to show where environment variables are resolved from
#   - Supports --dot-env option to specify a custom .env file
#   - Supports --force-dot-env option to make .env files override existing environment variables
#   - Supports --help option to display usage information
#   - Supports passing additional arguments to docker build with -- separator
#
# USAGE:
#   docker-rebuild.sh [<image-name>] [--no-exec] [--verbose] [--dot-env <env-file>] [--force-dot-env] [--help] [-- <docker-build-args>]
#
# EXAMPLES:
#   docker-rebuild.sh                          # Rebuild container using image name from Dockerfile
#   docker-rebuild.sh api-server               # Rebuild container with specified image name
#   docker-rebuild.sh --no-exec                # Show commands without execution
#   docker-rebuild.sh --verbose                # Show verbose environment variable resolution
#   docker-rebuild.sh --dot-env .env.prod      # Use a specific .env file
#   docker-rebuild.sh --force-dot-env          # Make .env files override environment variables
#   docker-rebuild.sh --help                   # Show usage information
#   docker-rebuild.sh -- --no-cache            # Pass --no-cache to docker build
#
# AUTHOR:
#   Petrarca Lab Team
#
#==============================================================================

set -e  # Exit immediately if a command exits with a non-zero status

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

# Function to display usage information
show_usage() {
  echo "USAGE:"
  echo "  docker-rebuild.sh [<image-name>] [--no-exec] [--verbose] [--dot-env <env-file>] [--force-dot-env] [--help] [-- <docker-build-args>]"
  echo ""
  echo "DESCRIPTION:"
  echo "  This script rebuilds a Docker container locally with build arguments."
  echo "  It checks for a Dockerfile in the current directory and builds the container."
  echo "  If no image name is provided, it will try to extract it from Dockerfile labels."
  echo ""
  echo "ARGUMENTS:"
  echo "  <image-name>      Optional name for the container image to build"
  echo "                    If not provided, will be extracted from Dockerfile labels"
  echo ""
  echo "OPTIONS:"
  echo "  --no-exec         Show docker commands without executing them"
  echo "  --verbose         Show where environment variables are resolved from"
  echo "  --dot-env <env-file>  Specify a custom .env file to use"
  echo "  --force-dot-env   Make .env files override existing environment variables"
  echo "  --help            Display this help message"
  echo "  -- <args>         Any arguments after -- will be passed directly to docker build"
  echo ""
  echo "EXAMPLES:"
  echo "  docker-rebuild.sh                          # Rebuild container using image name from Dockerfile"
  echo "  docker-rebuild.sh api-server               # Rebuild container with specified image name"
  echo "  docker-rebuild.sh --no-exec                # Show commands without execution"
  echo "  docker-rebuild.sh --verbose                # Show verbose environment variable resolution"
  echo "  docker-rebuild.sh --dot-env .env.prod      # Use a specific .env file"
  echo "  docker-rebuild.sh --force-dot-env          # Make .env files override environment variables"
  echo "  docker-rebuild.sh -- --no-cache            # Pass --no-cache to docker build"
}

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
IMAGE_NAME=""
NO_EXEC=false
SHOW_HELP=false
VERBOSE=false
CUSTOM_ENV_FILE=""
FORCE_DOT_ENV=false
DOCKER_ARGS=()
PARSING_DOCKER_ARGS=false

for arg in "$@"; do
  if [ "$PARSING_DOCKER_ARGS" = true ]; then
    # After -- all arguments go directly to docker build
    DOCKER_ARGS+=("$arg")
  elif [ "$arg" == "--" ]; then
    # Start parsing docker arguments
    PARSING_DOCKER_ARGS=true
  elif [ "$arg" == "--no-exec" ]; then
    NO_EXEC=true
  elif [ "$arg" == "--verbose" ] || [ "$arg" == "-v" ]; then
    VERBOSE=true
  elif [ "$arg" == "--dot-env" ]; then
    # Next argument should be the env file
    CUSTOM_ENV_FILE_NEXT=true
  elif [ "$CUSTOM_ENV_FILE_NEXT" = true ]; then
    CUSTOM_ENV_FILE="$arg"
    CUSTOM_ENV_FILE_NEXT=false
  elif [ "$arg" == "--force-dot-env" ]; then
    FORCE_DOT_ENV=true
  elif [ "$arg" == "--help" ] || [ "$arg" == "-h" ]; then
    SHOW_HELP=true
  elif [ -z "$IMAGE_NAME" ]; then
    IMAGE_NAME="$arg"
  fi
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
  show_usage
  exit 0
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOT_ENV_SCRIPT="$SCRIPT_DIR/dot-env.sh"
DOCKERFILE_INFO_SCRIPT="$SCRIPT_DIR/dockerfile-info.sh"

# If image name is not provided, try to extract it from Dockerfile
if [ -z "$IMAGE_NAME" ]; then
  if [ ! -f "$DOCKERFILE_INFO_SCRIPT" ]; then
    echo_status "Error: dockerfile-info.sh script not found at $DOCKERFILE_INFO_SCRIPT" "error"
    exit 1
  fi
  
  # Make sure dockerfile-info.sh is executable
  chmod +x "$DOCKERFILE_INFO_SCRIPT" 2>/dev/null || true
  
  # Try to extract image name from Dockerfile
  if ! IMAGE_NAME=$($DOCKERFILE_INFO_SCRIPT image-name "Dockerfile"); then
    echo_status "Error: Could not extract image name from Dockerfile and no image name provided." "error"
    exit 1
  fi
  echo_status "Using image name from Dockerfile: $IMAGE_NAME" "info"
fi

# Check if Dockerfile exists in the current directory
if [ ! -f "Dockerfile" ]; then
  echo_status "Error: Dockerfile not found in the current directory." "error"
  echo "This script must be run from a directory containing a Dockerfile."
  exit 1
fi

echo_status "=== Container Rebuild Script for $IMAGE_NAME ===" "info"

# Check if dot-env.sh exists
if [ ! -f "$DOT_ENV_SCRIPT" ]; then
  # Try to find dot-env.sh in the current directory
  if [ -f "./dot-env.sh" ]; then
    DOT_ENV_SCRIPT="./dot-env.sh"
    echo_status "Found dot-env.sh in current directory" "info"
  else
    echo_status "Error: dot-env.sh script not found at $DOT_ENV_SCRIPT or in current directory" "error"
    exit 1
  fi
fi

# Make sure dot-env.sh is executable
chmod +x "$DOT_ENV_SCRIPT" 2>/dev/null || true

# Extract ARG variables from Dockerfile
echo_status "Extracting ARG variables from Dockerfile..." "info"
ARG_VARS=($(grep -i "^ARG" Dockerfile | awk '{print $2}' | cut -d= -f1))

if [ ${#ARG_VARS[@]} -eq 0 ]; then
  echo_status "No ARG variables found in Dockerfile." "info"
  echo_status "Will build without build arguments."
  BUILD_ARG_CMD=""
else
  echo_status "Found ${#ARG_VARS[@]} ARG variables in Dockerfile:" "info"
  for var in "${ARG_VARS[@]}"; do
    echo "  - $var"
  done
fi

# Initialize build arguments
BUILD_ARG_CMD=""
RESOLVED_ARGS=()

# Process each ARG variable using dot-env.sh
if [ ${#ARG_VARS[@]} -gt 0 ]; then
  echo "🔍 Resolving build arguments using dot-env.sh..."
  
  # Adjust the custom env file path if needed
  if [ -n "$CUSTOM_ENV_FILE" ]; then
    # If the path is relative and contains the working directory, adjust it
    if [[ "$CUSTOM_ENV_FILE" == *"$(basename "$(pwd)")"* ]] && [[ "$CUSTOM_ENV_FILE" == ./* ]]; then
      CUSTOM_ENV_FILE="${CUSTOM_ENV_FILE#./$(basename "$(pwd)")/}"
      CUSTOM_ENV_FILE="./$CUSTOM_ENV_FILE"
      if [ "$VERBOSE" = true ]; then
        echo_status "Adjusted env file path to: $CUSTOM_ENV_FILE" "info"
      fi
    fi
  fi
  
  # Call dot-env.sh with all ARG variables and check exit code
  if [ "$VERBOSE" = true ]; then
    # Use verbose mode to show where variables are resolved from
    if [ -n "$CUSTOM_ENV_FILE" ] && [ "$FORCE_DOT_ENV" = true ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --verbose --dot-env "$CUSTOM_ENV_FILE" --force-dot-env "${ARG_VARS[@]}"))
    elif [ -n "$CUSTOM_ENV_FILE" ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --verbose --dot-env "$CUSTOM_ENV_FILE" "${ARG_VARS[@]}"))
    elif [ "$FORCE_DOT_ENV" = true ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --verbose --force-dot-env "${ARG_VARS[@]}"))
    else
      RESOLVED=($("$DOT_ENV_SCRIPT" --verbose "${ARG_VARS[@]}"))
    fi
  else
    # Standard mode without verbose output
    if [ -n "$CUSTOM_ENV_FILE" ] && [ "$FORCE_DOT_ENV" = true ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --dot-env "$CUSTOM_ENV_FILE" --force-dot-env "${ARG_VARS[@]}"))
    elif [ -n "$CUSTOM_ENV_FILE" ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --dot-env "$CUSTOM_ENV_FILE" "${ARG_VARS[@]}"))
    elif [ "$FORCE_DOT_ENV" = true ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --force-dot-env "${ARG_VARS[@]}"))
    else
      RESOLVED=($("$DOT_ENV_SCRIPT" "${ARG_VARS[@]}"))
    fi
  fi
  if ! [ $? -eq 0 ]; then
    echo "❌ Error: Failed to resolve all required build arguments."
    echo "Please ensure all ARG variables from the Dockerfile are defined in your environment or .env files."
    exit 1
  fi
  
  # Process the resolved variables
  for resolved_var in "${RESOLVED[@]}"; do
    # Extract variable name and value
    var_name=$(echo "$resolved_var" | cut -d= -f1)
    var_value=$(echo "$resolved_var" | cut -d= -f2-)
    
    if [ -n "$var_value" ]; then
      BUILD_ARG_CMD+=" --build-arg $var_name=\"$var_value\""
      RESOLVED_ARGS+=("$var_name=$var_value")
    fi
  done
else
  echo_status "No ARG variables found in Dockerfile." "info"
  echo_status "Will build without build arguments."
  BUILD_ARG_CMD=""
fi

# Display resolved build arguments
if [ ${#RESOLVED_ARGS[@]} -eq 0 ]; then
  echo_status "No build arguments resolved." "info"
  echo_status "Will build without build arguments."
else
  echo_status "Found ${#RESOLVED_ARGS[@]} build arguments to use:" "info"
  for ((i=0; i<${#RESOLVED_ARGS[@]}; i++)); do
    echo "   $((i+1)). ${RESOLVED_ARGS[$i]}"
  done
fi

# Extract exposed ports from Dockerfile
echo_status "Extracting exposed ports from Dockerfile..." "info"
EXPOSED_PORTS=($(grep -i "^EXPOSE" Dockerfile | awk '{for(i=2;i<=NF;i++) print $i}'))

if [ ${#EXPOSED_PORTS[@]} -eq 0 ]; then
  echo_status "Warning: No EXPOSE directives found in Dockerfile. Container may not expose any ports." "warning"
else
  echo_status "Found ${#EXPOSED_PORTS[@]} exposed ports: ${EXPOSED_PORTS[*]}" "info"
fi

# Build the docker commands
STOP_CMD="docker stop $IMAGE_NAME 2>/dev/null || true"
RM_CMD="docker rm $IMAGE_NAME 2>/dev/null || true"

# Construct docker build command with any additional arguments
DOCKER_ARGS_STR=""
if [ ${#DOCKER_ARGS[@]} -gt 0 ]; then
  for arg in "${DOCKER_ARGS[@]}"; do
    DOCKER_ARGS_STR="$DOCKER_ARGS_STR $arg"
  done
  echo_status "Additional docker build arguments: $DOCKER_ARGS_STR" "info"
fi
BUILD_CMD="docker build -t $IMAGE_NAME $DOCKER_ARGS_STR $BUILD_ARG_CMD ."

# Always get user confirmation if not in no-exec mode
echo_status "This will stop and remove any existing container named '$IMAGE_NAME' and rebuild it." "warning"
if [ ${#RESOLVED_ARGS[@]} -eq 0 ]; then
  echo_status "No build arguments will be used for the build" "warning"
else
  echo_status "The above build arguments will be used for the build" "warning"
fi
echo_status "Note: The container will only be rebuilt, not run. Use docker-run.sh to run it after rebuilding." "info"

# Show the commands that will be executed
echo_status "Commands to execute:" "info"
echo_status "$STOP_CMD" "command"
echo_status "$RM_CMD" "command"
echo_status "$BUILD_CMD" "command"

if [ "$NO_EXEC" = true ]; then
  echo_status "--no-exec option specified. Commands will be shown but not executed." "info"
else
  read -p "Proceed with rebuild? (y/n) [n]: " CONFIRM
  CONFIRM=${CONFIRM:-n}  # Default to 'n' if empty

  if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo_status "Operation cancelled by user." "warning"
    exit 0
  fi
fi

# Step 1: Stop and remove the existing container if it exists
echo_status "Stopping and removing existing container (if any)..." "info"

if [ "$NO_EXEC" = false ]; then
  eval $STOP_CMD
  eval $RM_CMD
  echo_status "Container stopped and removed." "success"
fi

# Step 2: Build the container with build arguments
echo_status "Building container with build arguments..." "info"

if [ "$NO_EXEC" = false ]; then
  eval $BUILD_CMD
  BUILD_EXIT_CODE=$?
  if [ $BUILD_EXIT_CODE -ne 0 ]; then
    echo_status "Error: Build failed with exit code $BUILD_EXIT_CODE!" "error"
    exit 1
  fi
  echo_status "Container built successfully." "success"
fi

# Container is now built but not running
if [ "$NO_EXEC" = false ]; then
  echo_status "Container built successfully." "success"
  echo_status "Note: The container will only be rebuilt, not run. Use docker-run.sh to run it after rebuilding." "warning"
else
  echo_status "Commands shown but not executed due to --no-exec option." "info"
  echo_status "Note: This script only rebuilds the container, it does not run it." "warning"
fi
echo_status "To run the container, use:" "info"
echo_status "  docker-run.sh $IMAGE_NAME" "command"

# Step 4: Display container information
if [ "$NO_EXEC" = false ]; then
  echo_status "Container information:" "info"
  docker ps | grep $IMAGE_NAME
  echo_status "Container rebuild completed successfully!" "success"
fi
