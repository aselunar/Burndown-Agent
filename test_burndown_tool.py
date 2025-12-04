import sys
sys.path.insert(0, '.')  # Or sys.path.insert(0, '.roo') if testing installed version

from burndown_server import get_burndown_tasks

print("=== Testing without prioritize_parents ===")
result = get_burndown_tasks(limit=10, prioritize_parents=False)
print(result)

print("\n=== Testing with prioritize_parents ===")
result = get_burndown_tasks(limit=5, prioritize_parents=True)
print(result)