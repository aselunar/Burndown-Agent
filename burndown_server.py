import os
import base64
import requests
from dotenv import load_dotenv
from mcp import FastMCP

# Environment Setup
project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, ".env")
load_dotenv(env_path)

mcp = FastMCP("Burndown Manager")

# ADO Configuration
ADO_ORG_URL = os.getenv("AZURE_DEVOPS_ORG_URL") or os.getenv("AZURE_DEVOPS_SCOPE")
ADO_PAT = os.getenv("AZURE_DEVOPS_EXT_PAT") or os.getenv("AZURE_DEVOPS_TOKEN")

def get_headers():
    if not ADO_PAT: return None
    auth = base64.b64encode(f":{ADO_PAT}".encode()).decode()
    return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

def run_wiql(query: str):
    if not ADO_ORG_URL or not ADO_PAT: return []
    base_url = ADO_ORG_URL.rstrip('/')
    api_url = f"{base_url}/_apis/wit/wiql?api-version=6.0"
    try:
        response = requests.post(api_url, headers=get_headers(), json={"query": query})
        if response.status_code == 200:
            return response.json().get("workItems", [])
    except: pass
    return []

def get_work_items(ids: list):
    if not ids: return []
    try:
        chunk_size = 200
        all_items = []
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            ids_str = ",".join(map(str, chunk))
            base_url = ADO_ORG_URL.rstrip('/')
            api_url = f"{base_url}/_apis/wit/workitems?ids={ids_str}&api-version=6.0"
            res = requests.get(api_url, headers=get_headers())
            if res.status_code == 200:
                all_items.extend(res.json().get("value", []))
        return all_items
    except: return []

@mcp.tool()
def get_burndown_tasks(limit: int = 5, prioritize_parents: bool = True) -> str:
    """
    Fetches the next batch of tasks to burn down from Azure DevOps.
    """
    try:
        tasks = []
        if prioritize_parents:
            # Fetch Top Parents
            pq = "SELECT [System.Id] FROM WorkItems WHERE [System.State] NOT IN ('Closed','Removed','Resolved') AND [System.Parent]=0 ORDER BY [Microsoft.VSTS.Common.Priority] ASC"
            parents = run_wiql(pq)
            for p in parents:
                if len(tasks) >= limit: break
                cq = f"SELECT [System.Id] FROM WorkItems WHERE [System.Parent]={p['id']} AND [System.State] NOT IN ('Closed','Removed','Resolved') AND [System.WorkItemType] IN ('Task','Bug')"
                children = run_wiql(cq)
                if children:
                    tasks.extend(get_work_items([c['id'] for c in children]))
        else:
            # Direct Query
            q = "SELECT [System.Id] FROM WorkItems WHERE [System.State] NOT IN ('Closed','Removed','Resolved') AND [System.WorkItemType] IN ('Task','Bug') ORDER BY [Microsoft.VSTS.Common.Priority] ASC"
            refs = run_wiql(q)
            tasks.extend(get_work_items([r['id'] for r in refs[:limit]]))

        if not tasks:
            return "✅ No active tasks found. Backlog is clear!"

        output = f"## 🚀 Burndown Mission ({len(tasks[:limit])} items)\n"
        for t in tasks[:limit]:
            tid = t['id']
            title = t['fields'].get('System.Title', 'Unknown')
            wtype = t['fields'].get('System.WorkItemType', 'Item')
            output += f"- [ ] **{wtype} #{tid}**: {title}\n"
            
        return output

    except Exception as e:
        return f"❌ Error fetching tasks: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")