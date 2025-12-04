import os, base64, requests
from dotenv import load_dotenv
import urllib.parse
load_dotenv()

pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
auth = base64.b64encode(f":{pat}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
org_url = os.getenv("AZURE_DEVOPS_ORG_URL") or os.getenv("AZURE_DEVOPS_SCOPE")
project = os.getenv("AZURE_DEVOPS_PROJECT")
project_encoded = urllib.parse.quote(project) if project else ""
api_url = f"{org_url}/{project_encoded}/_apis/wit/wiql?api-version=6.0"
query = {"query": f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject]='{project}'"}

response = requests.post(api_url, headers=headers, json=query)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")