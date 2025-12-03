import json
import os
import platform
import sys
import shutil
import argparse
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
        "args": ["-y", "@azure-devops/mcp@1.0.0"], 
        "env_vars": ["AZURE_DEVOPS_EXT_PAT"]
    }
}

class BurndownSetup:
    def __init__(self):
        self.config_data = {"mcpServers": {}}
        
        # 1. Parse Command Line Arguments
        parser = argparse.ArgumentParser(description="Configure RooCode MCP Servers for a target project.")
        parser.add_argument("--target", type=str, help="Path to the target project directory (default: current directory)")
        args = parser.parse_args()

        # 2. Determine Project Root
        if args.target:
            self.project_root = Path(args.target).resolve()
            if not self.project_root.exists():
                print(f"❌ Error: Target directory '{self.project_root}' does not exist.")
                sys.exit(1)
            print(f"🎯 Targeting Project: {self.project_root}")
        else:
            self.project_root = Path.cwd()

        self.env_file_path = self.project_root / ".env"
        
        # TARGET: Project-specific setting (.roo/mcp.json)
        self.settings_dir = self.project_root / ".roo" 
        self.settings_file = self.settings_dir / "mcp.json"

        self.collected_secrets = {}
        # Try loading env from target first (to update existing)
        self._load_env_file()

    def _verify_node_exists(self):
        # We only check for node locally since we assume npx will run inside the target's environment later
        # But strictly speaking, this check is less relevant if running "remote" setup.
        pass 

    def _load_env_file(self):
        if not self.env_file_path.exists(): return
        print(f"ℹ️  Loading environment variables from {self.env_file_path}")
        try:
            with open(self.env_file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line: continue
                    key, value = line.split("=", 1)
                    value = value.strip("'").strip('"')
                    if key not in os.environ: os.environ[key] = value
        except Exception as e: print(f"⚠️  Warning: Could not read .env file: {e}")

    def get_user_input(self, prompt: str, env_var: str) -> str:
        value = os.environ.get(env_var)
        if value:
            print(f"   Found {env_var} in environment.")
            self.collected_secrets[env_var] = value
            return value
        try:
            val = input(f"   Enter {prompt}: ").strip()
            if not val: raise ValueError("Value cannot be empty")
            self.collected_secrets[env_var] = val
            return val
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            sys.exit(0)

    def configure_servers(self):
        print("\n--- Configuring GitHub MCP ---")
        gh_token = self.get_user_input("GitHub Personal Access Token", "GITHUB_PERSONAL_ACCESS_TOKEN")
        
        print("\n--- Configuring Azure DevOps MCP ---")
        ado_org = self.get_user_input("Azure DevOps Organization Name", "AZURE_DEVOPS_ORG")
        ado_token = self.get_user_input("Azure DevOps PAT", "AZURE_DEVOPS_EXT_PAT")

        ado_args = MCP_SERVERS["azure-devops"]["args"].copy()
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
                "args": ado_args,
                "env": { "AZURE_DEVOPS_EXT_PAT": ado_token },
                "disabled": False,
                "autoApprove": []
            }
        }

    def save_configuration(self):
        print("\n--- Finalizing Configuration ---")
        try:
            self.settings_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ Error creating directory {self.settings_dir}: {e}")
            return

        if self.settings_file.exists():
            print(f"✅ Found existing configuration at: {self.settings_file}")
            try:
                with open(self.settings_file, "r") as f:
                    existing = json.load(f)
            except: existing = {"mcpServers": {}}
            
            if "mcpServers" not in existing: existing["mcpServers"] = {}
            existing["mcpServers"].update(self.config_data["mcpServers"])
            
            with open(self.settings_file, "w") as f: json.dump(existing, f, indent=2)
            print("✅ Configuration updated.")
        else:
            with open(self.settings_file, "w") as f: json.dump(self.config_data, f, indent=2)
            print(f"✅ Created new configuration file at: {self.settings_file}")

        self._update_gitignore(".roo/")
        self._save_secrets_to_env()

    def _save_secrets_to_env(self):
        existing_content = ""
        if self.env_file_path.exists():
            with open(self.env_file_path, "r") as f: existing_content = f.read()

        new_lines = []
        for key, val in self.collected_secrets.items():
            if key not in existing_content: new_lines.append(f"{key}={val}")
        
        if not new_lines: return

        print("\n--- Persistence Setup ---")
        mode = "a" if self.env_file_path.exists() else "w"
        try:
            with open(self.env_file_path, mode) as f:
                if mode == "a" and existing_content and not existing_content.endswith("\n"): f.write("\n")
                for line in new_lines: f.write(f"{line}\n")
            print(f"✅ Saved secrets to {self.env_file_path}")
            self._update_gitignore(".env")
        except Exception as e: print(f"❌ Error saving .env: {e}")

    def _update_gitignore(self, entry: str):
        gitignore_path = self.project_root / ".gitignore"
        try:
            content = ""
            if gitignore_path.exists():
                with open(gitignore_path, "r") as f: content = f.read()
            if entry in content: return
            with open(gitignore_path, "a") as f:
                if content and not content.endswith("\n"): f.write("\n")
                f.write(f"\n# Local Secrets\n{entry}\n")
            action = "Updated" if gitignore_path.exists() else "Created"
            print(f"✅ {action} .gitignore to exclude '{entry}'")
        except Exception as e: print(f"⚠️  Could not update .gitignore: {e}")

    def run(self):
        print(f"🔥 Burndown Agent Setup Initialized")
        self.configure_servers()
        self.save_configuration()
        print(f"\n🎉 Setup Complete for {self.project_root.name}.")

if __name__ == "__main__":
    setup = BurndownSetup()
    setup.run()