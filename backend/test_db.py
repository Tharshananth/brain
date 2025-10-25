"""
Feedback Database Verification Tool
Comprehensive checker for feedback.db database
Shows exactly what's stored and helps debug save issues
"""
import sqlite3
from pathlib import Path
from datetime import datetime
import sys

DB_PATH = Path("data/database/feedback.db")

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80 + "\n")

def print_section(text):
    """Print section divider"""
    print("\n" + "-" * 80)
    print(text)
    print("-" * 80)

def check_file_exists():
    """Check if database file exists"""
    print_section("1. DATABASE FILE CHECK")
    
    if not DB_PATH.exists():
        print("❌ CRITICAL: Database file does NOT exist!")
        print(f"   Expected location: {DB_PATH.absolute()}")
        print("\n🔧 Fix this by:")
        print("   1. Run: cd backend && python main.py")
        print("   2. The database will be created automatically")
        return False
    
    print(f"✅ Database file exists")
    print(f"   Location: {DB_PATH.absolute()}")
    
    # File size
    size_bytes = DB_PATH.stat().st_size
    size_kb = size_bytes / 1024
    print(f"   Size: {size_kb:.2f} KB ({size_bytes:,} bytes)")
    
    # Last modified
    mtime = datetime.fromtimestamp(DB_PATH.stat().st_mtime)
    print(f"   Last modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

def check_table_exists():
    """Check if feedback_interactions table exists"""
    print_section("2. TABLE STRUCTURE CHECK")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='feedback_interactions'
        """)
        
        if not cursor.fetchone():
            print("❌ CRITICAL: Table 'feedback_interactions' does NOT exist!")
            print("\n🔧 Fix this by running database migration")
            conn.close()
            return False
        
        print("✅ Table 'feedback_interactions' exists")
        
        # Get columns
        cursor.execute("PRAGMA table_info(feedback_interactions)")
        columns = cursor.fetchall()
        
        print(f"\n📋 Table has {len(columns)} columns:")
        print(f"\n{'Column Name':<25} {'Type':<15} {'Nullable':<10} {'Primary Key'}")
        print("-" * 75)
        
        for col in columns:
            col_id, name, col_type, not_null, default, pk = col
            nullable = "NOT NULL" if not_null else "NULL"
            is_pk = "✓" if pk else ""
            print(f"{name:<25} {col_type:<15} {nullable:<10} {is_pk}")
        
        # Check indexes
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='index' AND tbl_name='feedback_interactions'
        """)
        indexes = cursor.fetchall()
        
        if indexes:
            print(f"\n📌 Indexes ({len(indexes)}):")
            for idx_name, idx_sql in indexes:
                print(f"   • {idx_name}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False

def count_all_records():
    """Count and categorize all records"""
    print_section("3. RECORD COUNT & CATEGORIZATION")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM feedback_interactions")
        total = cursor.fetchone()[0]
        
        print(f"📊 TOTAL RECORDS: {total}")
        
        if total == 0:
            print("\n⚠️  DATABASE IS EMPTY!")
            print("\n💡 This means NO data has been saved yet.")
            print("   Possible reasons:")
            print("   1. No chat messages sent through frontend")
            print("   2. Backend not saving data (check logs)")
            print("   3. Database save code has errors")
            conn.close()
            return 0, 0, 0
        
        # Categorize by user_id patterns
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                CASE 
                    WHEN user_id LIKE '%test%' THEN 'Test Records'
                    WHEN user_id LIKE '%verify%' THEN 'Verification Records'
                    WHEN user_id = 'anonymous' THEN 'Anonymous Users'
                    ELSE 'Real Users'
                END as category
            FROM feedback_interactions
            GROUP BY category
        """)
        
        categories = cursor.fetchall()
        
        print("\n📈 Records by Category:")
        test_count = 0
        real_count = 0
        
        for count, category in categories:
            icon = "🧪" if "Test" in category else "✅" if "Real" in category else "👤" if "Anonymous" in category else "🔍"
            print(f"   {icon} {category}: {count}")
            
            if "Test" in category or "Verification" in category:
                test_count += count
            else:
                real_count += count
        
        # Records with feedback
        cursor.execute("""
            SELECT COUNT(*) FROM feedback_interactions 
            WHERE feedback_type IS NOT NULL
        """)
        with_feedback = cursor.fetchone()[0]
        
        print(f"\n💬 Records with feedback: {with_feedback} ({with_feedback/total*100:.1f}%)")
        
        conn.close()
        return total, test_count, real_count
        
    except Exception as e:
        print(f"❌ Error counting records: {e}")
        return 0, 0, 0

def show_all_records():
    """Show ALL records in database"""
    print_section("4. ALL RECORDS (Complete List)")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                message_id,
                user_id,
                timestamp,
                question,
                response,
                provider_used,
                tokens_used,
                feedback_type
            FROM feedback_interactions
            ORDER BY timestamp DESC
        """)
        
        records = cursor.fetchall()
        
        if not records:
            print("⚠️  No records to display")
            conn.close()
            return
        
        for i, record in enumerate(records, 1):
            msg_id, user_id, timestamp, question, response, provider, tokens, feedback = record
            
            # Determine record type
            if 'test' in user_id.lower() or 'verify' in user_id.lower():
                record_type = "🧪 TEST"
            elif user_id == 'anonymous':
                record_type = "👤 ANONYMOUS"
            else:
                record_type = "✅ REAL"
            
            print(f"\n{record_type} Record #{i}")
            print("-" * 80)
            print(f"🆔 Message ID:  {msg_id}")
            print(f"👤 User ID:     {user_id}")
            print(f"📅 Timestamp:   {timestamp}")
            print(f"❓ Question:    {question[:70]}{'...' if len(question) > 70 else ''}")
            print(f"💬 Response:    {response[:70]}{'...' if len(response) > 70 else ''}")
            print(f"🤖 Provider:    {provider or 'N/A'}")
            print(f"🎫 Tokens:      {tokens or 'N/A'}")
            print(f"👍/👎 Feedback:  {feedback or 'None'}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing records: {e}")

