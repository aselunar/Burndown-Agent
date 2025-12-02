#!/bin/sh

echo "⬇️  Attempting to download setup.py from host..."

# 1. Download: Removed '-s' to show errors. Added fail check.
# We try to fetch setup.py. If it fails, we exit.
if curl -L "http://host.docker.internal:8000/setup.py" -o setup.py; then
    
    # Check if the file is empty or looks like a 404 error
    if [ ! -s setup.py ] || grep -q "Error code 404" setup.py; then
        echo "❌ Error: Downloaded file is empty or 404 Not Found."
        echo "   -> Verify 'setup.py' exists in the folder where you ran 'python3 -m http.server'"
        rm setup.py
        exit 1
    fi

    echo "✅ Download successful. Running setup..."
    
    # 2. Run: '< /dev/tty' forces Python to read from your keyboard
    python3 setup.py < /dev/tty
    
    # 3. Cleanup
    rm setup.py
else
    echo "❌ Download failed."
    echo "   -> Is the server running? (python3 -m http.server 8000)"
    echo "   -> Can the container reach 'host.docker.internal'?"
    exit 1
fi
