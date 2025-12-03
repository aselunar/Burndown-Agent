# Burndown Agent Setup

This tool automates the configuration of RooCode/Cline MCP servers (GitHub and Azure DevOps) and injects necessary configurations into DevContainers.

## Prerequisites

* **Python 3.8+** (for running the setup script locally)
* **Node.js / npx** (for the MCP servers)
* **VS Code** with **RooCode** extension installed

---

## 🚀 Usage Method 1: Host-based Setup (Recommended)

This is the cleanest method. You run the script on your Mac/Windows host, targeting your project folder. This injects the configuration (`.roo/mcp.json` and `.env`) without needing Python installed inside your container.

1.  Open your terminal in the **Burndown Agent** directory.
2.  Run the script targeting your other repository:

    ```bash
    python3 setup.py --target ../path-to-your-project
    ```

3.  **Result:**
    * Creates/Updates `../path-to-your-project/.roo/mcp.json`
    * Creates/Updates `../path-to-your-project/.env` (Secrets are safe!)
    * Modifies `../path-to-your-project/.devcontainer/devcontainer.json` to include Python.

4.  **Finish:** Open the target project in VS Code (Reopen in Container) and you are ready.

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

Run ./local-server.bash in this repo.

Changes to files are served immediately (no restart needed).

From your test container, run the curl command (Option B) above.