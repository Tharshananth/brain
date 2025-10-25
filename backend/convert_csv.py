"""
Simple Database to CSV Converter
Directly converts feedback.db to CSV file
"""
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

# Paths
DB_PATH = Path("data/database/feedback.db")
OUTPUT_PATH = Path("feedback_export.csv")

def convert_db_to_csv():
    """Convert entire feedback database to CSV"""
    
    # Check if database exists
    if not DB_PATH.exists():
        print(f"❌ Error: Database not found at {DB_PATH}")
        print(f"   Make sure you're running this from the backend/ directory")
        return False
    
    try:
        print("🔄 Reading database...")
        
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all data from feedback_interactions table
        cursor.execute("""
            SELECT 
                id,
                user_id,
                session_id,
                message_id,
                timestamp,
                question,
                response,
                provider_used,
                tokens_used,
                feedback_type,
                feedback_comment,
                feedback_timestamp
            FROM feedback_interactions
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️  Database is empty - no data to export")
            conn.close()
            return False
        
        print(f"📊 Found {len(rows)} records")
        print("✍️  Writing to CSV...")
        
        # Write to CSV
        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header row
            writer.writerow([
                'ID',
                'User_ID',
                'Session_ID',
                'Message_ID',
                'Timestamp',
                'Question',
                'Response',
                'Provider_Used',
                'Tokens_Used',
                'Feedback_Type',
                'Feedback_Comment',
                'Feedback_Timestamp'
            ])
            
            # Write all data rows
            writer.writerows(rows)
        
        conn.close()
        
        # Show success message
        file_size = OUTPUT_PATH.stat().st_size / 1024
        print("\n✅ SUCCESS!")
        print("=" * 60)
        print(f"📁 File: {OUTPUT_PATH.absolute()}")
        print(f"📊 Records: {len(rows)}")
        print(f"💾 Size: {file_size:.2f} KB")
        print("=" * 60)
        
        # Show quick stats
        with_feedback = sum(1 for row in rows if row[9] is not None)  # feedback_type column
        thumbs_up = sum(1 for row in rows if row[9] == 'thumbs_up')
        thumbs_down = sum(1 for row in rows if row[9] == 'thumbs_down')
        
        print("\n📈 Quick Stats:")
        print(f"   Total interactions: {len(rows)}")
        print(f"   With feedback: {with_feedback}")
        print(f"   👍 Thumbs up: {thumbs_up}")
        print(f"   👎 Thumbs down: {thumbs_down}")
        
        if with_feedback > 0:
            satisfaction = (thumbs_up / with_feedback) * 100
            print(f"   😊 Satisfaction: {satisfaction:.1f}%")
        
        print("\n✨ Done! Open feedback_export.csv to view your data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during export: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FEEDBACK DATABASE → CSV CONVERTER")
    print("=" * 60 + "\n")
    
    convert_db_to_csv()