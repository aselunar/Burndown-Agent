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
ADO_ORG_URL = os.getenv("AZURE_DEVOPS_ORG_URL")
ADO_PAT = os.getenv("AZURE_DEVOPS_EXT_PAT") or os.getenv("AZURE_DEVOPS_TOKEN")

# Extract project name from URL
def extract_project_name(ado_url):
    """
    Extracts the project name from an Azure DevOps URL.
    Handles both dev.azure.com and visualstudio.com formats.
    Returns None if extraction fails.
    """
    if not ado_url:
        return None
    try:
        parsed = urlparse(ado_url.rstrip('/'))
        # dev.azure.com/org/project/_apis/...
        if parsed.netloc.endswith("dev.azure.com"):
            path_parts = [p for p in parsed.path.split('/') if p]
            # Expect at least org/project
            if len(path_parts) >= 2:
                return unquote(path_parts[1])
        # org.visualstudio.com/project/_apis/...
        elif parsed.netloc.endswith("visualstudio.com"):
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) >= 1:
                return unquote(path_parts[0])
        # Unknown format
        return None
    except Exception as e:
        print(f"Error extracting project name from URL: {e}")
        return None
project_name = extract_project_name(ADO_ORG_URL)


def get_base_url():
    """
    Constructs the base URL for Azure DevOps REST API calls, handling both dev.azure.com and visualstudio.com formats.
    Returns None if the URL format is unrecognized.
    """
    if not ADO_ORG_URL:
        return None
    try:
        parsed = urlparse(ADO_ORG_URL.rstrip('/'))
        # dev.azure.com/org/project/_apis/...
        if parsed.netloc.endswith("dev.azure.com"):
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) >= 2:
                org = path_parts[0]
                project = path_parts[1]
                return f"{parsed.scheme}://{parsed.netloc}/{org}/{project}"
        # org.visualstudio.com/project/_apis/...
        elif parsed.netloc.endswith("visualstudio.com"):
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) >= 1:
                project = path_parts[0]
                return f"{parsed.scheme}://{parsed.netloc}/{project}"
        # Unknown format
        return None
    except Exception as e:
        print(f"Error constructing base URL from ADO_ORG_URL: {e}")
        return None
    
def get_headers():
    if not ADO_PAT: raise Exception("ADO_PAT is not set")
    auth = base64.b64encode(f":{ADO_PAT}".encode()).decode()
    return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

def run_wiql(query: str):
    if not ADO_ORG_URL or not ADO_PAT: raise Exception("AZURE_DEVOPS_ORG_URL or AZURE_DEVOPS_TOKEN is not set")
    base_url = get_base_url()
    api_url = f"{base_url}/_apis/wit/wiql?api-version=6.0"
    try:
        response = requests.post(api_url, headers=get_headers(), json={"query": query})
        if response.status_code == 200:
            return response.json().get("workItems", [])
        else:
            print(f"WIQL query failed with status {response.status_code}: {response.text}")
    except Exception as e:  
        print(f"Unexpected error in run_wiql: {e}")  
        return [] 

def get_work_items(ids: list):
    """
    Fetches Azure DevOps work items for the given list of IDs.
    This function splits the list of IDs into chunks of 200 to avoid API limits,
    and fetches each chunk in a separate request. All results are combined into a single list.
    Parameters:
        ids (list): List of work item IDs to fetch.
    Returns:
        list: List of work item dictionaries returned by the API, or an empty list on error.
    """
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
            else:
                print(f"Failed to fetch work items for chunk {ids_str}: {res.status_code}: {res.text}")
        return all_items
    except requests.RequestException as e:  
        raise Exception(f"Error fetching work items: {e}")

