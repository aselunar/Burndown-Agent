import os
import base64
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from urllib.parse import unquote, urlparse

# Environment Setup
project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, ".env")
load_dotenv(env_path)

mcp = FastMCP("Burndown Manager")

# ADO Configuration
ADO_ORG_URL = os.getenv("AZURE_DEVOPS_ORG_URL") or os.getenv("AZURE_DEVOPS_SCOPE")
ADO_PAT = os.getenv("AZURE_DEVOPS_EXT_PAT") or os.getenv("AZURE_DEVOPS_TOKEN")

# Extract project name from URL
PROJECT_NAME = None
if ADO_ORG_URL:
    url_parts = ADO_ORG_URL.rstrip('/').split('/')
    if len(url_parts) >= 5:
        PROJECT_NAME = unquote(url_parts[4])

def get_base_url():  
    if not ADO_ORG_URL:  
        return None  
    from urllib.parse import urlparse  
    parsed = urlparse(ADO_ORG_URL.rstrip('/'))  
    return f"{parsed.scheme}://{parsed.netloc}/{parsed.path.split('/')[1]}"  

def get_headers():
    if not ADO_PAT: return None
    auth = base64.b64encode(f":{ADO_PAT}".encode()).decode()
    return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

def run_wiql(query: str):
    if not ADO_ORG_URL or not ADO_PAT: return []
    base_url = get_base_url()
    api_url = f"{base_url}/_apis/wit/wiql?api-version=6.0"
    try:
        response = requests.post(api_url, headers=get_headers(), json={"query": query})
        if response.status_code == 200:
            return response.json().get("workItems", [])
        else :
            print(f"WIQL query failed with status {response.status_code}: {response.text}")
    except requests.RequestException as e:  
        # Handle network/API errors  
        return []  
    except Exception as e:  
        # Log unexpected errors for debugging  
        print(f"Unexpected error in run_wiql: {e}")  
        return []  

def get_work_items(ids: list):
    if not ids: return []
    try:
        chunk_size = 200
        all_items = []
        base_url = get_base_url()
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            ids_str = ",".join(map(str, chunk))
            api_url = f"{base_url}/_apis/wit/workitems?ids={ids_str}&api-version=6.0"
            res = requests.get(api_url, headers=get_headers())
            if res.status_code == 200:
                all_items.extend(res.json().get("value", []))
        return all_items
    except requests.RequestException as e:  
        print(f"Error fetching work items: {e}")  
        return []  

# @mcp.tool()
def _get_burndown_tasks_impl(limit: int = 5, prioritize_parents: bool = True) -> str:
    """
    Fetches the next batch of tasks to burn down from Azure DevOps.
    """
    try:
        if not PROJECT_NAME:
            return "❌ Error: Could not extract project name from AZURE_DEVOPS_ORG_URL"
        
        project_filter = f"[System.TeamProject]='{PROJECT_NAME}'"
        tasks = []
        
        if prioritize_parents:
            # Fetch Top Parents
            pq = f"SELECT [System.Id] FROM WorkItems WHERE {project_filter} AND [System.State] NOT IN ('Closed','Removed','Resolved','Done','Completed') ORDER BY [Microsoft.VSTS.Common.Priority] ASC"
            parents = run_wiql(pq)
            seen_ids = set()  # Track what we've already added
            
            for p in parents:
                if len(tasks) >= limit: break
                
                # Skip if already added
                if p['id'] in seen_ids:
                    continue
                    
                cq = f"SELECT [System.Id] FROM WorkItems WHERE {project_filter} AND [System.Parent]={p['id']} AND [System.State] NOT IN ('Closed','Removed','Resolved','Done','Completed')"
                children = run_wiql(cq)
                if children:
                    # Has children - add the children (they're bottom level)
                    child_items = get_work_items([c['id'] for c in children])
                    for item in child_items:
                        if item['id'] not in seen_ids:
                            tasks.append(item)
                            seen_ids.add(item['id'])
                else:
                    # No children - parent itself is bottom level
                    parent_items = get_work_items([p['id']])
                    for item in parent_items:
                        if item['id'] not in seen_ids:
                            tasks.append(item)
                            seen_ids.add(item['id'])
        else:
            # Direct Query
            q = f"SELECT [System.Id] FROM WorkItems WHERE {project_filter} AND [System.State] NOT IN ('Closed','Removed','Resolved','Done','Completed') ORDER BY [Microsoft.VSTS.Common.Priority] ASC"
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
    
@mcp.tool()
def get_burndown_tasks(limit: int = 5, prioritize_parents: bool = True) -> str:
    """
    Fetches the next batch of tasks to burn down from Azure DevOps.
    """
    return _get_burndown_tasks_impl(limit, prioritize_parents)

if __name__ == "__main__":
    mcp.run(transport="stdio")