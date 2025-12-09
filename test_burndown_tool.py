# Manual integration test for burndown_server. Requires .env file with environment variables (can be created by running setup.py).
# Sometimes you need to test the mcp logic outside of the MCP server context.
import sys
sys.path.insert(0, '.')

# Requires AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_EXT_PAT to be set in a .env file. Run `python3 setup.py` to configure.
from burndown_server import _get_burndown_tasks_impl

print("=== Testing without prioritize_parents ===")
try:
    result = _get_burndown_tasks_impl(limit=10, prioritize_parents=False)
    print(result)
except Exception as e:
    print(f"Error: {e}")
print("\n=== Testing with prioritize_parents ===")
try:
    result = _get_burndown_tasks_impl(limit=5, prioritize_parents=True)
    print(result)
except Exception as e:
    print(f"Error: {e}")