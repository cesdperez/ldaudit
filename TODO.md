# TODO - Future Enhancements

## Deferred Improvements

### Better Maintainer Filtering
- Support email-based filtering: `--maintainer=john@example.com`
- Support maintainer ID: `--maintainer-id=user-123`
- Case-insensitive matching for names

### Enhanced Search Capabilities
- Support regex patterns: `--search-pattern='ld\.variation\(["\']([^"\']+)'`

### Verbosity Options
- `-v/--verbose` - Show API calls, cache hits, detailed progress
- `-q/--quiet` - Minimal output, results only

### Custom Exclude Directories
Allow users to specify additional directories to exclude from scanning:
```bash
ldaudit scan --exclude-dir=dir1,dir2
```

### Publishing
- Publish to PyPI for easy `uv tool install ld-audit` installation
- Consider semantic versioning automation
