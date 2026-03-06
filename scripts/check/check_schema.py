import sqlite3
import os

def check_schema():
    db_path = "d:/aqusition_os/acq.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    tables = ["customers", "bookings", "booking_events"]
    print("Checking for new tables...")
    for table in tables:
        try:
            cur.execute(f"SELECT count(*) FROM {table}")
            print(f"[OK] Table '{table}' exists.")
            
            # Print columns
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            print(f"  Columns: {', '.join(cols)}")
            
        except sqlite3.OperationalError:
            print(f"[MISSING] Table '{table}' does NOT exist.")
            
    conn.close()

if __name__ == "__main__":
    check_schema()
