#!/bin/bash

# Description:
#   This script extracts information from a Dockerfile.
#
# Usage:
#   dockerfile-info.sh <action> <dockerfile>
#
# Arguments:
#   <action>      Action to perform (image-name)
#   <dockerfile>  Path to the Dockerfile
#
# Action: image-name
#   Extracts the image name from the Dockerfile labels:
#   - org.opencontainers.image.title
#   - org.opencontainers.image.version (optional)
#   If labels are not present, exits with 1.
#   Otherwise, outputs the constructed image name to stdout.

set -e

ACTION="$1"
DOCKERFILE="$2"

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
  echo "Error: Dockerfile not found: $DOCKERFILE" >&2
  exit 1
fi

case "$ACTION" in
  image-name)
    IMAGE_NAME=$(grep -i "^LABEL org.opencontainers.image.title=" "$DOCKERFILE" | cut -d= -f2- | tr -d '"')
    IMAGE_VERSION=$(grep -i "^LABEL org.opencontainers.image.version=" "$DOCKERFILE" | cut -d= -f2- | tr -d '"')

    if [ -z "$IMAGE_NAME" ]; then
      echo "Error: Image title label not found in Dockerfile" >&2
      exit 1
    fi

    if [ -n "$IMAGE_VERSION" ]; then
      echo "$IMAGE_NAME:$IMAGE_VERSION"
    else
      echo "$IMAGE_NAME"
    fi
    ;;
  *)
    echo "Error: Invalid action: $ACTION" >&2
    exit 1
    ;;
esac
