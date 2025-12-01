import json
import os
import platform
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# --- Configuration Constants ---

# The specific MCP servers we want to configure
MCP_SERVERS = {
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env_vars": ["GITHUB_PERSONAL_ACCESS_TOKEN"]
    },
    "azure-devops": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-azure-devops"], # Assuming standard package naming convention
        "env_vars": ["AZURE_DEVOPS_TOKEN", "AZURE_DEVOPS_ORG_URL"]
    }
}

class BurndownSetup:
    def __init__(self):
        self.os_type = platform.system()
        self.is_devcontainer = self._check_devcontainer()
        self.config_data = {"mcpServers": {}}

    def _check_devcontainer(self) -> bool:
        """Detects if we are running inside a DevContainer."""
        # Common env vars set by VS Code DevContainers and Codespaces
        if os.environ.get("REMOTE_CONTAINERS"):
            return True
        if os.environ.get("CODESPACES"):
            return True
        # Check for generic container indicators
        if os.path.exists("/.dockerenv"):
            return True
        return False

    def _verify_node_exists(self):
        """Ensures npx is available in the path."""
        if not shutil.which("npx"):
            print("❌ Error: 'npx' is not found in your PATH.")
            print("   Please install Node.js (which includes npx) to use these MCP servers.")
            sys.exit(1)
        print("✅ Node.js runtime (npx) detected.")

    def get_user_input(self, prompt: str, env_var: str) -> str:
        """
        Gets input from Environment Variable first, then prompts user.
        This makes it automatable in CI/CD or DevContainers.
        """
        value = os.environ.get(env_var)
        if value:
            print(f"   Found {env_var} in environment.")
            return value
        
        # Interactive prompt if not in env
        try:
            val = input(f"   Enter {prompt}: ").strip()
            if not val:
                raise ValueError("Value cannot be empty")
            return val
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            sys.exit(0)

    def configure_github(self):
        print("\n--- Configuring GitHub MCP ---")
        token = self.get_user_input("GitHub Personal Access Token", "GITHUB_PERSONAL_ACCESS_TOKEN")
        
        self.config_data["mcpServers"]["github"] = {
            "command": MCP_SERVERS["github"]["command"],
            "args": MCP_SERVERS["github"]["args"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": token
            },
            "disabled": False,
            "autoApprove": []
        }

    def configure_azure(self):
        print("\n--- Configuring Azure DevOps MCP ---")
        url = self.get_user_input("Azure DevOps Org URL (e.g. https://dev.azure.com/myorg)", "AZURE_DEVOPS_ORG_URL")
        token = self.get_user_input("Azure DevOps PAT", "AZURE_DEVOPS_TOKEN")

        self.config_data["mcpServers"]["azure-devops"] = {
            "command": MCP_SERVERS["azure-devops"]["command"],
            "args": MCP_SERVERS["azure-devops"]["args"],
            "env": {
                "AZURE_DEVOPS_ORG_URL": url,
                "AZURE_DEVOPS_TOKEN": token
            },
            "disabled": False,
            "autoApprove": []
        }

    def attempt_auto_locate_roocode(self) -> Optional[Path]:
        """
        Attempts to find the RooCode/Cline configuration file based on OS.
        """
        home = Path.home()
        possible_paths = []

        if self.os_type == "Windows":
            base =  Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage"
            possible_paths.append(base / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json")
        elif self.os_type == "Darwin": # macOS
            base = home / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
            possible_paths.append(base / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json")
        else: # Linux / DevContainer
            # Standard local Linux
            base = home / ".config" / "Code" / "User" / "globalStorage"
            possible_paths.append(base / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json")
            
            # VS Code Server (DevContainers)
            # Paths here are tricky and vary by version, but often mirror local structure relative to home
            base_server = home / ".vscode-server" / "data" / "User" / "globalStorage"
            possible_paths.append(base_server / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json")

        for p in possible_paths:
            if p.exists():
                return p
        
        return None

    def save_configuration(self):
        print("\n--- Finalizing Configuration ---")
        
        target_path = self.attempt_auto_locate_roocode()
        
        # Determine output mode
        if target_path:
            print(f"✅ Detected RooCode config at: {target_path}")
            choice = input("   Update this file directly? (y/n): ").lower()
            if choice == 'y':
                self._merge_and_save(target_path)
                return
        
        # Fallback: Save to local directory
        local_file = Path("burndown_mcp_config.json")
        print(f"⚠️  Could not automatically inject config. Saving to local file: {local_file.absolute()}")
        with open(local_file, "w") as f:
            json.dump(self.config_data, f, indent=2)
        print("   -> Copy the content of this file into your RooCode/Cline MCP settings.")

    def _merge_and_save(self, path: Path):
        """Merges new config with existing to avoid deleting other tools."""
        try:
            with open(path, "r") as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_data = {"mcpServers": {}}

        # Ensure mcpServers key exists
        if "mcpServers" not in existing_data:
            existing_data["mcpServers"] = {}

        # Update only our specific keys
        existing_data["mcpServers"].update(self.config_data["mcpServers"])

        with open(path, "w") as f:
            json.dump(existing_data, f, indent=2)
        print("✅ Configuration updated successfully.")

    def run(self):
        print(f"🔥 Burndown Agent Setup Initialized")
        print(f"   Environment: {'DevContainer' if self.is_devcontainer else 'Local System'}")
        
        self._verify_node_exists()
        
        self.configure_github()
        self.configure_azure()
        
        self.save_configuration()
        print("\n🎉 Setup Complete. Please restart RooCode/VS Code to load changes.")

if __name__ == "__main__":
    setup = BurndownSetup()
    setup.run()
    