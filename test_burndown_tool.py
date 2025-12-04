import sys
sys.path.insert(0, '.')  # Or sys.path.insert(0, '.roo') if testing installed version

from burndown_server import _get_burndown_tasks_impl

print("=== Testing without prioritize_parents ===")
result = _get_burndown_tasks_impl(limit=10, prioritize_parents=False)
print(result)

print("\n=== Testing with prioritize_parents ===")
result = _get_burndown_tasks_impl(limit=5, prioritize_parents=True)
print(result)