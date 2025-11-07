# template.py
slack_message = """
*:among-use-party: Feature flags cleanup time*

> All these (temporary) feature flags haven't been modified in ANY environment (production, staging, dev, etc.) in the last {modified_before_months} months. That smells like an inactive flag!

# Total inactive flags: {total_inactive_flags}

*Inactive flags that are toggled `off` in production:*

> :work: Suggested actions:
> a. Enable the flag in production, or
> b. Archive the flag and remove all code evaluating this flag, or
> c. Only if it truly makes sense, make this a _permanenet_ flag instead of a _temporal_ one

{inactive_flags_off}

*Inactive flags that are toggled `on` in production:*

> :work: Suggested actions:
> a. Archive the flag and remove all code evaluating this flag, or
> b. Only if it truly makes sense, make this a _permanenet_ flag instead of a _temporal_ one

{inactive_flags_on}
"""
