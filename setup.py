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
        
        # ANCHOR: Use Current Working Directory (CWD) instead of Script Location
        # This allows us to run the script from /tmp but save .env to the project root
        self.project_root = Path.cwd()
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
                    value = value.strip("'").strip('"')
                    if key not in os.environ:
                        os.environ[key] = value
        except Exception as e:
            print(f"⚠️  Warning: Could not read .env file: {e}")

    def get_user_input(self, prompt: str, env_var: str) -> str:
        """Gets input from Env Var first, then prompts user."""
        value = os.environ.get(env_var)
        if value:
            print(f"   Found {env_var} in environment.")
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
        roo_path = base_path / "rooveterinaryinc.roo-cline" / "settings" / "mcp_settings.json"

        # 1. DevContainer Priority Check
        if self.is_devcontainer:
            # VS Code Server specific path
            vscode_server = Path.home() / ".vscode-server" / "data" / "User" / "globalStorage"
            server_path = vscode_server / "rooveterinaryinc.roo-cline" / "settings" / "mcp_settings.json"
            
            # If exists, return it. If not, return it as the target for creation.
            if server_path.exists():
                return server_path, True
            return server_path, False

        # 2. Local Desktop Check
        if roo_path.exists():
            return roo_path, True

        return roo_path, False

    def save_configuration(self):
        print("\n--- Finalizing Configuration ---")
        
        target_path, exists = self.locate_or_define_path()
        
        if exists:
            print(f"✅ Found existing configuration at: {target_path}")
            if not self.is_devcontainer:
                 choice = input("   Merge new settings into this file? (y/n): ").lower()
                 if choice != 'y':
                     print("   Skipping direct file update.")
                     return
            self._merge_and_save(target_path)

        else:
            print(f"⚠️  Configuration file not found.")
            print(f"   Proposed location: {target_path}")
            
            if self.is_devcontainer:
                print("   DevContainer detected: Automatically creating configuration file.")
                self._create_fresh_file(target_path)
            else:
                choice = input("   Create new configuration file here? (y/n): ").lower()
                if choice == 'y':
                    self._create_fresh_file(target_path)
                else:
                    local_file = self.project_root / "burndown_mcp_config.json"
                    print(f"\n📂 Saving to local file instead: {local_file.absolute()}")
                    with open(local_file, "w") as f:
                        json.dump(self.config_data, f, indent=2)
                    self._update_gitignore(local_file.name)
        
        self._save_secrets_to_env()

    def _save_secrets_to_env(self):
        """Saves collected secrets to .env, APPENDING if file exists."""
        
        # 1. Read existing content to avoid duplicates
        existing_content = ""
        if self.env_file_path.exists():
            with open(self.env_file_path, "r") as f:
                existing_content = f.read()

        new_lines = []
        for key, val in self.collected_secrets.items():
            if key not in existing_content:
                new_lines.append(f"{key}={val}")
        
        if not new_lines:
            return # Nothing to add

        print("\n--- Persistence Setup ---")
        print(f"   Updating {self.env_file_path.name} to include new secrets...")
        
        # 2. Append or Create
        mode = "a" if self.env_file_path.exists() else "w"
        try:
            with open(self.env_file_path, mode) as f:
                # Ensure we start on a new line if appending
                if mode == "a" and existing_content and not existing_content.endswith("\n"):
                    f.write("\n")
                for line in new_lines:
                    f.write(f"{line}\n")
            
            print(f"✅ Saved secrets to {self.env_file_path}")
            self._update_gitignore(self.env_file_path.name)
        except Exception as e:
            print(f"❌ Error saving .env: {e}")

    def _update_gitignore(self, filename: str):
        """Adds the local config file to .gitignore to prevent accidental commits."""
        gitignore_path = self.project_root / ".gitignore"
        
        try:
            content = ""
            if gitignore_path.exists():
                with open(gitignore_path, "r") as f:
                    content = f.read()
            
            if filename in content:
                return

            with open(gitignore_path, "a") as f:
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n# Local Secrets\n{filename}\n")
            
            action = "Updated" if gitignore_path.exists() else "Created"
            print(f"✅ {action} .gitignore to exclude '{filename}'")
            
        except Exception as e:
            print(f"⚠️  Could not update .gitignore: {e}")

    def _create_fresh_file(self, path: Path):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(self.config_data, f, indent=2)
            print(f"✅ Created new configuration file at: {path}")
        except Exception as e:
            print(f"❌ Error creating file: {e}")

    def _merge_and_save(self, path: Path):
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