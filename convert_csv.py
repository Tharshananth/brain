import sqlite3
import csv
from pathlib import Path
from datetime import datetime

DB_PATH = Path("C:\\Users\\tharshananth N\\brainsightAI\\feedback.db")
OUTPUT_DIR = Path("exports")
OUTPUT_DIR.mkdir(exist_ok=True)

def export_to_csv():
    """Export feedback database to CSV"""
    if not DB_PATH.exists():
        print("❌ Database not found!")
        return
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = OUTPUT_DIR / f"feedback_data_{timestamp}.csv"
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all data
    cursor.execute("SELECT * FROM feedback_interactions ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    
    # Get column names
    cursor.execute("PRAGMA table_info(feedback_interactions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Write to CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)  # Header
        writer.writerows(rows)     # Data
    
    conn.close()
    
    print(f"✅ Exported {len(rows)} records to: {csv_file}")
    print(f"📊 Columns: {', '.join(columns)}")
    return csv_file

if __name__ == "__main__":
    export_to_csv()