# Internal implementation for testing
def _get_burndown_tasks_impl(limit: int = 5, prioritize_parents: bool = True) -> str:
    """
    Fetches the next batch of tasks to burn down from Azure DevOps.
    """
    if limit <= 0: raise ValueError("Limit must be a positive integer")
    try:
        if not project_name:
            return "❌ Error: Could not extract project name from AZURE_DEVOPS_ORG_URL Expected format: https://dev.azure.com/org/project or https://org.visualstudio.com/project"
        
        project_filter = f"[System.TeamProject]='{project_name}'"
        tasks = []
        
        if prioritize_parents:
            # Fetch Top Parents
            pq = f"SELECT [System.Id] FROM WorkItems WHERE {project_filter} AND [System.State] NOT IN ('Closed','Removed','Resolved','Done','Completed') ORDER BY [Microsoft.VSTS.Common.Priority] ASC"
            parents = run_wiql(pq)
            if not isinstance(parents, list):
                print(f"Warning: run_wiql(pq) returned non-list: {parents}")
                parents = []
            seen_ids = set()  # Track what we've already added
            
            max_parents = min(len(parents), limit * 3)

            parent_ids = [p['id'] for i, p in enumerate(parents) if i < max_parents and p['id'] not in seen_ids]
            initial_len = len(tasks)
            if parent_ids:
                # Batch query for all children of these parents
                parent_ids_str = ",".join(str(pid) for pid in parent_ids)
                cq = f"SELECT [System.Id], [System.Parent] FROM WorkItems WHERE {project_filter} AND [System.Parent] IN ({parent_ids_str}) AND [System.State] NOT IN ('Closed','Removed','Resolved','Done','Completed')"
                children = run_wiql(cq)
                child_id_map = {}
                if children:
                    # Map parent id to its children
                    for c in children:
                        pid = c.get('parent') or c.get('System.Parent')
                        if pid:
                            child_id_map.setdefault(pid, []).append(c['id'])
                # For each parent, add children if any, else add parent itself
                for pid in parent_ids:
                    if len(tasks) >= limit:
                        break
                    if pid in child_id_map and child_id_map[pid]:
                        # Has children - add the children (they're bottom level)
                        child_items = get_work_items(child_id_map[pid])
                        for item in child_items:
                            if len(tasks) >= limit:
                                break
                            if item['id'] not in seen_ids:
                                tasks.append(item)
                                seen_ids.add(item['id'])
                    else:
                        # No children - parent itself is bottom level
                        parent_items = get_work_items([pid])
                        for item in parent_items:
                            if len(tasks) >= limit:
                                break
                            if item['id'] not in seen_ids:
                                tasks.append(item)
                                seen_ids.add(item['id'])
            # Track progress for batching
            tasks_added = (len(tasks) > initial_len)
        else:
            # Direct Query
            q = f"SELECT [System.Id] FROM WorkItems WHERE {project_filter} AND [System.State] NOT IN ('Closed','Removed','Resolved','Done','Completed') ORDER BY [Microsoft.VSTS.Common.Priority] ASC"
            refs = run_wiql(q)
            tasks.extend(get_work_items([r['id'] for r in refs[:limit]]))

        if not tasks:
            return f"✅ No active open tasks found in {project_name}. Backlog is clear!"

        output = f"## 🚀 Burndown Mission ({len(tasks[:limit])} items)\n"
        for t in tasks[:limit]:
            tid = t['id']
            title = t['fields'].get('System.Title', 'Unknown')
            wtype = t['fields'].get('System.WorkItemType', 'Item')
            output += f"- [ ] **{wtype} #{tid}**: {title}\n"
            
        return output

    except Exception as e:
        print(f"Unexpected error in _get_burndown_tasks_impl: {e}")
        raise Exception(f"❌ Error fetching tasks: {str(e)}")
    
@mcp.tool()
def get_burndown_tasks(limit: int = 5, prioritize_parents: bool = True) -> str:
    """
    Fetches the next batch of tasks to burn down from Azure DevOps.
    """
    return _get_burndown_tasks_impl(limit, prioritize_parents)

if __name__ == "__main__":
    mcp.run(transport="stdio")