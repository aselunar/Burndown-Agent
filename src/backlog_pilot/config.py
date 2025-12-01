"""
Configuration management for Backlog Pilot.

Handles loading and managing configuration from environment variables
and configuration files.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv


class Config:
    """Configuration manager for backlog-pilot."""
    
    DEFAULT_CONFIG_PATH = Path.home() / ".backlog-pilot" / "config.env"
    
    def __init__(
        self,
        azure_org: Optional[str] = None,
        azure_project: Optional[str] = None,
        azure_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        github_token: Optional[str] = None,
        config_path: Optional[Path] = None,
    ):
        """Initialize configuration."""
        self.azure_org = azure_org
        self.azure_project = azure_project
        self.azure_token = azure_token
        self.github_repo = github_repo
        self.github_token = github_token
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from environment and config file.
        
        Priority order:
        1. Environment variables
        2. Config file (if specified)
        3. Default config file location
        """
        # Load from config file if it exists
        path = config_path or cls.DEFAULT_CONFIG_PATH
        if path.exists():
            load_dotenv(path)
        
        return cls(
            azure_org=os.getenv("AZURE_DEVOPS_ORG"),
            azure_project=os.getenv("AZURE_DEVOPS_PROJECT"),
            azure_token=os.getenv("AZURE_DEVOPS_PAT"),
            github_repo=os.getenv("GITHUB_REPO"),
            github_token=os.getenv("GITHUB_TOKEN"),
            config_path=path,
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from a specific file."""
        return cls.load(Path(config_path))
    
    @classmethod
    def create_default(cls) -> "Config":
        """Create a default configuration file."""
        config_path = cls.DEFAULT_CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create template config file
        template = """# Backlog Pilot Configuration
# Configure your Azure DevOps and GitHub credentials here

# Azure DevOps Configuration
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_PROJECT=your-project
AZURE_DEVOPS_PAT=your-personal-access-token

# GitHub Configuration
GITHUB_REPO=owner/repository
GITHUB_TOKEN=your-github-token
"""
        
        if not config_path.exists():
            config_path.write_text(template)
        
        return cls.load(config_path)
    
    def validate(self) -> bool:
        """Validate that all required configuration is present."""
        required_fields = [
            ("azure_org", "AZURE_DEVOPS_ORG"),
            ("azure_project", "AZURE_DEVOPS_PROJECT"),
            ("azure_token", "AZURE_DEVOPS_PAT"),
            ("github_repo", "GITHUB_REPO"),
            ("github_token", "GITHUB_TOKEN"),
        ]
        
        missing = []
        for field, env_var in required_fields:
            if not getattr(self, field):
                missing.append(env_var)
        
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Please set these in your environment or config file at {self.config_path}"
            )
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "azure_org": self.azure_org,
            "azure_project": self.azure_project,
            "github_repo": self.github_repo,
            "config_path": str(self.config_path),
        }
