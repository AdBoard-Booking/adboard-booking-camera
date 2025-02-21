import os
import subprocess
import sys

# Get the base directory (assumes script is inside the project folder)
base_dir = os.path.dirname(os.path.abspath(__file__))

# Set Python path dynamically
python_path = sys.executable  # Uses the Python running this script

# Define the script path relative to the project directory
script_path = os.path.join(base_dir, "..", "billboardMonitoring", "monitoring.py")

# Run the script
subprocess.run([
    python_path, script_path,
    "--publish", "1",
    "--verbose", "0"
], check=True)
