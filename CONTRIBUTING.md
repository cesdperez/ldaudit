# Contributing to ldaudit

Thanks for your interest in contributing to ldaudit! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.12 or later
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for running tests with TestContainers)
- LaunchDarkly API key (for integration testing)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/cesdperez/launchdarkly-audit.git
   cd launchdarkly-audit
   ```

2. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Set up pre-commit hooks**
   ```bash
   uv run pre-commit install
   ```

5. **Set up environment variables**
   ```bash
   cp .env.sample .env
   # Edit .env and add your LD_API_KEY
   ```

## Running the Project

### Running locally with uv
```bash
uv run ldaudit --help
uv run ldaudit list --project=my-project
```

### Installing as a tool
```bash
uv tool install -e .
ldaudit --help
```

## Testing

### Run all tests
```bash
uv run pytest
```

### Run tests with verbose output
```bash
uv run pytest -xvs
```

### Run specific tests
```bash
uv run pytest tests/test_cli.py::TestGetPrimaryEnv
```

## Code Style

This project uses automated code formatting and linting:

- **Black** for consistent code formatting (120 character line length)
- **Ruff** for fast Python linting
- **Pre-commit hooks** to automatically check code before commits

### Running formatters manually

```bash
# Format all code with black
uv run black src tests

# Run ruff linter
uv run ruff check src tests

# Auto-fix ruff issues
uv run ruff check --fix src tests
```

### Code standards

- Use type hints for function parameters and return values
- Write docstrings for public functions
- Keep functions focused and concise
- Avoid comments where good variable/function names suffice

## Pull Request Process

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure CI checks pass

## Project Structure

```
launchdarkly-audit/
├── src/ld_audit/          # Main source code
│   ├── __init__.py        # Package initialization
│   ├── cli.py             # CLI commands and logic
│   └── cache.py           # Caching implementation
├── tests/                 # Test suite
│   ├── test_cli.py        # CLI function tests
│   └── test_search.py     # Search functionality tests
├── pyproject.toml         # Project metadata
└── README.md              # User documentation
```

## Adding New Features

When adding new features:
1. Start with tests
2. Implement the feature
3. Update documentation
4. Ensure backward compatibility where possible
5. Add configuration options rather than hardcoding values

## Reporting Issues

When reporting issues, please include:
- **Description** of the problem
- **Steps to reproduce** the issue
- **Expected behavior**
- **Actual behavior**
- **Environment details** (OS, Python version, uv version)
- **Error messages** or logs if applicable

## Feature Requests

Feature requests are welcome! Please:
- Check existing issues to avoid duplicates
- Clearly describe the use case
- Explain how it benefits other users
- Consider backward compatibility

## Questions?

If you have questions about contributing, feel free to open an issue with the "question" label.

## License

By contributing to LD Audit, you agree that your contributions will be licensed under the MIT License.
