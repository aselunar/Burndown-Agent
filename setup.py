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
        # EXACT MATCH for your working configuration
        "command": "npx",
        "args": ["-y", "@azure-devops/mcp@1.0.0"], 
        "env_vars": ["AZURE_DEVOPS_EXT_PAT"]
    }
}

class BurndownSetup:
    def __init__(self):
        self.config_data = {"mcpServers": {}}
        
        # ANCHOR: Project Root is where we are running the script (Current Working Directory)
        self.project_root = Path.cwd()
        self.env_file_path = self.project_root / ".env"
        
        # TARGET: Project-specific setting (.roo/mcp.json)
        self.settings_dir = self.project_root / ".roo" 
        self.settings_file = self.settings_dir / "mcp.json"

        self.collected_secrets = {}
        self._load_env_file()

    def _verify_node_exists(self):
        """Ensures npx is available in the path."""
        if not shutil.which("npx"):
            print("❌ Error: 'npx' is not found in your PATH.")
            print("   Please install Node.js to use these MCP servers.")
            sys.exit(1)
        print("✅ Node.js runtime (npx) detected.")

    def _load_env_file(self):
        """Simple .env parser."""
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

    def configure_servers(self):
        print("\n--- Configuring GitHub MCP ---")
        gh_token = self.get_user_input("GitHub Personal Access Token", "GITHUB_PERSONAL_ACCESS_TOKEN")
        
        print("\n--- Configuring Azure DevOps MCP ---")
        # 1. Ask for Organization Name (Required argument for this package)
        ado_org = self.get_user_input("Azure DevOps Organization Name (e.g. CropScience-1)", "AZURE_DEVOPS_ORG")
        
        # 2. Ask for the Token (New variable name)
        ado_token = self.get_user_input("Azure DevOps PAT", "AZURE_DEVOPS_EXT_PAT")

        # 3. Construct the Args list dynamically
        # We start with ["-y", "@azure-devops/mcp@1.0.0"]
        ado_args = MCP_SERVERS["azure-devops"]["args"].copy()
        # We append the Organization Name as the final argument
        ado_args.append(ado_org) 

        self.config_data["mcpServers"] = {
            "github": {
                "command": MCP_SERVERS["github"]["command"],
                "args": MCP_SERVERS["github"]["args"],
                "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": gh_token },
                "disabled": False,
                "autoApprove": []
            },
            "azure-devops": {
                "command": MCP_SERVERS["azure-devops"]["command"],
                "args": ado_args, # This will be ["-y", "@azure-devops/mcp@1.0.0", "CropScience-1"]
                "env": { 
                    "AZURE_DEVOPS_EXT_PAT": ado_token 
                },
                "disabled": False,
                "autoApprove": []
            }
        }

    def save_configuration(self):
        print("\n--- Finalizing Configuration ---")
        
        # 1. Create the .roo directory if missing
        try:
            self.settings_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ Error creating directory {self.settings_dir}: {e}")
            return

        # 2. Check for existing config
        if self.settings_file.exists():
            print(f"✅ Found existing configuration at: {self.settings_file}")
            # Merge logic
            try:
                with open(self.settings_file, "r") as f:
                    existing = json.load(f)
            except:
                existing = {"mcpServers": {}}
            
            if "mcpServers" not in existing:
                existing["mcpServers"] = {}
            
            existing["mcpServers"].update(self.config_data["mcpServers"])
            
            with open(self.settings_file, "w") as f:
                json.dump(existing, f, indent=2)
            print("✅ Configuration updated.")
        else:
            # Create new
            with open(self.settings_file, "w") as f:
                json.dump(self.config_data, f, indent=2)
            print(f"✅ Created new configuration file at: {self.settings_file}")

        # 3. CRITICAL: Add to .gitignore
        self._update_gitignore(".roo/")
        self._save_secrets_to_env()

    def _save_secrets_to_env(self):
        """Saves collected secrets to .env"""
        existing_content = ""
        if self.env_file_path.exists():
            with open(self.env_file_path, "r") as f:
                existing_content = f.read()

        new_lines = []
        for key, val in self.collected_secrets.items():
            if key not in existing_content:
                new_lines.append(f"{key}={val}")
        
        if not new_lines:
            return

        print("\n--- Persistence Setup ---")
        mode = "a" if self.env_file_path.exists() else "w"
        try:
            with open(self.env_file_path, mode) as f:
                if mode == "a" and existing_content and not existing_content.endswith("\n"):
                    f.write("\n")
                for line in new_lines:
                    f.write(f"{line}\n")
            
            print(f"✅ Saved secrets to {self.env_file_path}")
            self._update_gitignore(".env")
        except Exception as e:
            print(f"❌ Error saving .env: {e}")

    def _update_gitignore(self, entry: str):
        """Adds entry to .gitignore."""
        gitignore_path = self.project_root / ".gitignore"
        try:
            content = ""
            if gitignore_path.exists():
                with open(gitignore_path, "r") as f:
                    content = f.read()
            
            if entry in content:
                return

            with open(gitignore_path, "a") as f:
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n# Local Secrets\n{entry}\n")
            
            action = "Updated" if gitignore_path.exists() else "Created"
            print(f"✅ {action} .gitignore to exclude '{entry}'")
        except Exception as e:
            print(f"⚠️  Could not update .gitignore: {e}")

    def run(self):
        print(f"🔥 Burndown Agent Setup Initialized (Project Mode)")
        self._verify_node_exists()
        self.configure_servers()
        self.save_configuration()
        print("\n🎉 Setup Complete. Restart RooCode to apply.")

if __name__ == "__main__":
    setup = BurndownSetup()
    setup.run()