#!/bin/sh

# 1. Download: Save to a file so Python can read from keyboard (stdin)
curl -sL "[http://host.docker.internal:8000/setup.py](http://host.docker.internal:8000/setup.py)" -o setup.py

# 2. Run: '< /dev/tty' forces Python to read from your keyboard, not the curl pipe
python3 setup.py < /dev/tty

# 3. Cleanup: Delete the file to leave no trace
rm setup.py
