import json
import os
import sys
import subprocess
import argparse
import shutil
import re
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
        
        # Source paths
        self.source_dir = Path(__file__).parent.resolve()
        self.source_agent_script = self.source_dir / "burndown_server.py"
        self.source_requirements = self.source_dir / "requirements.txt"
        
        # Destination paths
        self.dest_agent_script = self.settings_dir / "burndown_server.py"
        self.dest_requirements = self.settings_dir / "requirements.txt"

        self.collected_secrets = {}
        self._load_env_file()

    def _create_requirements_file(self):
        source_req = self.source_requirements
        if source_req.exists():
            with open(source_req, "r") as src, open(self.dest_requirements, "w") as dst:
                dst.write(src.read())
        else:
            # If source requirements.txt does not exist, create an empty file or handle as needed
            with open(self.dest_requirements, "w") as dst:
                dst.write("")

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
            profile_in = input("   Profile Name [default]: ").strip()
            if not profile_in: 
                profile = "default"
                print("   > Selected default profile: 'default'")
            else:
                profile = profile_in
            self.collected_secrets["ROO_CODE_PROFILE_NAME"] = profile

    # --- 2. INSTALL AGENT ASSETS ---
    def install_agent_script(self):
        print("\n--- Installing Burndown Agent Assets ---")
        try:
            self.settings_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ Error creating directory {self.settings_dir}: {e}")
            sys.exit(1)

        # Copy the server script
        if self.source_agent_script.exists():
            shutil.copy2(self.source_agent_script, self.dest_agent_script)
            print(f"✅ Installed logic to {self.dest_agent_script}")
        else:
            print(f"⚠️  Source script missing. Ensure burndown_server.py is present.")

        # Create requirements.txt with correct content
        self._create_requirements_file()
        print(f"✅ Created requirements.txt")

        # Create virtual environment
        venv_path = self.settings_dir / "venv"
        if venv_path.exists():
            print("🔧 Removing existing venv...")
            shutil.rmtree(venv_path)

        print("🔧 Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            print("✅ Virtual environment created")
        except Exception as e:
            print(f"❌ Error creating venv: {e}")
            sys.exit(1)

        # Install dependencies
        print("📦 Installing dependencies...")
        pip_path = venv_path / "bin" / "pip"
        if os.name == 'nt':  # Windows
            pip_path = venv_path / "Scripts" / "pip.exe"
        
        try:
            subprocess.run([str(pip_path), "install", "-r", str(self.dest_requirements)], 
                        check=True, capture_output=True)
            print("✅ Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing dependencies: {e}")
            print(f"stdout: {e.stdout.decode() if e.stdout else ''}")
            print(f"stderr: {e.stderr.decode() if e.stderr else ''}")
            sys.exit(1)

    # --- 3. SERVER CONFIGURATION ---
    def configure_servers(self):
        print("\n--- Configuring MCP Access ---")
        gh_token = self.get_user_input("GitHub Personal Access Token", "GITHUB_PERSONAL_ACCESS_TOKEN")
        
        print("\n--- Configuring Azure DevOps MCP ---")
        print("ℹ️  Tip: Enter the Organization Name (e.g. 'ExampleOrg') or Project URL.")
        ado_scope = self.get_user_input("Azure DevOps Scope", "AZURE_DEVOPS_SCOPE")
        ado_token = self.get_user_input("Azure DevOps PAT", "AZURE_DEVOPS_EXT_PAT")

        ado_args = MCP_SERVERS["azure-devops"]["args"].copy()
        ado_args.append(ado_scope) 

        if os.name == 'nt':
            python_cmd = ".roo/venv/Scripts/python.exe"
        else:
            python_cmd = ".roo/venv/bin/python"
        
        # Use relative path for script
        script_arg = ".roo/burndown_server.py"

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
                "args": [script_arg], 
                "env": {
                    "AZURE_DEVOPS_SCOPE": ado_scope,
                    "AZURE_DEVOPS_EXT_PAT": ado_token,
                    "AZURE_DEVOPS_ORG_URL": ado_scope,
                    "ROO_CODE_PROFILE_NAME": self.collected_secrets.get("ROO_CODE_PROFILE_NAME", "default")
                },
                "disabled": False,
                "autoApprove": []
            }
        }

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

            # A. Extensions
            customizations = data.setdefault("customizations", {})
            vscode_cust = customizations.setdefault("vscode", {})
            extensions = vscode_cust.setdefault("extensions", [])
            if ROO_EXTENSION_ID not in extensions:
                extensions.append(ROO_EXTENSION_ID)
                print(f"✅ Added {ROO_EXTENSION_ID} to extensions.")
                modified = True

            # B. Persistence Mount
            mounts = data.get("mounts", [])
            if not isinstance(mounts, list):
                mounts = []
                data["mounts"] = mounts
            target_mount = "/home/vscode/.vscode-server/data"
            mount_str = f"source=vscode-server-data,target={target_mount},type=volume"
            
            mount_exists = any(
                "source=vscode-server-data" in m and f"target={target_mount}" in m
                for m in mounts
            )
            if not mount_exists:
                mounts.append(mount_str)
                print(f"✅ Injected persistence mount.")
                modified = True

            # C. Python + Requirements
            is_alpine = "alpine" in raw_content.lower()

            if not is_alpine:
                # Check referenced Docker Compose files
                compose_files = data.get("dockerComposeFile")
                if compose_files:
                    if isinstance(compose_files, str): compose_files = [compose_files]
                    for cf_name in compose_files:
                        cf_path = dc_path.parent / cf_name
                        if cf_path.exists():
                            try:
                                with open(cf_path, "r") as cf:
                                    if "alpine" in cf.read().lower():
                                        is_alpine = True
                                        print(f"🔍 Detected Alpine in {cf_name}")
                                        break
                            except (FileNotFoundError, IOError): pass
            
            if not is_alpine:
                # Check referenced Dockerfile
                build = data.get("build")
                if isinstance(build, dict) and "dockerfile" in build:
                    df_path = dc_path.parent / build["dockerfile"]
                    if df_path.exists():
                        try:
                            with open(df_path, "r") as df:
                                if "alpine" in df.read().lower():
                                    is_alpine = True
                                    print(f"🔍 Detected Alpine in {build['dockerfile']}")
                        except (FileNotFoundError, IOError): pass

            if is_alpine:
                install_cmd = "apk add --no-cache python3 py3-pip py3-virtualenv"
                pip_cmd = "rm -rf .roo/venv && virtualenv .roo/venv && .roo/venv/bin/pip install -r .roo/requirements.txt"
            else:
                install_cmd = "apt-get update && apt-get install -y python3 python3-pip python3-venv"
                pip_cmd = "rm -rf .roo/venv && python3 -m venv .roo/venv && .roo/venv/bin/pip install -r .roo/requirements.txt"

            current_cmd = data.get("postCreateCommand", "")

            commands = []

            # 1. Python installation (if not present)
            python_install_patterns = [
                r'\bapt(-get)?\s+install\s+.*python3\b',
                r'\bapk\s+add\s+.*python3\b',
                r'\bdnf\s+install\s+.*python3\b',
                r'\byum\s+install\s+.*python3\b',
                r'\bzypper\s+install\s+.*python3\b',
                r'\bpacman\s+-S\s+.*python3\b',
                r'\bpython3\s+-m\s+venv\b',  # direct venv creation
            ]
            def has_python_install(cmd):
                subcommands = [c.strip() for c in re.split(r'&&|;', cmd) if c.strip()]
                for subcmd in subcommands:
                    for pat in python_install_patterns:
                        if re.search(pat, subcmd, re.IGNORECASE):
                            return True
                return False
            if not has_python_install(current_cmd):
                commands.append(install_cmd)

            # 2. Pip requirements (if not present)
            if "requirements.txt" not in current_cmd:
                commands.append(pip_cmd)

            # 3. Existing command (if any and not empty)
            if current_cmd and current_cmd.strip():
                commands.append(current_cmd)

            # Only update if we added something new
            if len(commands) > (1 if current_cmd else 0):
                data["postCreateCommand"] = " && ".join(commands)
                print(f"✅ Updated postCreateCommand")
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
            except json.JSONDecodeError:
                print(f"⚠️  Warning: Invalid JSON in {self.settings_file}. Falling back to empty config.")
            
            if "mcpServers" not in existing: existing["mcpServers"] = {}
            existing["mcpServers"].update(self.config_data["mcpServers"])
            
            with open(self.settings_file, "w") as f: json.dump(existing, f, indent=2)
            print(f"✅ Updated existing config at {self.settings_file}")
        else:
            with open(self.settings_file, "w") as f: json.dump(self.config_data, f, indent=2)
            print(f"✅ Created new config at {self.settings_file}")

        self._update_gitignore(".roo/")
        self._save_secrets_to_env()

    def _save_secrets_to_env(self):
        existing_keys = set()
        content = ""
        if self.env_file_path.exists():
            try:
                with open(self.env_file_path, "r") as f:
                    content = f.read()
                lines = content.splitlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key = line.split("=", 1)[0].strip()
                        existing_keys.add(key)
            except Exception as e: print(f"⚠️  Error reading .env: {e}")

        new_lines = []
        for key, val in self.collected_secrets.items():
            if key not in existing_keys:
                new_lines.append(f"{key}={val}")
        
        if not new_lines: return

        print("\n--- Persistence Setup ---")
        mode = "a" if self.env_file_path.exists() else "w"
        try:
            with open(self.env_file_path, mode) as f:
                if mode == "a" and content and not content.endswith("\n"):
                    f.write("\n")
                for line in new_lines:
                    f.write(f"{line}\n")
            
            print(f"✅ Saved new secrets to {self.env_file_path} (Appended)")
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
            print(f"✅ Added {entry} to .gitignore")
        except Exception as e: print(f"⚠️  Error updating .gitignore: {e}")

    def run(self):
        print(f"🔥 Burndown Agent Setup Initialized (Project Mode)")
        self.configure_profile() 
        self.install_agent_script() 
        self.configure_servers()
        self.save_configuration()
        self.inject_devcontainer_config()
        
        print(f"\n🎉 Setup Complete for {self.project_root.name}.")
        print("👉 Use the RooCode tool 'get_burndown_tasks' to start.")

if __name__ == "__main__":
    setup = BurndownSetup()
    setup.run()