def show_recent_real_messages():
    """Show only recent REAL (non-test) messages"""
    print_section("5. RECENT REAL CHAT MESSAGES")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                message_id,
                user_id,
                timestamp,
                question,
                response,
                provider_used,
                feedback_type
            FROM feedback_interactions
            WHERE user_id NOT LIKE '%test%' 
                AND user_id NOT LIKE '%verify%'
                AND user_id NOT LIKE '%direct%'
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        records = cursor.fetchall()
        
        if not records:
            print("⚠️  NO REAL CHAT MESSAGES FOUND!")
            print("\n❌ This is the problem!")
            print("\n💡 What this means:")
            print("   • Test records are being saved (backend works)")
            print("   • BUT real chat messages from frontend are NOT being saved")
            print("\n🔧 Troubleshooting steps:")
            print("   1. Check if user_id is being sent from frontend")
            print("   2. Check backend logs when you send a chat message")
            print("   3. Look for database save errors in logs")
            print("   4. Verify the fixed chat.py is being used")
        else:
            print(f"✅ Found {len(records)} real chat messages:\n")
            
            for i, record in enumerate(records, 1):
                msg_id, user_id, timestamp, question, response, provider, feedback = record
                
                print(f"Message #{i}")
                print(f"   🆔 ID: {msg_id}")
                print(f"   👤 User: {user_id}")
                print(f"   📅 Time: {timestamp}")
                print(f"   ❓ Q: {question[:60]}...")
                print(f"   💬 A: {response[:60]}...")
                print(f"   👍/👎: {feedback or 'No feedback yet'}")
                print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def show_feedback_statistics():
    """Show feedback statistics"""
    print_section("6. FEEDBACK STATISTICS")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN feedback_type = 'thumbs_up' THEN 1 END) as thumbs_up,
                COUNT(CASE WHEN feedback_type = 'thumbs_down' THEN 1 END) as thumbs_down,
                COUNT(CASE WHEN feedback_type IS NULL THEN 1 END) as no_feedback,
                COUNT(CASE WHEN feedback_comment IS NOT NULL THEN 1 END) as with_comments
            FROM feedback_interactions
            WHERE user_id NOT LIKE '%test%'
        """)
        
        stats = cursor.fetchone()
        total, up, down, none, comments = stats
        
        if total == 0:
            print("⚠️  No real messages to analyze")
            conn.close()
            return
        
        print(f"📊 Feedback Summary (Real Messages Only):")
        print(f"\n   Total messages: {total}")
        print(f"   👍 Thumbs up: {up} ({up/total*100:.1f}%)")
        print(f"   👎 Thumbs down: {down} ({down/total*100:.1f}%)")
        print(f"   ⏸️  No feedback: {none} ({none/total*100:.1f}%)")
        print(f"   💬 With comments: {comments}")
        
        if up + down > 0:
            satisfaction = (up / (up + down)) * 100
            print(f"\n   😊 Satisfaction Rate: {satisfaction:.1f}%")
        
        # Provider breakdown
        cursor.execute("""
            SELECT provider_used, COUNT(*) as count
            FROM feedback_interactions
            WHERE user_id NOT LIKE '%test%'
                AND provider_used IS NOT NULL
            GROUP BY provider_used
            ORDER BY count DESC
        """)
        
        providers = cursor.fetchall()
        
        if providers:
            print(f"\n🤖 Messages by Provider:")
            for provider, count in providers:
                print(f"   • {provider}: {count} ({count/total*100:.1f}%)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def search_by_message_id(message_id):
    """Search for a specific message by ID"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM feedback_interactions
            WHERE message_id = ?
        """, (message_id,))
        
        record = cursor.fetchone()
        conn.close()
        
        return record is not None
        
    except Exception as e:
        print(f"❌ Error searching: {e}")
        return False

def check_specific_message():
    """Check if a specific message exists"""
    print_section("7. SEARCH FOR SPECIFIC MESSAGE")
    
    print("Enter a message_id to search (or press Enter to skip):")
    message_id = input("Message ID: ").strip()
    
    if not message_id:
        print("⏭️  Skipped")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
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
                feedback_comment
            FROM feedback_interactions
            WHERE message_id = ?
        """, (message_id,))
        
        record = cursor.fetchone()
        
        if record:
            print(f"\n✅ FOUND!")
            print("-" * 80)
            print(f"ID:              {record[0]}")
            print(f"User ID:         {record[1]}")
            print(f"Session ID:      {record[2]}")
            print(f"Message ID:      {record[3]}")
            print(f"Timestamp:       {record[4]}")
            print(f"Question:        {record[5][:100]}...")
            print(f"Response:        {record[6][:100]}...")
            print(f"Provider:        {record[7]}")
            print(f"Tokens:          {record[8]}")
            print(f"Feedback Type:   {record[9]}")
            print(f"Feedback Comment: {record[10]}")
        else:
            print(f"\n❌ NOT FOUND!")
            print(f"   Message ID '{message_id}' does not exist in database")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def export_to_csv_summary():
    """Show export information"""
    print_section("8. DATA EXPORT OPTIONS")
    
    print("📁 You can export this data to CSV:")
    print("\n   Option 1: Simple export")
    print("   Command: python convert_csv.py")
    print("   Output:  feedback_export.csv")
    print("\n   Option 2: Check first")
    print("   Command: python check_database.py")
    print("\n   The CSV will contain all fields including:")
    print("   • All questions and responses")
    print("   • User IDs and session IDs")
    print("   • Timestamps")
    print("   • Feedback data")
    print("   • Provider and token information")

