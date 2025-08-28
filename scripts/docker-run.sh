#!/bin/bash

#==============================================================================
# docker-run.sh
#==============================================================================
# 
# DESCRIPTION:
#   This script runs a Docker container based on a Dockerfile in the specified
#   working directory. It extracts environment variables and exposed ports from
#   the Dockerfile, resolves variables using dot-env.sh, and runs the container
#   with the appropriate configuration.
#
# FEATURES:
#   - Checks for Dockerfile in the working directory
#   - Extracts environment variables and exposed ports from the Dockerfile
#   - Uses dot-env.sh to resolve environment variables from .env files
#   - Maps exposed ports automatically
#   - Can extract container name from Dockerfile labels if no name is provided
#   - Supports --no-exec option to only show the docker command without execution
#   - Supports --verbose option to show where environment variables are resolved from
#   - Supports --dot-env option to specify a custom .env file
#   - Supports --force-dot-env option to make .env files override existing environment variables
#   - Supports --help option to display usage information
#
# USAGE:
#   docker-run.sh [<container-name>] [working-dir] [--no-exec] [--verbose] [--dot-env <env-file>] [--force-dot-env] [--help] [-- <docker-run-args>]
#
# EXAMPLES:
#   docker-run.sh                                 # Run container using name from Dockerfile
#   docker-run.sh api-server                      # Run container from current directory
#   docker-run.sh api-server ../some-dir          # Run container from specified directory
#   docker-run.sh api-server --no-exec            # Show command without execution
#   docker-run.sh api-server --verbose            # Show verbose environment variable resolution
#   docker-run.sh api-server --dot-env .env.prod  # Use a specific .env file
#   docker-run.sh api-server --force-dot-env      # Make .env files override environment variables
#   docker-run.sh --help                          # Show usage information
#
# AUTHOR:
#   Petrarca Lab Team
#
#==============================================================================

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display usage information
show_usage() {
  echo "USAGE:"
  echo "  docker-run.sh [<container-name>] [working-dir] [--no-exec] [--verbose] [--dot-env <env-file>] [--force-dot-env] [--help] [-- <docker-run-args>]"
  echo ""
  echo "DESCRIPTION:"
  echo "  This script runs a Docker container based on a Dockerfile in the specified"
  echo "  working directory. It extracts environment variables and exposed ports from"
  echo "  the Dockerfile, resolves variables using dot-env.sh, and runs the container"
  echo "  with the appropriate configuration."
  echo ""
  echo "ARGUMENTS:"
  echo "  <container-name>   Optional name for the container to run"
  echo "                     If not provided, will be extracted from Dockerfile labels"
  echo "  [working-dir]      Directory containing the Dockerfile (default: current directory)"
  echo ""
  echo "OPTIONS:"
  echo "  --no-exec          Show docker command without executing it"
  echo "  --verbose          Show where environment variables are resolved from"
  echo "  --dot-env <env-file>  Specify a custom .env file to use"
  echo "  --force-dot-env    Make .env files override existing environment variables"
  echo "  --help             Display this help message"
  echo "  -- <args>          Any arguments after -- will be passed directly to docker run"
  echo ""
  echo "EXAMPLES:"
  echo "  docker-run.sh                                 # Run container using name from Dockerfile"
  echo "  docker-run.sh api-server                 # Run container from current directory"
  echo "  docker-run.sh api-server ../some-dir     # Run container from specified directory"
  echo "  docker-run.sh api-server --no-exec       # Show command without execution"
  echo "  docker-run.sh api-server --verbose       # Show verbose environment variable resolution"
  echo "  docker-run.sh api-server --dot-env .env.prod # Use a specific .env file"
  echo "  docker-run.sh api-server --force-dot-env # Make .env files override environment variables"
  echo "  docker-run.sh -- -it --rm                     # Pass -it and --rm to docker run"
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
CONTAINER_NAME=""
WORKING_DIR="."
NO_EXEC=false
VERBOSE=false
SHOW_HELP=false
CUSTOM_ENV_FILE=""
FORCE_DOT_ENV=false
DOCKER_ARGS=()
PARSING_DOCKER_ARGS=false

for arg in "$@"; do
  if [ "$PARSING_DOCKER_ARGS" = true ]; then
    # After -- all arguments go directly to docker run
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
  elif [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME="$arg"
  elif [ -z "$WORKING_DIR" ] || [ "$WORKING_DIR" == "." ]; then
    WORKING_DIR="$arg"
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

# If container name is not provided, try to extract it from Dockerfile
if [ -z "$CONTAINER_NAME" ]; then
  # First check if we're in the working directory with a Dockerfile
  DOCKERFILE_PATH="Dockerfile"
  if [ "$WORKING_DIR" != "." ] && [ ! -f "$DOCKERFILE_PATH" ]; then
    # If not in current directory, check the working directory
    if [ -d "$WORKING_DIR" ] && [ -f "$WORKING_DIR/Dockerfile" ]; then
      DOCKERFILE_PATH="$WORKING_DIR/Dockerfile"
    fi
  fi
  
  if [ -f "$DOCKERFILE_PATH" ]; then
    if [ ! -f "$DOCKERFILE_INFO_SCRIPT" ]; then
      echo_status "Error: dockerfile-info.sh script not found at $DOCKERFILE_INFO_SCRIPT" "error"
      exit 1
    fi
    
    # Make sure dockerfile-info.sh is executable
    chmod +x "$DOCKERFILE_INFO_SCRIPT" 2>/dev/null || true
    
    # Try to extract image name from Dockerfile
    if ! CONTAINER_NAME=$($DOCKERFILE_INFO_SCRIPT image-name "$DOCKERFILE_PATH"); then
      echo_status "Error: Could not extract image name from Dockerfile and no container name provided." "error"
      echo ""
      show_usage
      exit 1
    fi
    echo_status "Using container name from Dockerfile: $CONTAINER_NAME" "info"
  else
    echo_status "Error: No container name provided and no Dockerfile found in the current directory or specified working directory." "error"
    echo ""
    show_usage
    exit 1
  fi
fi

echo_status "=== Docker Run Script for $CONTAINER_NAME ===" "info"

# Change to working directory if specified
if [ "$WORKING_DIR" != "." ]; then
  echo_status "Changing to working directory: $WORKING_DIR" "info"
  if [ ! -d "$WORKING_DIR" ]; then
    echo_status "Error: Working directory '$WORKING_DIR' not found." "error"
    exit 1
  fi
  cd "$WORKING_DIR"
fi

# Check if Dockerfile exists in the working directory
if [ ! -f "Dockerfile" ]; then
  echo_status "Error: Dockerfile not found in the working directory." "error"
  echo_status "This script must be run with a directory containing a Dockerfile." "error"
  exit 1
fi

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

# Extract ENV variables from Dockerfile
echo_status "Extracting ENV variables from Dockerfile..." "info"
# Extract traditional ENV variables
TRADITIONAL_ENV_VARS=($(grep -i "^ENV" Dockerfile | awk '{print $2}' | cut -d= -f1))
# Extract new style ENV variables from comment lines, including those marked with !
COMMENT_ENV_VARS=()
while read -r line; do
  # Extract the variable name (4th field)
  var=$(echo "$line" | awk '{print $4}')
  COMMENT_ENV_VARS+=("$var")
done < <(grep -i "^# -- ENV" Dockerfile)

# Combine both arrays, removing duplicates and identify required variables
ENV_VARS=()
REQUIRED_VARS=()
for var in "${TRADITIONAL_ENV_VARS[@]}" "${COMMENT_ENV_VARS[@]}"; do
  # Check if variable is marked as required (ends with !)
  if [[ "$var" == *"!" ]]; then
    # Remove the ! from the variable name
    clean_var="${var%!}"
    # Add to required variables
    REQUIRED_VARS+=("$clean_var")
    # Add clean name to ENV_VARS if not already there
    if [[ ! " ${ENV_VARS[*]} " =~ " ${clean_var} " ]]; then
      ENV_VARS+=("$clean_var")
    fi
  else
    # Only add if not already in the array
    if [[ ! " ${ENV_VARS[*]} " =~ " ${var} " ]]; then
      ENV_VARS+=("$var")
    fi
  fi
done

if [ ${#ENV_VARS[@]} -eq 0 ]; then
  echo_status "Warning: No ENV variables found in Dockerfile." "warning"
else
  echo_status "Found ${#ENV_VARS[@]} ENV variables in Dockerfile:" "info"
  for var in "${ENV_VARS[@]}"; do
    if [[ " ${REQUIRED_VARS[*]} " =~ " ${var} " ]]; then
      echo "  - $var (required)"
    else
      echo "  - $var"
    fi
  done
fi

# Initialize environment variables
ENV_VAR_CMD=""
RESOLVED_VARS=()

# Process each ENV variable using dot-env.sh
if [ ${#ENV_VARS[@]} -gt 0 ]; then
  echo_status "Resolving environment variables using dot-env.sh..." "info"
  
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
  
  # Call dot-env.sh with all ENV variables
  if [ "$VERBOSE" = true ]; then
    # Use verbose mode to show where variables are resolved from
    if [ -n "$CUSTOM_ENV_FILE" ] && [ "$FORCE_DOT_ENV" = true ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --verbose --dot-env "$CUSTOM_ENV_FILE" --force-dot-env "${ENV_VARS[@]}" 2>/dev/null)) || true
    elif [ -n "$CUSTOM_ENV_FILE" ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --verbose --dot-env "$CUSTOM_ENV_FILE" "${ENV_VARS[@]}" 2>/dev/null)) || true
    elif [ "$FORCE_DOT_ENV" = true ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --verbose --force-dot-env "${ENV_VARS[@]}" 2>/dev/null)) || true
    else
      RESOLVED=($("$DOT_ENV_SCRIPT" --verbose "${ENV_VARS[@]}" 2>/dev/null)) || true
    fi
  else
    # Standard mode without verbose output
    if [ -n "$CUSTOM_ENV_FILE" ] && [ "$FORCE_DOT_ENV" = true ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --dot-env "$CUSTOM_ENV_FILE" --force-dot-env "${ENV_VARS[@]}" 2>/dev/null)) || true
    elif [ -n "$CUSTOM_ENV_FILE" ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --dot-env "$CUSTOM_ENV_FILE" "${ENV_VARS[@]}" 2>/dev/null)) || true
    elif [ "$FORCE_DOT_ENV" = true ]; then
      RESOLVED=($("$DOT_ENV_SCRIPT" --force-dot-env "${ENV_VARS[@]}" 2>/dev/null)) || true
    else
      RESOLVED=($("$DOT_ENV_SCRIPT" "${ENV_VARS[@]}" 2>/dev/null)) || true
    fi
  fi
  
  # Check if any variables were resolved
  if [ ${#RESOLVED[@]} -eq 0 ]; then
    echo_status "Warning: Some environment variables could not be resolved." "warning"
    echo_status "Container will use default values from Dockerfile." "info"
  else
    # Process the resolved variables
    MISSING_REQUIRED_VARS=()
    for var in "${ENV_VARS[@]}"; do
      # Check if this variable is in the resolved list
      resolved=false
      for resolved_var in "${RESOLVED[@]}"; do
        var_name=$(echo "$resolved_var" | cut -d= -f1)
        var_value=$(echo "$resolved_var" | cut -d= -f2-)
        
        if [ "$var_name" = "$var" ]; then
          resolved=true
          if [ -n "$var_value" ]; then
            echo_status "  $var_name: Resolved successfully" "success"
            RESOLVED_VARS+=("$resolved_var")
          else
            echo_status "  $var_name: Not found in environment or .env files" "warning"
            # Check if this is a required variable
            if [[ " ${REQUIRED_VARS[*]} " =~ " ${var} " ]]; then
              MISSING_REQUIRED_VARS+=("$var")
            fi
          fi
          break
        fi
      done
      
      # If variable wasn't in resolved list at all
      if [ "$resolved" = false ]; then
        echo_status "  $var: Not found in environment or .env files" "warning"
        # Check if this is a required variable
        if [[ " ${REQUIRED_VARS[*]} " =~ " ${var} " ]]; then
          MISSING_REQUIRED_VARS+=("$var")
        fi
      fi
    done
    
    # Check if any required variables are missing
    if [ ${#MISSING_REQUIRED_VARS[@]} -gt 0 ]; then
      echo_status "Error: The following required environment variables are not resolved:" "error"
      for var in "${MISSING_REQUIRED_VARS[@]}"; do
        echo_status "  - $var" "error"
      done
      echo_status "Container cannot be started without these variables." "error"
      exit 1
    fi
  fi
  
  # Build the -e part of the command
  if [ ${#RESOLVED_VARS[@]} -gt 0 ]; then
    for var in "${RESOLVED_VARS[@]}"; do
      ENV_VAR_CMD="$ENV_VAR_CMD -e $var"
    done
  fi
fi

# Extract exposed ports from Dockerfile
echo_status "Extracting exposed ports from Dockerfile..." "info"
EXPOSED_PORTS=($(grep -i "^EXPOSE" Dockerfile | awk '{for(i=2;i<=NF;i++) print $i}'))

if [ ${#EXPOSED_PORTS[@]} -eq 0 ]; then
  echo_status "Warning: No EXPOSE directives found in Dockerfile. Container may not expose any ports." "warning"
else
  echo_status "Found ${#EXPOSED_PORTS[@]} exposed ports: ${EXPOSED_PORTS[*]}" "info"
fi

# Build port mappings
PORT_MAPPINGS=""
for PORT in "${EXPOSED_PORTS[@]}"; do
  PORT_MAPPINGS="$PORT_MAPPINGS -p $PORT:$PORT"
done

# Construct docker run command with any additional arguments
DOCKER_ARGS_STR=""
if [ ${#DOCKER_ARGS[@]} -gt 0 ]; then
  for arg in "${DOCKER_ARGS[@]}"; do
    DOCKER_ARGS_STR="$DOCKER_ARGS_STR $arg"
  done
  echo_status "Additional docker run arguments: $DOCKER_ARGS_STR" "info"
fi

# Build the final docker run command
RUN_CMD="docker run -d $PORT_MAPPINGS $ENV_VAR_CMD --name $CONTAINER_NAME $DOCKER_ARGS_STR $CONTAINER_NAME"

# Display the command
echo_status "Docker run command:" "info"
echo_status "$RUN_CMD" "command"

# Execute the command if not in no-exec mode
if [ "$NO_EXEC" = true ]; then
  echo_status "--no-exec option specified. Command not executed." "info"
else
  echo_status "Running container..." "info"
  eval $RUN_CMD || { 
    echo_status "Error: Failed to run container!" "error"
    exit 1
  }
  echo_status "Container started successfully." "success"
fi
