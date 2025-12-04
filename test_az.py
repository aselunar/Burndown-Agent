import os, base64, requests
from dotenv import load_dotenv
load_dotenv()

pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
auth = base64.b64encode(f":{pat}".encode()).decode()
headers = {"Authorization": f"Basic {auth}"}

# List all projects
url = "https://dev.azure.com/CropScience-1/_apis/projects?api-version=6.0"
response = requests.get(url, headers=headers)
print(response.json())