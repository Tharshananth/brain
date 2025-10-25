"""
Database Migration Script - Add user_id column
Run this once to update existing database
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/database/feedback.db")

def migrate_database():
    """Add user_id column to existing database"""
    if not DB_PATH.exists():
        print("❌ Database not found")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user_id column exists
        cursor.execute("PRAGMA table_info(feedback_interactions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' in columns:
            print("✅ user_id column already exists")
        else:
            print("Adding user_id column...")
            cursor.execute("""
                ALTER TABLE feedback_interactions 
                ADD COLUMN user_id STRING NOT NULL DEFAULT 'anonymous'
            """)
            
            # Create index for user_id
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id 
                ON feedback_interactions(user_id)
            """)
            
            conn.commit()
            print("✅ Migration complete!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    migrate_database()