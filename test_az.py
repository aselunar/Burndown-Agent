import os
import base64
import requests
from dotenv import load_dotenv
load_dotenv()

url = os.getenv("AZURE_DEVOPS_ORG_URL")
pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
auth = base64.b64encode(f":{pat}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

# Extract project from URL
url_parts = url.rstrip('/').split('/')
print(f"URL parts: {url_parts}")

if len(url_parts) >= 5:
    base_url = '/'.join(url_parts[:4])
    project = url_parts[4]
    api_url = f"{base_url}/{project}/_apis/wit/wiql?api-version=6.0"
    print(f"Using project-scoped endpoint: {api_url}")
else:
    print("No project in URL - would query all projects")
    exit(1)

query = """
SELECT [System.Id] FROM WorkItems 
WHERE [System.State] NOT IN ('Closed','Removed','Resolved','Done','Completed') 
AND [System.WorkItemType] IN ('Task','Bug','User Story') 
"""

response = requests.post(api_url, headers=headers, json={"query": query})
print(f"\nStatus: {response.status_code}")
if response.status_code == 200:
    items = response.json().get("workItems", [])
    print(f"Found {len(items)} active work items in project '{project}'")
    print(f"Items: {items}")
else:
    print(f"Error: {response.text}")