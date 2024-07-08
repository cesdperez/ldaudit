# Launch Darkly audit CLI

Python CLI to audit LaunchDarkly feature flags. It fetches all flags from a specified project and identifies inactive flags that haven't been modified in production in a specified number of months.

Gives a message to be manually copy pasted into Slack. If it proves useful, can be automated.

## Setup

1.
```
pip install -r requirements.txt
```

2. Put a Launch Darkly API key with _read_ permissions in `.env`

## Usage

```
python ld-audit.py --help
```

Get friendly message to put on slack with all inactive flags:
```
python ld-audit.py list_inactive
```

Copy that message straight to your clipboard:
```
python ld-audit.py list_inactive | pbcopy
```
