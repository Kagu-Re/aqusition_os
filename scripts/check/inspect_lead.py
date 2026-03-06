import sqlite3
import json

def inspect_lead():
    conn = sqlite3.connect("d:/aqusition_os/acq.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM lead_intake WHERE lead_id = 87")
    row = cur.fetchone()
    if row:
        # Get column names
        col_names = [description[0] for description in cur.description]
        data = dict(zip(col_names, row))
        print(json.dumps(data, indent=2, default=str))
    else:
        print("Lead 87 not found")
    conn.close()

if __name__ == "__main__":
    inspect_lead()
