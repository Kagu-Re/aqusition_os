#!/usr/bin/env python3
"""Migrate clients table to add business_model and service_config_json columns."""

import sqlite3
import os

# Determine database path
db_path = 'acq.db' if os.path.exists('acq.db') else 'data/acq.db'

if not os.path.exists(db_path):
    print(f"Database not found: {db_path}")
    print("Creating new database with updated schema...")
    # If database doesn't exist, init_db will create it with the new schema
    from ae import db as dbmod
    dbmod.init_db(db_path)
    print("[OK] Database created with new schema")
else:
    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    
    try:
        # Check if columns exist
        cur = conn.execute('PRAGMA table_info(clients)')
        columns = [row[1] for row in cur.fetchall()]
        
        if 'business_model' not in columns:
            conn.execute('ALTER TABLE clients ADD COLUMN business_model TEXT NOT NULL DEFAULT "quote_based"')
            print("[OK] Added business_model column")
        else:
            print("  business_model column already exists")
        
        if 'service_config_json' not in columns:
            conn.execute('ALTER TABLE clients ADD COLUMN service_config_json TEXT NOT NULL DEFAULT "{}"')
            print("[OK] Added service_config_json column")
        else:
            print("  service_config_json column already exists")
        
        conn.commit()
        print("[OK] Migration complete")
    except Exception as e:
        print(f"[ERROR] Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()
