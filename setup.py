import json
import os
import sys
import argparse
import re
import stat
from pathlib import Path

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

ROO_EXTENSION_ID = "rooveterinaryinc.roo-cline"

class BurndownSetup:
    def __init__(self):
        self.config_data = {"mcpServers": {}}
        
        parser = argparse.ArgumentParser(description="Configure RooCode MCP Servers for a target project.")
        parser.add_argument("--target", type=str, help="Path to the target project directory (default: current directory)")
        args = parser.parse_args()

        if args.target:
            self.project_root = Path(args.target).resolve()
            if not self.project_root.exists():
                print(f"❌ Error: Target directory '{self.project_root}' does not exist.")
                sys.exit(1)
            print(f"🎯 Targeting Project: {self.project_root}")
        else:
            self.project_root = Path.cwd()

        self.env_file_path = self.project_root / ".env"
        self.settings_dir = self.project_root / ".roo" 
        self.settings_file = self.settings_dir / "mcp.json"
        
        self.script_dir = Path(__file__).parent.resolve()
        self.burndown_script = self.script_dir / "burndown_server.py"

        self.collected_secrets = {}
        self._load_env_file()

    def _load_env_file(self):
        if not self.env_file_path.exists(): return
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
            sys.exit(0)

    # --- 1. PROFILE CONFIGURATION ---
    def configure_profile(self):
        print("\n--- Project Configuration Profile ---")
        print("ℹ️  RooCode uses Configuration Profiles (Settings > Profiles) to manage API keys and Models.")
        
        profile = os.getenv("ROO_CODE_PROFILE_NAME")
        if not profile:
            print("   What is the name of the RooCode Profile for this project?")
            print("   (e.g. 'default', 'Work', 'Personal')")
            profile = input("   Profile Name [default]: ").strip()
            if not profile: 
                profile = "default"
                print("   > Selected default profile: 'default'")
            self.collected_secrets["ROO_CODE_PROFILE_NAME"] = profile

    # --- 2. SERVER CONFIGURATION ---
    def configure_servers(self):
        print("\n--- Configuring MCP Access ---")
        gh_token = self.get_user_input("GitHub Personal Access Token", "GITHUB_PERSONAL_ACCESS_TOKEN")
        
        print("\n--- Configuring Azure DevOps MCP ---")
        ado_scope = self.get_user_input("Azure DevOps Scope (Org Name or Project URL)", "AZURE_DEVOPS_SCOPE")
        ado_token = self.get_user_input("Azure DevOps PAT", "AZURE_DEVOPS_EXT_PAT")

        ado_args = MCP_SERVERS["azure-devops"]["args"].copy()
        ado_args.append(ado_scope) 

        python_cmd = sys.executable 

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
            },
            "burndown-manager": {
                "command": python_cmd,
                "args": [str(self.burndown_script)],
                "env": {
                    "AZURE_DEVOPS_SCOPE": ado_scope,
                    "AZURE_DEVOPS_EXT_PAT": ado_token,
                    "AZURE_DEVOPS_ORG_URL": ado_scope
                },
                "disabled": False,
                "autoApprove": []
            }
        }

    # --- 3. DETERMINISTIC LAUNCH SCRIPT ---
    def create_launch_script(self):
        """Creates a script to launch VS Code with the enforced Profile."""
        profile_name = self.collected_secrets.get("ROO_CODE_PROFILE_NAME", "default")
        
        print(f"\n--- Creating Safe Launch Script ({profile_name}) ---")
        
        is_windows = os.name == 'nt'
        script_name = "start_agent.bat" if is_windows else "start_agent.sh"
        script_path = self.project_root / script_name
        
        if is_windows:
            content = f'@echo off\ncode . --profile "{profile_name}"\n'
        else:
            content = f'#!/bin/sh\n# Launches VS Code with the enforced profile\ncode . --profile "{profile_name}"\n'

        try:
            with open(script_path, "w") as f:
                f.write(content)
            
            # Make executable on Unix
            if not is_windows:
                st = os.stat(script_path)
                os.chmod(script_path, st.st_mode | stat.S_IEXEC)
                
            print(f"✅ Created {script_name}")
            print(f"👉 Use './{script_name}' to open this project with the correct profile.")
            
            self._update_gitignore(script_name)
            
        except Exception as e:
            print(f"❌ Error creating launch script: {e}")

    # --- 4. DEVCONTAINER AUTOMATION ---
    def inject_devcontainer_config(self):
        print("\n--- Checking DevContainer Configuration ---")
        
        dc_path = self.project_root / ".devcontainer" / "devcontainer.json"
        if not dc_path.exists():
            dc_path = self.project_root / "devcontainer.json"
            if not dc_path.exists():
                print("ℹ️  No devcontainer.json found. Skipping injection.")
                return

        print(f"🔍 Found {dc_path.name}")
        
        try:
            with open(dc_path, "r") as f:
                raw_content = f.read()

            pattern = r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/'
            def replacer(match):
                return match.group(1) if match.group(1) else ""
            
            json_content = re.sub(pattern, replacer, raw_content, flags=re.DOTALL)
            data = json.loads(json_content)
            modified = False

            # A. Inject Extension
            customizations = data.setdefault("customizations", {})
            vscode_cust = customizations.setdefault("vscode", {})
            extensions = vscode_cust.setdefault("extensions", [])
            if ROO_EXTENSION_ID not in extensions:
                extensions.append(ROO_EXTENSION_ID)
                print(f"✅ Added {ROO_EXTENSION_ID} to extensions.")
                modified = True

            # B. Inject Persistence Mount (CRITICAL FOR SAVING PROFILE SELECTION)
            mounts = data.setdefault("mounts", [])
            target_mount = "/home/vscode/.vscode-server/data"
            mount_str = f"source=vscode-server-data,target={target_mount},type=volume"
            
            if not any("vscode-server-data" in m for m in mounts):
                mounts.append(mount_str)
                print(f"✅ Injected persistence mount (Saves Profile Selection).")
                modified = True

            # C. Inject Python Command
            is_alpine = "alpine" in raw_content.lower()
            if not is_alpine:
                # Check referenced files (Docker Compose / Dockerfile)
                pass

            if is_alpine:
                install_cmd = "apk add --no-cache python3 curl"
            else:
                install_cmd = "apt-get update && apt-get install -y python3 curl"

            current_cmd = data.get("postCreateCommand", "")
            if "python3" not in current_cmd:
                if current_cmd:
                    data["postCreateCommand"] = install_cmd + " && " + current_cmd
                else:
                    data["postCreateCommand"] = install_cmd
                print(f"✅ Injected Python install command.")
                modified = True

            if modified:
                print("⚠️  Updating devcontainer.json (Comments will be removed)...")
                with open(dc_path, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write('\n')
                print("✅ devcontainer.json updated successfully.")
            else:
                print("✅ devcontainer.json is already up to date.")

        except Exception as e:
            print(f"❌ Could not automatically update devcontainer.json: {e}")

    def save_configuration(self):
        print("\n--- Finalizing Configuration ---")
        try:
            self.settings_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ Error creating directory {self.settings_dir}: {e}")
            return

        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    existing = json.load(f)
            except: existing = {"mcpServers": {}}
            
            if "mcpServers" not in existing: existing["mcpServers"] = {}
            existing["mcpServers"].update(self.config_data["mcpServers"])
            
            with open(self.settings_file, "w") as f: json.dump(existing, f, indent=2)
            print("✅ Updated existing config at {self.settings_file}")
        else:
            with open(self.settings_file, "w") as f: json.dump(self.config_data, f, indent=2)
            print(f"✅ Created new config at {self.settings_file}")

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
        print(f"🔥 Burndown Agent Setup Initialized (Project Mode)")
        self.configure_profile()
        self.configure_servers()
        self.save_configuration()
        self.create_launch_script() # New Deterministic Launcher
        self.inject_devcontainer_config()
        
        print(f"\n🎉 Setup Complete for {self.project_root.name}.")
        print("👉 Please use './start_agent.sh' to launch VS Code with the correct profile.")

if __name__ == "__main__":
    setup = BurndownSetup()
    setup.run()