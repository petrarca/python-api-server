# Version Information Generation

This document explains how version information is generated in the API server starter project.

## Overview

The API server includes version information that shows:
1. The current version based on Git tags
2. When the package was built
3. Additional details like commit hash and branch name

This information is:
- Automatically generated during the build process
- Displayed in the web UI
- Included in the health check API response
- Generated without requiring manual intervention

## Implementation Details

### Manual Version Generation

We use a custom script (`scripts/git-version.sh`) to generate version information:

1. **Script Execution**:
   ```bash
   scripts/git-version.sh --tag-regex "server-v" --lang python
   ```

2. **Version Detection**:
   - The script looks for Git tags matching the pattern "server-v*"
   - It extracts the version number from the most recent matching tag
   - If no matching tags exist, it uses a fallback version based on commit information

3. **Output Generation**:
   - Creates a `_version.py` file with version information
   - Includes:
     - Version number (from tag)
     - Commit hash
     - Build timestamp
     - Branch name
     - Dirty state indicator (if working directory has uncommitted changes)

### Integration with CI/CD Pipeline

The version information is automatically generated during the CI/CD process. Here's an example from our GitHub Actions workflow (`.github/workflows/deploy-backend.yml`):

```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Fetch all history and tags for version generation

# ... other steps ...

- name: Generate version file
  run: |
     ./scripts/git-version.sh --tag-regex server-v --lang python > ./src/api_server/__version__.py
```

Key points:
- The `fetch-depth: 0` option is crucial as it fetches the complete Git history and tags
- The script is executed before the build/deployment steps
- The output is redirected to the appropriate Python module file
- The version information is then included in the deployed application

### Integration with Build Process

The version information is generated:
- During the build process
- When packaging the application
- Without requiring manual intervention

### Accessing Version Information

The version information can be accessed:
- In the web UI (displayed in the footer or about page)
- Via the health check API endpoint
- Programmatically by importing the version module

## Benefits

This approach offers several advantages:
1. **Simplicity**: No external dependencies required beyond Git
2. **Flexibility**: Can be customized for different components (server, frontend, etc.)
3. **Traceability**: Each build is linked to a specific Git commit and timestamp
4. **Automation**: Version generation is part of the build process
