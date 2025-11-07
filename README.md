# Launch Darkly audit CLI

Python CLI to audit LaunchDarkly feature flags. Modern CLI tool with rich terminal output that identifies inactive temporary flags and finds their references in your codebase.

## Features

- **List all flags**: View all feature flags with environment status in a rich formatted table
- **List inactive flags**: Identify flags that haven't been modified in any environment for X months with color-coded output
- **Scan codebase**: Find inactive flags that are still referenced in your code with exact file locations

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your LaunchDarkly API key:
```
LD_API_KEY=your-api-key-here
```

## Usage

### Show help
```bash
python ld_audit.py --help
```

### List all flags
```bash
python ld_audit.py list --project=<project-name>
python ld_audit.py list -p <project-name>
```

### List inactive flags
```bash
python ld_audit.py inactive --project=<project-name>
python ld_audit.py inactive -p <project-name> --months=6
```

Options:
- `--project`, `-p`: LaunchDarkly project name
- `--months`, `-m`: Inactivity threshold in months (default: 3)
- `--maintainer`: Filter by maintainer (comma-separated or repeatable)

Examples:
```bash
# Find flags inactive for 6+ months
python ld_audit.py inactive --project=my-project --months=6

# Filter by specific maintainers
python ld_audit.py inactive -p my-project --maintainer=john,jane
python ld_audit.py inactive -p my-project --maintainer=john --maintainer=jane
```

### Scan codebase for inactive flags
```bash
python ld_audit.py scan --project=<project-name> --dir=/path/to/repo
python ld_audit.py scan -p <project-name> -d ./src --ext=cs,js,ts
```

Options:
- `--project`, `-p`: LaunchDarkly project name
- `--dir`, `-d`: Directory to scan (default: current directory)
- `--ext`: File extensions to scan (comma-separated or repeatable)
- `--months`, `-m`: Inactivity threshold in months (default: 3)
- `--maintainer`: Filter by maintainer

Examples:
```bash
# Scan C# files in a .NET project
python ld_audit.py scan -p my-project -d /path/to/api --ext=cs

# Scan multiple file types
python ld_audit.py scan -p my-project -d ./src --ext=js,ts,jsx,tsx
python ld_audit.py scan -p my-project -d ./src --ext=js --ext=ts --ext=jsx

# Scan all files in current directory
python ld_audit.py scan -p my-project -d .
```

## Output Features

- Rich tables with rounded borders
- Color-coded status indicators (🟢 ON / 🔴 OFF)
- Clickable URLs in supported terminals
- Multi-environment status display
- Actionable cleanup suggestions
- File locations formatted as `path:line_number` for easy IDE navigation
