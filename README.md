# Launch Darkly audit CLI

Python CLI to audit LaunchDarkly feature flags. Modern CLI tool with rich terminal output that identifies inactive temporary flags and finds their references in your codebase.

## Features

- **List all flags**: View all feature flags with environment status in a rich formatted table
- **List inactive flags**: Identify flags that haven't been modified in any environment for X months with color-coded output
- **Scan codebase**: Find inactive flags that are still referenced in your code with exact file locations

## Installation

### For Local Development

1. Install [uv](https://docs.astral.sh/uv/) if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository and install in editable mode:
```bash
git clone https://github.com/yourusername/launchdarkly-audit.git
cd launchdarkly-audit
uv sync
```

3. The CLI is now available via `uv run`:
```bash
uv run ldaudit --help
```

Or install it as a tool globally:
```bash
uv tool install -e .
ldaudit --help
```

### For End Users (from PyPI)

Once published, users can install directly:
```bash
uv tool install ld-audit
ldaudit --help
```

Or with pipx:
```bash
pipx install ld-audit
ldaudit --help
```

### For CI/CD Pipelines

Use the pre-built Docker image for fast, reproducible builds:

```bash
docker pull ghcr.io/yourusername/ld-audit:latest
```

## Configuration

Create a `.env` file with your LaunchDarkly API key:
```
LD_API_KEY=your-api-key-here
```

Or export it as an environment variable:
```bash
export LD_API_KEY=your-api-key-here
```

## Usage

### Show help
```bash
ldaudit --help
```

### List all flags
```bash
ldaudit list --project=<project-name>
ldaudit list -p <project-name>
```

### List inactive flags
```bash
ldaudit inactive --project=<project-name>
ldaudit inactive -p <project-name> --months=6
```

Options:
- `--project`, `-p`: LaunchDarkly project name
- `--months`, `-m`: Inactivity threshold in months (default: 3)
- `--maintainer`: Filter by maintainer (comma-separated or repeatable)
- `--exclude`: Exclude specific flag keys (comma-separated or repeatable)

Examples:
```bash
# Find flags inactive for 6+ months
ldaudit inactive --project=my-project --months=6

# Filter by specific maintainers
ldaudit inactive -p my-project --maintainer=john,jane
ldaudit inactive -p my-project --maintainer=john --maintainer=jane

# Exclude known flags
ldaudit inactive -p my-project --exclude=flag-to-keep,another-flag
```

### Scan codebase for inactive flags
```bash
ldaudit scan --project=<project-name> --dir=/path/to/repo
ldaudit scan -p <project-name> -d ./src --ext=cs,js,ts
```

Options:
- `--project`, `-p`: LaunchDarkly project name
- `--dir`, `-d`: Directory to scan (default: current directory)
- `--ext`: File extensions to scan (comma-separated or repeatable)
- `--months`, `-m`: Inactivity threshold in months (default: 3)
- `--maintainer`: Filter by maintainer
- `--exclude`: Exclude specific flag keys

Examples:
```bash
# Scan C# files in a .NET project
ldaudit scan -p my-project -d /path/to/api --ext=cs

# Scan multiple file types
ldaudit scan -p my-project -d ./src --ext=js,ts,jsx,tsx
ldaudit scan -p my-project -d ./src --ext=js --ext=ts --ext=jsx

# Scan all files in current directory
ldaudit scan -p my-project -d .
```

### Cache Control

All commands support cache control flags:

```bash
# Bypass cache for this run (read from cache, don't write)
ldaudit list --no-cache

# Force refresh from API and update cache
ldaudit inactive --override-cache
```

## Output Features

- Rich tables with rounded borders
- Color-coded status indicators (🟢 ON / 🔴 OFF)
- Clickable URLs in supported terminals
- Multi-environment status display
- Actionable cleanup suggestions
- File locations formatted as `path:line_number` for easy IDE navigation

## Docker Usage

The Docker image is optimized for CI/CD pipelines with minimal size and fast startup.

### Basic Usage

```bash
docker run --rm \
  -e LD_API_KEY=$LD_API_KEY \
  ghcr.io/yourusername/ld-audit:latest \
  inactive --project=my-project
```

### GitHub Actions Example

```yaml
name: Audit LaunchDarkly Flags

on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly on Monday at 9 AM
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Audit inactive flags
        run: |
          docker run --rm \
            -e LD_API_KEY=${{ secrets.LD_API_KEY }} \
            ghcr.io/yourusername/ld-audit:latest \
            inactive --project=my-project --months=3
```

### GitLab CI Example

```yaml
audit-flags:
  stage: audit
  image: ghcr.io/yourusername/ld-audit:latest
  script:
    - ldaudit inactive --project=$CI_PROJECT_NAME --months=3
  variables:
    LD_API_KEY: $LD_API_KEY
  only:
    - schedules
```

### CircleCI Example

```yaml
version: 2.1

jobs:
  audit-flags:
    docker:
      - image: ghcr.io/yourusername/ld-audit:latest
    steps:
      - run:
          name: Audit feature flags
          command: ldaudit inactive --project=my-project --months=3
          environment:
            LD_API_KEY: ${LD_API_KEY}

workflows:
  weekly-audit:
    triggers:
      - schedule:
          cron: "0 9 * * 1"
          filters:
            branches:
              only: main
    jobs:
      - audit-flags
```

### Building the Docker Image Locally

```bash
# Build with uv
docker build -t ld-audit:local .

# Run locally built image
docker run --rm -e LD_API_KEY=$LD_API_KEY ld-audit:local inactive -p my-project
```

## Publishing

### To PyPI

```bash
# Build the package
uv build

# Publish to PyPI (requires PyPI account and token)
uv publish
```

### To GitHub Container Registry

```bash
# Build and tag
docker build -t ghcr.io/cesdperez/ld-audit:latest .

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u cesdperez --password-stdin

# Push
docker push ghcr.io/cesdperez/ld-audit:latest
```
