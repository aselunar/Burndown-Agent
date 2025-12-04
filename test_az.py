import os, base64, requests
from dotenv import load_dotenv
load_dotenv()

pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
auth = base64.b64encode(f":{pat}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

api_url = "https://dev.azure.com/CropScience-1/Burndown%20Agent/_apis/wit/wiql?api-version=6.0"

query = {"query": "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject]='Burndown Agent'"}
response = requests.post(api_url, headers=headers, json=query)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")