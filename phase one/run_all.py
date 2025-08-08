import subprocess
import sys

# Change to your virtualenv Python if needed
PYTHON = sys.executable

steps = [
    [PYTHON, "schema_parcels.py"],
    [PYTHON, "etl_kent_mi.py", "--db", "contacts.db", "--max_pages", "999"],
    [PYTHON, "etl_ottawa_mi.py", "--db", "contacts.db", "--pagesize", "2000", "--max_pages", "999"],
    [PYTHON, "app.py"]
]

for step in steps:
    print(f"\n🚀 Running: {' '.join(step)}")
    result = subprocess.run(step)
    if result.returncode != 0:
        print(f"❌ Step failed: {' '.join(step)}")
        sys.exit(result.returncode)
