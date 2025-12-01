# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-01

### Added
- Initial release of backlog-pilot
- CLI tool with commands: init, status, list-backlog, create-pr
- Azure DevOps integration for work item management
- GitHub integration for PR creation
- Configuration management via environment variables and config files
- Comprehensive documentation (README, USAGE guide, CONTRIBUTING guide)
- Type hints and py.typed marker for type checking support
- Example configuration file (config.env.example)

### Features
- **init**: Initialize configuration with default template
- **status**: Check configuration and test connections to Azure DevOps and GitHub
- **list-backlog**: Fetch and display work items from Azure DevOps in priority order
- **create-pr**: Create GitHub pull requests for specific work items

### Technical Details
- Python 3.8+ support
- Modern src-layout package structure
- Proper pyproject.toml configuration
- CLI built with Click framework
- Integration with azure-devops SDK and PyGithub
- Configuration via python-dotenv

[0.1.0]: https://github.com/aselunar/Burndown-Agent/releases/tag/v0.1.0
