"""
Migration script to add user_id column to existing database
Run this ONCE if you already have a database without user_id column
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/database/feedback.db")

def migrate():
    """Add user_id column to existing database"""
    if not DB_PATH.exists():
        print("No existing database found. Migration not needed.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(feedback_interactions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_id' in columns:
            print("✅ user_id column already exists. No migration needed.")
            return
        
        # Add user_id column with default value
        print("Adding user_id column...")
        cursor.execute("""
            ALTER TABLE feedback_interactions 
            ADD COLUMN user_id TEXT NOT NULL DEFAULT 'legacy_user'
        """)
        
        # Create index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id 
            ON feedback_interactions(user_id)
        """)
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()