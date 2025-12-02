import json
import os
import platform
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# --- Configuration Constants ---
MCP_SERVERS = {
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env_vars": ["GITHUB_PERSONAL_ACCESS_TOKEN"]
    },
    "azure-devops": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-azure-devops"],
        "env_vars": ["AZURE_DEVOPS_TOKEN", "AZURE_DEVOPS_ORG_URL"]
    }
}

class BurndownSetup:
    def __init__(self):
        self.os_type = platform.system()
        self.is_devcontainer = self._check_devcontainer()
        self.config_data = {"mcpServers": {}}
        
        # ANCHOR: Determine project root based on this script's location
        # This ensures .env is always saved to the repo root, even if run from a subdir
        self.project_root = Path(__file__).parent.resolve()
        self.env_file_path = self.project_root / ".env"
        
        self.collected_secrets = {}
        # Load existing .env if present
        self._load_env_file()

    def _check_devcontainer(self) -> bool:
        """Detects if we are running inside a DevContainer."""
        if os.environ.get("REMOTE_CONTAINERS") or os.environ.get("CODESPACES"):
            return True
        if os.path.exists("/.dockerenv"):
            return True
        return False

    def _verify_node_exists(self):
        """Ensures npx is available in the path."""
        if not shutil.which("npx"):
            print("❌ Error: 'npx' is not found in your PATH.")
            print("   Please install Node.js to use these MCP servers.")
            sys.exit(1)
        print("✅ Node.js runtime (npx) detected.")

    def _load_env_file(self):
        """Simple .env parser to avoid external dependencies like python-dotenv."""
        if not self.env_file_path.exists():
            return
        
        print(f"ℹ️  Loading environment variables from {self.env_file_path}")
        try:
            with open(self.env_file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    # Remove potential surrounding quotes
                    value = value.strip("'").strip('"')
                    # Set in os.environ so get_user_input can find it
                    if key not in os.environ:
                        os.environ[key] = value
        except Exception as e:
            print(f"⚠️  Warning: Could not read .env file: {e}")

    def get_user_input(self, prompt: str, env_var: str) -> str:
        """Gets input from Env Var first, then prompts user."""
        value = os.environ.get(env_var)
        if value:
            print(f"   Found {env_var} in environment.")
            # Store found value in collected secrets in case we want to save to .env later
            self.collected_secrets[env_var] = value
            return value
        
        try:
            val = input(f"   Enter {prompt}: ").strip()
            if not val:
                raise ValueError("Value cannot be empty")
            self.collected_secrets[env_var] = val
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

    def _get_vscode_settings_path(self) -> Path:
        """Returns the standard path for VS Code User Global Storage."""
        home = Path.home()
        if self.os_type == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage"
        elif self.os_type == "Darwin": # macOS
            return home / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
        else: # Linux / DevContainer
            # Standard fallback for Linux/DevContainers
            return home / ".config" / "Code" / "User" / "globalStorage"

    def locate_or_define_path(self) -> tuple[Path, bool]:
        """
        Returns: (Path to config file, boolean: True if file exists, False if it needs creation)
        """
        base_path = self._get_vscode_settings_path()
        
        # CORRECTED PATH: mcp_settings.json
        roo_path = base_path / "rooveterinaryinc.roo-cline" / "settings" / "mcp_settings.json"

        # 1. Check if it exists exactly where we expect
        if roo_path.exists():
            return roo_path, True

        # 2. Check if we are in a devcontainer (paths are messy here)
        if self.is_devcontainer:
            # In devcontainers, sometimes it's under /root/.vscode-server/
            vscode_server = Path.home() / ".vscode-server" / "data" / "User" / "globalStorage"
            server_path = vscode_server / "rooveterinaryinc.roo-cline" / "settings" / "mcp_settings.json"
            if server_path.exists():
                return server_path, True

        # 3. Return the standard path for creation
        return roo_path, False

    def save_configuration(self):
        print("\n--- Finalizing Configuration ---")
        
        target_path, exists = self.locate_or_define_path()
        
        if exists:
            print(f"✅ Found existing configuration at: {target_path}")
            # In automated environments (CI/DevContainer rebuilds), we might want to skip this prompt
            # But for safety, we default to merging.
            if not self.is_devcontainer:
                 choice = input("   Merge new settings into this file? (y/n): ").lower()
                 if choice != 'y':
                     print("   Skipping direct file update.")
                     return
            self._merge_and_save(target_path)

        else:
            print(f"⚠️  Configuration file not found.")
            print(f"   Proposed location: {target_path}")
            
            # Auto-create in devcontainer to ensure smooth setup
            if self.is_devcontainer:
                print("   DevContainer detected: Automatically creating configuration file.")
                self._create_fresh_file(target_path)
            else:
                choice = input("   Create new configuration file here? (y/n): ").lower()
                if choice == 'y':
                    self._create_fresh_file(target_path)
                else:
                    # Fallback: Save to local directory
                    local_file = self.project_root / "burndown_mcp_config.json"
                    print(f"\n📂 Saving to local file instead: {local_file.absolute()}")
                    with open(local_file, "w") as f:
                        json.dump(self.config_data, f, indent=2)
                    self._update_gitignore(local_file.name)
        
        self._prompt_save_dotenv()

    def _prompt_save_dotenv(self):
        """Offers to save collected secrets to .env for future automation."""
        # If we already have a .env file, we assume the user is happy or we already loaded from it
        if self.env_file_path.exists():
            return

        print("\n--- Persistence Setup ---")
        print("   To avoid entering these tokens again (e.g., when rebuilding the DevContainer),")
        print("   we can save them to a local .env file. This file will be git-ignored.")
        choice = input("   Create .env file with these credentials? (y/n): ").lower()
        
        if choice == 'y':
            try:
                with open(self.env_file_path, "w") as f:
                    for key, val in self.collected_secrets.items():
                        f.write(f"{key}={val}\n")
                print(f"✅ Created {self.env_file_path}")
                self._update_gitignore(self.env_file_path.name)
            except Exception as e:
                print(f"❌ Error creating .env file: {e}")

    def _update_gitignore(self, filename: str):
        """Adds the local config file to .gitignore to prevent accidental commits."""
        gitignore_path = self.project_root / ".gitignore"
        
        try:
            # Read existing content if file exists
            content = ""
            if gitignore_path.exists():
                with open(gitignore_path, "r") as f:
                    content = f.read()
            
            # Check if already ignored
            if filename in content:
                return

            # Append to .gitignore
            with open(gitignore_path, "a") as f:
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n# Local Secrets\n{filename}\n")
            
            action = "Updated" if gitignore_path.exists() else "Created"
            print(f"✅ {action} .gitignore to exclude '{filename}'")
            
        except Exception as e:
            print(f"⚠️  Could not update .gitignore: {e}")

    def _create_fresh_file(self, path: Path):
        """Creates directories and the file."""
        try:
            # Create the directory structure (e.g. .../settings/)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w") as f:
                json.dump(self.config_data, f, indent=2)
            print(f"✅ Created new configuration file at: {path}")
        except PermissionError:
            print("❌ Permission denied. Cannot create file at that location.")
            print("   Please check your permissions or run as administrator.")
        except Exception as e:
            print(f"❌ Error creating file: {e}")

    def _merge_and_save(self, path: Path):
        """Merges new config with existing to avoid deleting other tools."""
        try:
            with open(path, "r") as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_data = {"mcpServers": {}}

        if "mcpServers" not in existing_data:
            existing_data["mcpServers"] = {}

        existing_data["mcpServers"].update(self.config_data["mcpServers"])

        with open(path, "w") as f:
            json.dump(existing_data, f, indent=2)
        print("✅ Configuration updated successfully.")

    def run(self):
        print(f"🔥 Burndown Agent Setup Initialized")
        
        self._verify_node_exists()
        self.configure_github()
        self.configure_azure()
        self.save_configuration()
        
        print("\n🎉 Setup Complete. Restart RooCode/VS Code to apply.")

if __name__ == "__main__":
    setup = BurndownSetup()
    setup.run()