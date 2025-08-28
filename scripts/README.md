# Scripts Directory

This directory contains utility scripts for Docker container management and utility scripts.

## Common Features

### Image and Container Name Resolution

All Docker scripts can automatically resolve image names from the Dockerfile if not explicitly provided:
- If no name is provided as an argument, the scripts look for a Dockerfile in the current directory
- The `dockerfile-info.sh` script is used to extract the image name from the Dockerfile labels
- Image name: The name of the Docker image (e.g., `api-server`)
- Container name: The name of a running instance of an image (e.g., `api-server-instance`)
- This allows you to run the scripts without arguments when in a directory with a Dockerfile

### Environment Variable Resolution

All Docker and deployment scripts support resolving environment variables from various sources:
- Environment variables from the current shell
- Variables defined in `.env` files
- Custom environment files specified with the `--dot-env` option
- The `--dot-env` option allows you to specify a custom environment file (e.g., `--dot-env .env.production`)
- The `--force-dot-env` option makes variables in .env files override existing environment variables
- This provides flexibility for different deployment environments without modifying the scripts

### Additional Arguments with `--` Separator

All Docker scripts support passing additional arguments to their respective Docker commands using the `--` separator:
- `docker-rebuild.sh`: Pass additional arguments to `docker build` (e.g., `-- --no-cache --pull`)
- `docker-run.sh`: Pass additional arguments to `docker run` (e.g., `-- --restart always -v /tmp:/data`)
- `docker-sh.sh`: Pass additional arguments to `docker exec` (e.g., `-- -u root -w /app`)

This provides greater flexibility without modifying the scripts themselves.

## Docker Scripts

### docker-rebuild.sh

A script for rebuilding Docker images locally with build arguments. It automatically:
- Checks for a Dockerfile in the current directory
- Stops and removes existing containers with the provided name
- Extracts build arguments from the Dockerfile
- Resolves environment variables from .env files using dot-env.sh
- Builds the image with proper configuration

```bash
docker-rebuild.sh [<image-name>] [--no-exec] [--verbose] [--dot-env <env-file>] [--force-dot-env] [--help] [-- <docker-build-args>]
```

### docker-run.sh

A script for running Docker containers based on a Dockerfile. It automatically:
- Extracts environment variables and exposed ports from the Dockerfile
- Resolves environment variables from .env files using dot-env.sh
- Maps exposed ports automatically
- Runs the container with the appropriate configuration

```bash
docker-run.sh [<container-name>] [working-dir] [--no-exec] [--verbose] [--dot-env <env-file>] [--force-dot-env] [--help] [-- <docker-run-args>]
```

### docker-sh.sh

A script for connecting to a running Docker container with a shell or running a specified command. It:
- Finds containers by name pattern
- Handles multiple matching containers with interactive selection
- Automatically tries sh or bash for shell access
- Can run custom commands in the container

```bash
docker-sh.sh [<container-name-pattern>] [command] [--no-exec] [--help] [-- <docker-exec-args>]
```

### docker-stop.sh

A script for stopping all running Docker containers that match a given name pattern. It:
- Finds and stops all containers matching a name pattern
- Shows a summary of stopped containers
- Can optionally remove containers after stopping them

```bash
docker-stop.sh [<container-name>] [--rm] [--no-exec] [--help]
```

## Support Scripts

### dot-env.sh

A utility script used by the Docker and deployment scripts to resolve environment variables from various sources:
- First checks if variables are defined in the current shell environment
- If not found in the environment, checks for variables in .env files
- By default, looks for .env files in both the current directory and project root
- When using the `--dot-env` option, only uses the specified environment file
- Supports the `--verbose` option to show where variables are resolved from
- Supports the `--force-dot-env` option to make .env files override existing environment variables

The script follows this order when resolving variables:
1. Current shell environment (unless `--force-dot-env` is used)
2. Custom environment file (if `--dot-env` option is used)
3. Project root .env file and local .env file (if no `--dot-env` option is used)

When `--force-dot-env` is used, the order changes to:
1. Custom environment file (if `--dot-env` option is used)
2. Project root .env file and local .env file (if no `--dot-env` option is used)
3. Current shell environment (only used if variables are not found in .env files)

```bash
dot-env.sh [--verbose] [--dot-env <env-file>] [--force-dot-env] [variable1] [variable2] ...
```

### dockerfile-info.sh

A utility script used by the Docker scripts to extract information from Dockerfiles:
- Extracts image names from Dockerfile labels (org.opencontainers.image.title)
- Optionally includes version information (org.opencontainers.image.version)
- Used for automatic image and container name resolution when no name is provided
