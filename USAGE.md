# Backlog Pilot Usage Guide

This guide provides examples of how to use the backlog-pilot CLI tool.

## Initial Setup

### 1. Install the Package

```bash
pip install backlog-pilot
```

Or install from source:

```bash
git clone https://github.com/aselunar/Burndown-Agent.git
cd Burndown-Agent
pip install -e .
```

### 2. Initialize Configuration

```bash
backlog-pilot init
```

This creates a configuration file at `~/.backlog-pilot/config.env`.

### 3. Configure Credentials

Edit the configuration file with your credentials:

```bash
# On Linux/Mac
nano ~/.backlog-pilot/config.env

# On Windows
notepad %USERPROFILE%\.backlog-pilot\config.env
```

Update the following values:

```env
AZURE_DEVOPS_ORG=your-org-name
AZURE_DEVOPS_PROJECT=your-project-name
AZURE_DEVOPS_PAT=your-pat-token
GITHUB_REPO=owner/repository
GITHUB_TOKEN=ghp_your_token_here
```

#### Getting Azure DevOps Personal Access Token

1. Go to https://dev.azure.com/[your-org]/_usersSettings/tokens
2. Click "New Token"
3. Give it a name (e.g., "Backlog Pilot")
4. Select scopes: Work Items (Read & Write)
5. Click "Create"
6. Copy the token and save it to your config

#### Getting GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "Backlog Pilot")
4. Select scopes: `repo` (Full control of private repositories)
5. Click "Generate token"
6. Copy the token and save it to your config

## Basic Usage

### Check Status

Verify your configuration and test connections:

```bash
backlog-pilot status
```

Example output:
```
Backlog Pilot Status
========================================
Version: 0.1.0
Configuration: /home/user/.backlog-pilot/config.env

Azure DevOps:
  Organization: my-org
  Project: my-project

GitHub:
  Repository: owner/repo

Testing connections...
  ✓ Azure DevOps: Connected
  ✓ GitHub: Connected
```

### List Backlog Items

Get the top 10 items from your backlog:

```bash
backlog-pilot list-backlog
```

Customize the number of items:

```bash
backlog-pilot list-backlog --limit 20
```

Example output:
```
Fetching backlog items (limit: 10)...

Found 10 backlog items:
  - 12345: Implement user authentication (Priority: 1)
  - 12346: Add error handling (Priority: 2)
  - 12347: Update documentation (Priority: 3)
  ...
```

### Create a Pull Request

Create a PR for a specific work item:

```bash
backlog-pilot create-pr --item-id 12345
```

With a custom branch name:

```bash
backlog-pilot create-pr --item-id 12345 --branch feature/user-auth
```

Example output:
```
Creating PR for work item: 12345...
Work Item: Implement user authentication
Generated branch name: feature/12345-implement-user-authentication
✓ PR created successfully: https://github.com/owner/repo/pull/42
```

## Environment Variables

You can also set configuration via environment variables instead of the config file:

```bash
export AZURE_DEVOPS_ORG=my-org
export AZURE_DEVOPS_PROJECT=my-project
export AZURE_DEVOPS_PAT=your-token
export GITHUB_REPO=owner/repo
export GITHUB_TOKEN=ghp_your_token

backlog-pilot status
```

## Using with Roo Code

Backlog Pilot is designed to work as a tool provider for Roo Code. Once installed:

1. Roo Code can call `backlog-pilot` commands to interact with your backlog
2. Work items are fetched in priority order
3. PRs are automatically created for work items
4. The agent can iterate through the backlog systematically

### Example Workflow

1. Roo Code runs: `backlog-pilot list-backlog --limit 1`
2. Gets the highest priority item
3. Works on implementing the feature
4. Creates a branch with the changes
5. Runs: `backlog-pilot create-pr --item-id [ID] --branch [branch-name]`
6. Repeats for the next item

## Troubleshooting

### Connection Issues

If you get connection errors:

1. Verify your tokens are correct and not expired
2. Check that your organization/project names are correct
3. Ensure you have the necessary permissions
4. Try running `backlog-pilot status` to see detailed error messages

### Token Permissions

Azure DevOps PAT needs:
- Work Items: Read & Write

GitHub Token needs:
- `repo`: Full control of repositories

### Configuration File Not Found

If the config file isn't found, run:

```bash
backlog-pilot init
```

This will create the default configuration file.

## Advanced Usage

### Custom Configuration File

Use a custom configuration file location:

```bash
backlog-pilot init --config /path/to/custom/config.env
```

### Integration with CI/CD

You can use backlog-pilot in automated workflows:

```yaml
# GitHub Actions example
- name: Update work item
  env:
    AZURE_DEVOPS_ORG: ${{ secrets.AZURE_ORG }}
    AZURE_DEVOPS_PROJECT: ${{ secrets.AZURE_PROJECT }}
    AZURE_DEVOPS_PAT: ${{ secrets.AZURE_PAT }}
  run: |
    pip install backlog-pilot
    backlog-pilot status
```

## Getting Help

For more information on any command:

```bash
backlog-pilot --help
backlog-pilot [command] --help
```

For issues or feature requests:
- Visit: https://github.com/aselunar/Burndown-Agent/issues
