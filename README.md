# 🔥 Burndown Agent

**Automated Azure DevOps → GitHub orchestration for RooCode/Cline.**

Automatically connects your ADO backlog to RooCode with zero manual MCP configuration. Works seamlessly in DevContainers.

## ✨ What It Does

1. **Auto-configures MCP servers** - GitHub + Azure DevOps MCP servers in one command
2. **DevContainer-ready** - Injects Python, dependencies, and persistence mounts automatically  
3. **Project-level ADO queries** - Correctly scopes to your specific ADO project (solves the 20K item problem)
4. **Priority-aware burndown** - Fetches tasks respecting parent work item hierarchy
5. **Zero secrets in git** - All tokens stored in `.env` (auto-gitignored)

## 🎯 Key Achievement

Solved the **"MCP setup in DevContainers is painful"** problem. No more manual JSON editing, no more forgetting to install Python, no more persistence issues.

---

## Prerequisites

* **Python 3.8+** (for running the setup script locally)
* **Node.js / npx** (for the MCP servers)
* **VS Code** with **RooCode** extension installed

---

## 🚀 Usage Method 1: Host-based Setup (Recommended)

This is the cleanest method. You run the script on your Mac/Windows host, targeting your project folder. This injects the configuration (`.roo/mcp.json` and `.env`) without needing Python installed inside your container.

### Quick Start (5 minutes)

1. Clone and navigate to Burndown Agent:
   ```bash
   git clone https://github.com/aselunar/Burndown-Agent.git
   cd Burndown-Agent
2.  Run the script targeting your other repository:

    ```bash
    python3 setup.py --target ../path-to-your-project
    ```

3.  **Provide when prompted:**

* GitHub PAT (with repo access)
* Azure DevOps Organization & Project URL (e.g., https://dev.azure.com/YourOrg/YourProject)
* Azure DevOps PAT (with Work Items read access)

4. Result:

* Creates/Updates /path/to/your/project/.roo/mcp.json
* Creates/Updates /path/to/your/project/.env (Secrets are safe!)
* Modifies /path/to/your/project/.devcontainer/devcontainer.json to include Python

5. Finish: Open the target project in VS Code (Reopen in Container) and you are ready.

## Use It
In RooCode chat:

`Get my top 5 burndown tasks`

Or for orchestration (creates GitHub issues):

`Run burndown on my top 3 tasks`

---

## 📦 Usage Method 2: Bootstrapper (For Remote/Containers)

Use this method if you are already inside a container or remote environment and want to bootstrap the agent from scratch.

### Option A: Production (GitHub)

If you are installing the agent from the public repository, use this one-liner. This downloads the latest version from the `main` branch.

```bash
curl -sL https://raw.githubusercontent.com/aselunar/Burndown-Agent/main/install.sh | sh
```

### Option B: Development (Local)

If you are developing this agent and want to test the bootstrapper locally without pushing to GitHub:

Start the Local Server:
In the Burndown-Agent root, run:

```bash
./local-server.bash
```

(This starts a Python server on port 8000)

Run inside the Container:
Inside your target Dev Container terminal with Python already installed, run:

```bash
# Run the bootstrapper pointing to your host machine
curl -sL http://host.docker.internal:8000/install.sh | sh
``` 


🛠️ Development Workflow

To test changes to setup.py or install.sh:

1. Run ./local-server.bash in this repo.

2. Changes to files are served immediately (no restart needed).

3. From your test container, run the curl command (Option B) above.

---

# 🧪 Testing

## Test the MCP Tool Directly

You can test the underlying logic without going through RooCode:

```bash
source .roo/venv/bin/activate
python3 test_burndown_tool.py
```
This will show you the actual tasks being fetched from Azure DevOps.

## Dogfood Development Mode

To test changes without copying files:

1. Modify .roo/mcp.json → mcpServers.burndown-manager.args from [".roo/burndown_server.py"] to ["burndown_server.py"]
2. Edit burndown_server.py (source file in project root)
3. Restart the MCP server in RooCode
4. Test changes immediately
Note: You will need to activate the venv first: source .roo/venv/bin/activate

---

🏗️ What's Next
* GitHub PR automation - Currently creates issues; PR creation has MCP friction
* Batch processing - Handle >100 work items with pagination
* Status sync - Update ADO when GitHub issues close
* Multi-project support - Query across multiple ADO projects

---

🐛 Troubleshooting
"No tasks found" but I have work items:

* Check `.env` has correct `AZURE_DEVOPS_ORG_URL` with project name
* Verify project name in URL matches ADO exactly (case-sensitive)
* Restart MCP server after `.env` changes

MCP server won't start:

* Check `.roo/venv/` exists and has dependencies installed
* Run `source .roo/venv/bin/activate && pip install -r .roo/requirements.txt`
* Check VS Code Output panel for Python errors

Changes to `burndown_server.py` not taking effect:

* Restart MCP server (RooCode sidebar → MCP icon → restart)
* Or reload VS Code window (`Cmd+Shift+P` → "Developer: Reload Window")

"VS402337: The number of work items returned exceeds the size limit of 20000":

* This means your query is too broad
* The burndown agent now correctly scopes to your project using `[System.TeamProject]` filters
* Make sure your `AZURE_DEVOPS_ORG_URL` includes the project name

---

🏆 Hackathon 2025

Built to solve real DevOps friction: connecting enterprise backlogs to AI coding assistants without the config nightmare.
