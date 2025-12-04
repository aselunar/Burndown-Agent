
import os
import base64
import requests
from dotenv import load_dotenv
load_dotenv()

url = os.getenv("AZURE_DEVOPS_ORG_URL")
pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
auth = base64.b64encode(f":{pat}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

url_parts = url.rstrip('/').split('/')
base_url = '/'.join(url_parts[:4])
project = url_parts[4]
api_url = f"{base_url}/{project}/_apis/wit/wiql?api-version=6.0&$top=100"  # Add $top parameter

query = """
SELECT [System.Id] FROM WorkItems 
WHERE [System.State] NOT IN ('Closed','Removed','Resolved','Done','Completed') 
AND [System.WorkItemType] IN ('Task','Bug','User Story') 
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
"""

response = requests.post(api_url, headers=headers, json={"query": query})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    items = response.json().get("workItems", [])
    print(f"Found {len(items)} active work items")
    print(f"IDs: {[item['id'] for item in items]}")
else:
    print(f"Error: {response.text}")
