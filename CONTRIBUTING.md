# Contributing to Backlog Pilot

Thank you for your interest in contributing to Backlog Pilot! This document provides guidelines for contributing to the project.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/aselunar/Burndown-Agent.git
cd Burndown-Agent
```

### 2. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode along with development dependencies:
- pytest - for testing
- pytest-cov - for code coverage
- black - for code formatting
- ruff - for linting
- mypy - for type checking

### 3. Configure Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

## Development Workflow

### Code Style

We use:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting
- **mypy** for type checking

Format your code:
```bash
black src tests
```

Check linting:
```bash
ruff check src tests
```

Type check:
```bash
mypy src
```

### Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=backlog_pilot --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_config.py
```

### Testing Locally

Install in development mode:
```bash
pip install -e .
```

Test the CLI:
```bash
backlog-pilot --help
backlog-pilot init
backlog-pilot status
```

## Project Structure

```
Burndown-Agent/
├── src/
│   └── backlog_pilot/
│       ├── __init__.py          # Package initialization
│       ├── cli.py               # CLI commands
│       ├── config.py            # Configuration management
│       ├── azure_devops.py      # Azure DevOps integration
│       ├── github_client.py     # GitHub integration
│       └── py.typed             # Type hint marker
├── tests/                       # Test files
├── pyproject.toml              # Package configuration
├── README.md                   # Main documentation
├── USAGE.md                    # Usage guide
├── CONTRIBUTING.md             # This file
└── LICENSE                     # MIT License

```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Format code
black src tests

# Check linting
ruff check src tests

# Type check
mypy src

# Run tests
pytest
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "Description of your changes"
```

Use clear commit messages:
- `feat: Add new feature`
- `fix: Fix bug in X`
- `docs: Update documentation`
- `test: Add tests for Y`
- `refactor: Refactor Z`

### 5. Push and Create a Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Ensure all tests pass
- Update documentation if needed
- Add tests for new features

## Adding New Features

### New CLI Commands

1. Add the command in `src/backlog_pilot/cli.py`
2. Follow the existing pattern using Click
3. Add appropriate error handling
4. Update README.md with command documentation

Example:
```python
@main.command()
@click.option("--option", help="Description")
def new_command(option: str) -> None:
    """Command description."""
    # Implementation
```

### New Integrations

1. Create a new module in `src/backlog_pilot/`
2. Follow the client pattern (see `azure_devops.py` or `github_client.py`)
3. Add configuration options in `config.py`
4. Add CLI commands to use the integration

## Testing Guidelines

- Write tests for all new features
- Aim for high code coverage (>80%)
- Use descriptive test names
- Mock external API calls
- Test error conditions

Example test structure:
```python
def test_feature_name():
    """Test that feature works correctly."""
    # Arrange
    config = Config(...)
    
    # Act
    result = function_to_test()
    
    # Assert
    assert result == expected
```

## Code Review Process

1. All changes must be reviewed before merging
2. Address review comments promptly
3. Keep discussions constructive and professional
4. Once approved, the PR will be merged

## Release Process

Releases are handled by maintainers:

1. Update version in `pyproject.toml` and `__init__.py`
2. Update CHANGELOG.md
3. Create a git tag
4. Build and publish to PyPI

## Questions?

If you have questions:
- Open an issue on GitHub
- Check existing issues and discussions
- Review the documentation

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on what is best for the community
- Show empathy towards others

Thank you for contributing to Backlog Pilot!
