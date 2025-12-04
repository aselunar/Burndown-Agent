import os
import base64
import requests
from dotenv import load_dotenv
load_dotenv()

url = os.getenv("AZURE_DEVOPS_ORG_URL")
pat = os.getenv("AZURE_DEVOPS_EXT_PAT")

print(f"URL: {url}")
print(f"PAT: {'***' if pat else 'MISSING'}")

if not url or not pat:
    print("ERROR: Missing credentials")
    exit(1)

auth = base64.b64encode(f":{pat}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

# Test connection
api_url = f"{url.rstrip('/')}/_apis/wit/wiql?api-version=6.0"
query = {"query": "SELECT [System.Id] FROM WorkItems"}

response = requests.post(api_url, headers=headers, json=query)
print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text[:500]}")