def main():
    """Run complete verification"""
    print_header("FEEDBACK DATABASE VERIFICATION TOOL")
    print(f"⏰ Verification Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💾 Database Path: {DB_PATH.absolute()}")
    
    # Run all checks
    if not check_file_exists():
        print("\n❌ CRITICAL ERROR: Database file missing!")
        print("Cannot continue verification.")
        return
    
    if not check_table_exists():
        print("\n❌ CRITICAL ERROR: Table structure missing!")
        print("Cannot continue verification.")
        return
    
    total, test_count, real_count = count_all_records()
    
    show_all_records()
    show_recent_real_messages()
    show_feedback_statistics()
    check_specific_message()
    export_to_csv_summary()
    
    # Final summary
    print_header("FINAL VERDICT")
    
    if real_count > 0:
        print("✅✅✅ SUCCESS! Real chat messages ARE being saved!")
        print(f"\n📊 Summary:")
        print(f"   • Total records: {total}")
        print(f"   • Real messages: {real_count}")
        print(f"   • Test records: {test_count}")
        print(f"\n✨ Your database is working correctly!")
        print(f"   Run 'python convert_csv.py' to export to CSV")
        
    elif test_count > 0:
        print("⚠️  DATABASE WORKS BUT NO REAL MESSAGES")
        print(f"\n📊 Summary:")
        print(f"   • Total records: {total}")
        print(f"   • Test records: {test_count}")
        print(f"   • Real messages: {real_count} ❌")
        print(f"\n🔧 This means:")
        print(f"   ✅ Database structure works")
        print(f"   ✅ Test writes work")
        print(f"   ❌ Frontend messages not being saved")
        print(f"\n💡 Next steps:")
        print(f"   1. Replace chat.py with fixed version")
        print(f"   2. Restart backend")
        print(f"   3. Send a test message from frontend")
        print(f"   4. Check backend logs for save confirmation")
        
    else:
        print("❌ DATABASE IS EMPTY")
        print(f"\n📊 Summary:")
        print(f"   • Total records: 0")
        print(f"\n🔧 This means:")
        print(f"   • Database exists but nothing saved yet")
        print(f"\n💡 Next steps:")
        print(f"   1. Make sure backend is running")
        print(f"   2. Send messages through frontend")
        print(f"   3. Check backend logs for errors")
    
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    main()

    