import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))
from ae.db import init_db

if __name__ == "__main__":
    db_path = "d:/aqusition_os/acq.db"
    print(f"Applying migrations to {db_path}...")
    init_db(db_path)
    print("Done.")
