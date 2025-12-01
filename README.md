# Backlog Pilot

A Python CLI tool that integrates with Azure DevOps and GitHub to help Roo Code burn down your backlog in priority order by creating PRs automatically.

## Installation

Install from source:

```bash
pip install -e .
```

Or install from PyPI (once published):

```bash
pip install backlog-pilot
```

## Quick Start

### 1. Initialize Configuration

```bash
backlog-pilot init
```

This creates a configuration file at `~/.backlog-pilot/config.env`. Edit this file with your credentials:

```env
# Azure DevOps Configuration
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_PROJECT=your-project
AZURE_DEVOPS_PAT=your-personal-access-token

# GitHub Configuration
GITHUB_REPO=owner/repository
GITHUB_TOKEN=your-github-token
```

### 2. Check Status

```bash
backlog-pilot status
```

This verifies your configuration and tests connections to Azure DevOps and GitHub.

### 3. List Backlog Items

```bash
backlog-pilot list-backlog --limit 10
```

### 4. Create a PR for a Work Item

```bash
backlog-pilot create-pr --item-id 12345
```

## Commands

- `backlog-pilot init` - Initialize configuration
- `backlog-pilot status` - Show current status and test connections
- `backlog-pilot list-backlog` - List backlog items from Azure DevOps
- `backlog-pilot create-pr` - Create a GitHub PR for a work item
- `backlog-pilot --help` - Show all available commands

## Configuration

The tool can be configured via:
1. Environment variables
2. Configuration file at `~/.backlog-pilot/config.env`
3. Custom config file with `--config` option

### Required Environment Variables

- `AZURE_DEVOPS_ORG` - Your Azure DevOps organization name
- `AZURE_DEVOPS_PROJECT` - Your Azure DevOps project name
- `AZURE_DEVOPS_PAT` - Personal Access Token for Azure DevOps
- `GITHUB_REPO` - GitHub repository in format `owner/repo`
- `GITHUB_TOKEN` - GitHub Personal Access Token

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src tests
ruff check src tests
```

### Type Checking

```bash
mypy src
```

## Architecture

Backlog Pilot is designed to work as a background process that provides tools to Roo Code:

```
┌─────────────┐
│   Host OS   │
└─────────────┘
      ↓
┌─────────────┐
│   VS Code   │
└─────────────┘
      ↓
┌─────────────────────┐
│  Agent Platform     │
│  (Roo Code)         │
└─────────────────────┘
      ↓
┌─────────────────────┐
│  BACKLOG PILOT      │
│  (This Package)     │
│  Python Process     │
└─────────────────────┘
      ↓           ↓
┌──────────┐  ┌────────┐
│ Azure    │  │ GitHub │
│ DevOps   │  │        │
└──────────┘  └────────┘
```

## License

MIT License - see LICENSE file for details.
