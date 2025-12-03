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