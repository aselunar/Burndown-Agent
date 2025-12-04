import os, base64, requests
from dotenv import load_dotenv
from burndown_server import extract_project_name
load_dotenv()

pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
auth = base64.b64encode(f":{pat}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
url = os.getenv("AZURE_DEVOPS_ORG_URL")

api_url = f"{url}/_apis/wit/wiql?api-version=6.0"

# Extract project from env or use default
project = extract_project_name(url) or "Burndown Agent"
query = {"query": f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject]='{project}'"}
response = requests.post(api_url, headers=headers, json=query)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")