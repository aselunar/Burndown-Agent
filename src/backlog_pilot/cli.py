"""
Command-line interface for Backlog Pilot.

This module provides the main CLI entry point for the backlog-pilot tool.
"""

import re
import sys
from typing import Optional

import click

from backlog_pilot import __version__
from backlog_pilot.config import Config
from backlog_pilot.azure_devops import AzureDevOpsClient
from backlog_pilot.github_client import GitHubClient


def sanitize_branch_name(name: str) -> str:
    """
    Sanitize a string to be a valid Git branch name.
    
    Args:
        name: The string to sanitize
    
    Returns:
        A valid Git branch name
    """
    # Convert to lowercase and replace spaces with hyphens
    name = name.lower().replace(' ', '-')
    
    # Remove invalid characters (keep alphanumeric, hyphens, underscores, slashes)
    name = re.sub(r'[^a-z0-9\-_/]', '', name)
    
    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name)
    
    # Remove leading/trailing hyphens
    name = name.strip('-')
    
    # Truncate to reasonable length
    if len(name) > 50:
        name = name[:50].rstrip('-')
    
    return name or 'feature'


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context) -> None:
    """
    Backlog Pilot - Burndown your backlog with Roo Code.
    
    A tool that connects to Azure DevOps and GitHub to help
    automate backlog management and PR creation.
    """
    ctx.ensure_object(dict)


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
def init(config: Optional[str]) -> None:
    """Initialize backlog-pilot configuration."""
    click.echo("Initializing backlog-pilot...")
    
    if config:
        click.echo(f"Using configuration from: {config}")
        cfg = Config.from_file(config)
    else:
        click.echo("Creating default configuration...")
        cfg = Config.create_default()
    
    click.echo(f"Configuration loaded successfully!")
    click.echo(f"Azure DevOps Organization: {cfg.azure_org or 'Not configured'}")
    click.echo(f"GitHub Repository: {cfg.github_repo or 'Not configured'}")


@main.command()
@click.option(
    "--limit",
    "-l",
    type=int,
    default=10,
    help="Maximum number of items to fetch",
)
def list_backlog(limit: int) -> None:
    """List backlog items from Azure DevOps."""
    click.echo(f"Fetching backlog items (limit: {limit})...")
    
    try:
        config = Config.load()
        azure_client = AzureDevOpsClient(config)
        items = azure_client.get_backlog_items(limit=limit)
        
        if not items:
            click.echo("No backlog items found.")
            return
        
        click.echo(f"\nFound {len(items)} backlog items:")
        for item in items:
            click.echo(f"  - {item['id']}: {item['title']} (Priority: {item.get('priority', 'N/A')})")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--item-id",
    "-i",
    type=str,
    required=True,
    help="Azure DevOps work item ID",
)
@click.option(
    "--branch",
    "-b",
    type=str,
    help="Target branch name (auto-generated if not provided)",
)
def create_pr(item_id: str, branch: Optional[str]) -> None:
    """Create a GitHub PR for a backlog item."""
    click.echo(f"Creating PR for work item: {item_id}...")
    
    try:
        config = Config.load()
        azure_client = AzureDevOpsClient(config)
        github_client = GitHubClient(config)
        
        # Get work item details
        work_item = azure_client.get_work_item(item_id)
        click.echo(f"Work Item: {work_item['title']}")
        
        # Generate branch name if not provided
        if not branch:
            sanitized_title = sanitize_branch_name(work_item['title'])
            branch = f"feature/{item_id}-{sanitized_title}"
            click.echo(f"Generated branch name: {branch}")
        
        # Create PR
        pr = github_client.create_pr(
            title=f"{work_item['title']} (#{item_id})",
            body=work_item.get("description", ""),
            head=branch,
        )
        
        click.echo(f"✓ PR created successfully: {pr['url']}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
def status() -> None:
    """Show current backlog-pilot status and configuration."""
    click.echo("Backlog Pilot Status\n" + "=" * 40)
    
    try:
        config = Config.load()
        click.echo(f"Version: {__version__}")
        click.echo(f"Configuration: {config.config_path}")
        click.echo(f"\nAzure DevOps:")
        click.echo(f"  Organization: {config.azure_org or 'Not configured'}")
        click.echo(f"  Project: {config.azure_project or 'Not configured'}")
        click.echo(f"\nGitHub:")
        click.echo(f"  Repository: {config.github_repo or 'Not configured'}")
        
        # Test connections
        click.echo("\nTesting connections...")
        
        try:
            azure_client = AzureDevOpsClient(config)
            azure_client.test_connection()
            click.echo("  ✓ Azure DevOps: Connected")
        except Exception as e:
            click.echo(f"  ✗ Azure DevOps: Failed ({e})")
        
        try:
            github_client = GitHubClient(config)
            github_client.test_connection()
            click.echo("  ✓ GitHub: Connected")
        except Exception as e:
            click.echo(f"  ✗ GitHub: Failed ({e})")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
