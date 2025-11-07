# Launch Darkly audit CLI

Python CLI to audit LaunchDarkly feature flags. It fetches all flags from a specified project and identifies inactive flags that haven't been modified in production in a specified number of months.

## Features

- **List all flags**: View all active feature flags in LaunchDarkly
- **List inactive flags**: Identify flags that haven't been modified in production for X months (Slack-formatted output)
- **Scan codebase**: Find inactive flags that are still referenced in your code with exact file locations

## Setup

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Put a Launch Darkly API key with _read_ permissions in `.env`

## Usage

### List all flags
```
python ld_audit.py list_all --project=<project-name>
```

### List inactive flags (Slack message format)
```
python ld_audit.py list_inactive --project=<project-name>
```

Options:
- `--modified_before_months=3` (default: 3)
- `--maintainers=Name1,Name2` (optional filter)

Copy output straight to your clipboard:
```
python ld_audit.py list_inactive | pbcopy
```

### Scan codebase for inactive flags
```
python ld_audit.py scan_repo --project=<project-name> --directory=/path/to/repo
```

Options:
- `--directory=.` (default: current directory)
- `--extensions=cs,js,ts` (optional: filter file types to search)
- `--modified_before_months=3` (default: 3)
- `--maintainers=Name1,Name2` (optional filter)

Examples:
```bash
# Scan C# files in a .NET project
python ld_audit.py scan_repo --project=my-project --directory=/path/to/api --extensions=cs

# Scan JavaScript/TypeScript files
python ld_audit.py scan_repo --project=my-project --directory=./src --extensions=js,ts,jsx,tsx

# Scan all files in current directory
python ld_audit.py scan_repo --project=my-project --directory=.
```
