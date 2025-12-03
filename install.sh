#!/bin/sh

# 1. Define the target in /tmp (Invisible to your project)
TARGET="/tmp/setup.py"

# 2. Define a Cleanup Function (The Trap)
cleanup() {
    rm -f "$TARGET"
}

# 3. Set the Trap: Run 'cleanup' on EXIT, Ctrl+C (INT), or Kill (TERM)
trap cleanup EXIT INT TERM

echo "⬇️  Downloading agent to $TARGET..."

# 4. Download
if curl -L "http://host.docker.internal:8000/setup.py" -o "$TARGET"; then
    
    # Validation
    if [ ! -s "$TARGET" ] || grep -q "Error code 404" "$TARGET"; then
        echo "❌ Error: Download failed (404 or empty)."
        exit 1 # The trap will auto-run rm here
    fi

    echo "✅ Download successful. Running setup..."
    
    # 5. Run Python (Reading from keyboard)
    # Even if you Ctrl+C here, the 'trap' above ensures cleanup runs.
    python3 "$TARGET" < /dev/tty

else
    echo "❌ Download failed."
    exit 1
fi