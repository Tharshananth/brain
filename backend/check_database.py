"""
Quick Database Check Script
Verifies database status and shows recent entries
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/database/feedback.db")

def check_database():
    """Check database status and show recent entries"""
    
    print("\n" + "=" * 60)
    print("DATABASE STATUS CHECK")
    print("=" * 60 + "\n")
    
    # Check if database file exists
    if not DB_PATH.exists():
        print("❌ Database file not found!")
        print(f"   Expected location: {DB_PATH.absolute()}")
        print("\n💡 Tip: Make sure your backend is running and has created the database")
        return
    
    print(f"✅ Database file found: {DB_PATH}")
    print(f"📦 File size: {DB_PATH.stat().st_size / 1024:.2f} KB\n")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='feedback_interactions'
        """)
        
        if not cursor.fetchone():
            print("❌ Table 'feedback_interactions' not found!")
            print("   Database exists but table is missing")
            return
        
        print("✅ Table 'feedback_interactions' found\n")
        
        # Get table structure
        cursor.execute("PRAGMA table_info(feedback_interactions)")
        columns = cursor.fetchall()
        
        print("📋 Table Structure:")
        print("-" * 60)
        for col in columns:
            print(f"   {col[1]:20s} {col[2]:15s} {'NOT NULL' if col[3] else ''}")
        
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM feedback_interactions")
        total = cursor.fetchone()[0]
        
        print("\n" + "=" * 60)
        print(f"📊 TOTAL RECORDS: {total}")
        print("=" * 60 + "\n")
        
        if total == 0:
            print("⚠️  Database is EMPTY - No interactions recorded yet")
            print("\n💡 To add data:")
            print("   1. Make sure your backend is running")
            print("   2. Open the frontend (Streamlit)")
            print("   3. Send a chat message")
            print("   4. The interaction will be saved automatically")
            conn.close()
            return
        
        # Get recent entries
        cursor.execute("""
            SELECT 
                message_id,
                user_id,
                timestamp,
                question,
                feedback_type,
                provider_used
            FROM feedback_interactions
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        
        recent = cursor.fetchall()
        
        print("📝 RECENT ENTRIES (Last 5):")
        print("=" * 60)
        
        for i, row in enumerate(recent, 1):
            msg_id, user_id, timestamp, question, feedback, provider = row
            
            print(f"\n{i}. Message ID: {msg_id}")
            print(f"   User: {user_id}")
            print(f"   Time: {timestamp}")
            print(f"   Question: {question[:80]}{'...' if len(question) > 80 else ''}")
            print(f"   Feedback: {feedback or 'No feedback yet'}")
            print(f"   Provider: {provider}")
        
        # Get feedback stats
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN feedback_type = 'thumbs_up' THEN 1 END) as thumbs_up,
                COUNT(CASE WHEN feedback_type = 'thumbs_down' THEN 1 END) as thumbs_down,
                COUNT(CASE WHEN feedback_type IS NULL THEN 1 END) as no_feedback
            FROM feedback_interactions
        """)
        
        stats = cursor.fetchone()
        
        print("\n" + "=" * 60)
        print("📈 FEEDBACK STATISTICS:")
        print("=" * 60)
        print(f"   👍 Thumbs Up:     {stats[0]}")
        print(f"   👎 Thumbs Down:   {stats[1]}")
        print(f"   ⏸️  No Feedback:   {stats[2]}")
        
        total_feedback = stats[0] + stats[1]
        if total_feedback > 0:
            satisfaction = (stats[0] / total_feedback) * 100
            print(f"   😊 Satisfaction:  {satisfaction:.1f}%")
        
        conn.close()
        
        print("\n✅ Database is healthy and ready to export!")
        print(f"\n💡 Run: python export_db_to_csv.py to export to CSV\n")
        
    except Exception as e:
        print(f"\n❌ Error checking database: {e}")


if __name__ == "__main__":
    check_database()