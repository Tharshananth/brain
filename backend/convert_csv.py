"""
Export feedback.db to CSV file
Simple script to convert all feedback interactions to CSV format
"""
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path("data/database/feedback.db")

def export_to_csv(output_file="feedback_export.csv", include_test_records=False):
    """
    Export feedback database to CSV file
    
    Args:
        output_file: Name of CSV file to create
        include_test_records: If True, includes test records. If False, only real users
    """
    
    print("\n" + "=" * 80)
    print("EXPORTING FEEDBACK DATABASE TO CSV")
    print("=" * 80)
    
    # Check if database exists
    if not DB_PATH.exists():
        print(f"❌ ERROR: Database not found at {DB_PATH}")
        return False
    
    print(f"📂 Database: {DB_PATH.absolute()}")
    print(f"📄 Output CSV: {output_file}")
    print(f"🧪 Include test records: {include_test_records}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build query based on whether to include test records
        if include_test_records:
            query = """
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
            """
            print("\n📊 Exporting ALL records (including test records)...")
        else:
            query = """
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
                WHERE user_id NOT LIKE '%test%' 
                    AND user_id NOT LIKE '%verify%'
                    AND user_id NOT LIKE '%direct%'
                ORDER BY timestamp DESC
            """
            print("\n📊 Exporting REAL USER records only (excluding test records)...")
        
        # Execute query
        cursor.execute(query)
        
        # Get column names from cursor description
        columns = [description[0] for description in cursor.description]
        
        # Fetch all records
        records = cursor.fetchall()
        
        if not records:
            print("\n⚠️  No records found to export!")
            conn.close()
            return False
        
        print(f"\n✅ Found {len(records)} records")
        
        # Write to CSV
        print(f"\n📝 Writing to {output_file}...")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file)
            
            # Write header
            csv_writer.writerow(columns)
            
            # Write data rows
            csv_writer.writerows(records)
        
        # Get file size
        file_size = Path(output_file).stat().st_size / 1024  # KB
        
        print(f"✅ Export completed successfully!")
        print(f"\n📊 Export Summary:")
        print(f"   • Records exported: {len(records)}")
        print(f"   • Columns: {len(columns)}")
        print(f"   • File size: {file_size:.2f} KB")
        print(f"   • Output file: {Path(output_file).absolute()}")
        
        # Close connection
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ EXPORT SUCCESSFUL!")
        print("=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def export_with_stats(output_file="feedback_export_detailed.csv"):
    """
    Export with additional statistics in separate CSV
    """
    print("\n" + "=" * 80)
    print("EXPORTING WITH STATISTICS")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Get statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_messages,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT session_id) as unique_sessions,
                COUNT(CASE WHEN feedback_type = 'thumbs_up' THEN 1 END) as thumbs_up,
                COUNT(CASE WHEN feedback_type = 'thumbs_down' THEN 1 END) as thumbs_down,
                COUNT(CASE WHEN feedback_comment IS NOT NULL THEN 1 END) as with_comments,
                AVG(tokens_used) as avg_tokens,
                MIN(timestamp) as first_message,
                MAX(timestamp) as last_message
            FROM feedback_interactions
            WHERE user_id NOT LIKE '%test%'
        """
        
        cursor = conn.cursor()
        cursor.execute(stats_query)
        stats = cursor.fetchone()
        
        print(f"\n📊 Database Statistics:")
        print(f"   • Total messages: {stats[0]}")
        print(f"   • Unique users: {stats[1]}")
        print(f"   • Unique sessions: {stats[2]}")
        print(f"   • 👍 Thumbs up: {stats[3]}")
        print(f"   • 👎 Thumbs down: {stats[4]}")
        print(f"   • With comments: {stats[5]}")
        print(f"   • Average tokens: {stats[6]:.0f if stats[6] else 0}")
        print(f"   • First message: {stats[7]}")
        print(f"   • Last message: {stats[8]}")
        
        # Export main data
        export_success = export_to_csv(output_file, include_test_records=False)
        
        # Export stats to separate file
        if export_success:
            stats_file = output_file.replace('.csv', '_stats.csv')
            
            with open(stats_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Metric', 'Value'
                ])
                writer.writerow(['Total Messages', stats[0]])
                writer.writerow(['Unique Users', stats[1]])
                writer.writerow(['Unique Sessions', stats[2]])
                writer.writerow(['Thumbs Up', stats[3]])
                writer.writerow(['Thumbs Down', stats[4]])
                writer.writerow(['With Comments', stats[5]])
                writer.writerow(['Average Tokens', f"{stats[6]:.0f}" if stats[6] else "0"])
                writer.writerow(['First Message', stats[7]])
                writer.writerow(['Last Message', stats[8]])
            
            print(f"\n📊 Statistics saved to: {stats_file}")
        
        conn.close()
        return export_success
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    """Main function with menu"""
    print("\n" + "=" * 80)
    print("FEEDBACK DATABASE CSV EXPORTER")
    print("=" * 80)
    print("\nOptions:")
    print("  1. Export REAL messages only (recommended)")
    print("  2. Export ALL messages (including test records)")
    print("  3. Export with statistics")
    print("  4. Custom filename")
    print()
    
    choice = input("Select option (1-4) or press Enter for option 1: ").strip()
    
    if not choice:
        choice = "1"
    
    if choice == "1":
        export_to_csv("feedback_export.csv", include_test_records=False)
    
    elif choice == "2":
        export_to_csv("feedback_export_all.csv", include_test_records=True)
    
    elif choice == "3":
        export_with_stats("feedback_export_detailed.csv")
    
    elif choice == "4":
        filename = input("Enter CSV filename (e.g., my_export.csv): ").strip()
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        include_tests = input("Include test records? (y/n): ").strip().lower() == 'y'
        export_to_csv(filename, include_test_records=include_tests)
    
    else:
        print("Invalid opti" \
        "on. Using default (option 1)...")
        export_to_csv("feedback_export.csv", include_test_records=False)


if __name__ == "__main__":
    main()