# ldaudit

[![Build](https://github.com/cesdperez/launchdarkly-audit/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/cesdperez/launchdarkly-audit/actions/workflows/docker-publish.yml)
[![Version](https://img.shields.io/github/v/tag/cesdperez/launchdarkly-audit?label=version)](https://github.com/cesdperez/launchdarkly-audit/tags)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/cesdperez/launchdarkly-audit/pkgs/container/ld-audit)

CLI to audit LaunchDarkly feature flags. Identifies inactive temporary flags and finds their references in your codebase.

## Features

- **List flags**: View all feature flags with environment status
- **Find inactive flags**: Identify flags not modified in any environment for X months
- **Scan codebase**: Find inactive flag references with exact file locations
- **Rich output**: Color-coded tables, clickable URLs, actionable suggestions

## Quick Start

### Docker (Recommended)

```bash
docker run --rm -e LD_API_KEY=your-key ghcr.io/cesdperez/ld-audit:latest \
  inactive --project=my-project
```

### Local Installation

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/cesdperez/launchdarkly-audit.git
cd launchdarkly-audit
uv sync

# Run commands
uv run ldaudit --help
```

## Configuration

Required environment variable:
```bash
export LD_API_KEY=your-api-key-here
```

Or create a `.env` file:
```
LD_API_KEY=your-api-key-here
```

## Usage

The `--project` parameter defaults to `"default"` if not specified. Use `ldaudit <command> --help` to see all available options.

### List all flags
```bash
ldaudit list
ldaudit list --project=my-project
```

### Find inactive flags
```bash
ldaudit inactive
ldaudit inactive --project=my-project
ldaudit inactive -p my-project --months=6
ldaudit inactive -p my-project --maintainer=john,jane
```

### Scan codebase for flag references
```bash
ldaudit scan --dir=./src
ldaudit scan --project=my-project --dir=./src
ldaudit scan -p my-project -d ./src --ext=cs,js,ts
ldaudit scan -p my-project --months=6 --max-file-size=10
```

### Manage cache
```bash
ldaudit cache list
ldaudit cache clear
```

## Command Options

Common flags across all commands:
- `--project`, `-p`: LaunchDarkly project name (default: `"default"`)
- `--base-url`: LaunchDarkly base URL (default: `https://app.launchdarkly.com`)
- `--cache-ttl`: Cache TTL in seconds (default: 3600)
- `--no-cache`: Bypass cache for this run
- `--override-cache`: Force refresh from API

Additional flags for `inactive` and `scan`:
- `--months`, `-m`: Inactivity threshold (default: 3)
- `--maintainer`: Filter by maintainer name
- `--exclude`: Exclude specific flag keys

Additional flags for `scan`:
- `--dir`, `-d`: Directory to scan (default: current directory)
- `--ext`: File extensions to scan (comma-separated)
- `--max-file-size`: Max file size in MB to scan (default: 5)

Use `--help` on any command to see all available options.

## Docker Usage

### Basic Commands
```bash
# List flags
docker run --rm -e LD_API_KEY=$LD_API_KEY \
  ghcr.io/cesdperez/ld-audit:latest \
  list --project=my-project

# Find inactive flags (6+ months)
docker run --rm -e LD_API_KEY=$LD_API_KEY \
  ghcr.io/cesdperez/ld-audit:latest \
  inactive --project=my-project --months=6
```

## Advanced Configuration

### Custom LaunchDarkly Instance
For on-premises or custom LaunchDarkly installations:
```bash
ldaudit list --project=my-project \
  --base-url=https://launchdarkly.mycompany.com
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - see LICENSE file for details.
