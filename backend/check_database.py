"""
Complete Verification Script
Checks if chat messages are being saved to database
"""
import sys
from pathlib import Path
import sqlite3
from datetime import datetime
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70 + "\n")

def print_section(text):
    """Print section header"""
    print("\n" + "-" * 70)
    print(text)
    print("-" * 70)

def check_database_file():
    """Check if database file exists"""
    print_section("STEP 1: Database File Check")
    
    DB_PATH = Path("data/database/feedback.db")
    
    if not DB_PATH.exists():
        print("❌ Database file NOT found!")
        print(f"   Expected: {DB_PATH.absolute()}")
        return False
    
    print(f"✅ Database file exists: {DB_PATH}")
    size_kb = DB_PATH.stat().st_size / 1024
    print(f"   Size: {size_kb:.2f} KB")
    print(f"   Path: {DB_PATH.absolute()}")
    return True

def check_table_structure():
    """Check if table exists and has correct structure"""
    print_section("STEP 2: Table Structure Check")
    
    DB_PATH = Path("data/database/feedback.db")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='feedback_interactions'
        """)
        
        if not cursor.fetchone():
            print("❌ Table 'feedback_interactions' NOT found!")
            conn.close()
            return False
        
        print("✅ Table 'feedback_interactions' exists")
        
        # Get table structure
        cursor.execute("PRAGMA table_info(feedback_interactions)")
        columns = cursor.fetchall()
        
        print("\n📋 Table Columns:")
        required_columns = {
            'id', 'user_id', 'session_id', 'message_id', 
            'timestamp', 'question', 'response', 'provider_used',
            'tokens_used', 'feedback_type', 'feedback_comment', 
            'feedback_timestamp'
        }
        
        found_columns = set()
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            print(f"   ✓ {col_name:20s} ({col_type})")
            found_columns.add(col_name)
        
        missing = required_columns - found_columns
        if missing:
            print(f"\n⚠️  Missing columns: {missing}")
        else:
            print("\n✅ All required columns present")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False

def count_records():
    """Count total records"""
    print_section("STEP 3: Record Count")
    
    DB_PATH = Path("data/database/feedback.db")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM feedback_interactions")
        total = cursor.fetchone()[0]
        
        print(f"📊 Total Records: {total}")
        
        # Test records vs real records
        cursor.execute("""
            SELECT COUNT(*) FROM feedback_interactions 
            WHERE user_id LIKE '%test%'
        """)
        test_count = cursor.fetchone()[0]
        
        real_count = total - test_count
        
        print(f"   🧪 Test records: {test_count}")
        print(f"   💬 Real chat messages: {real_count}")
        
        conn.close()
        return total, real_count
        
    except Exception as e:
        print(f"❌ Error counting records: {e}")
        return 0, 0

def show_recent_records():
    """Show recent records"""
    print_section("STEP 4: Recent Records")
    
    DB_PATH = Path("data/database/feedback.db")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get recent non-test records
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
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        
        records = cursor.fetchall()
        
        if not records:
            print("⚠️  No real chat messages found!")
            print("\n💡 This means:")
            print("   1. Either no messages have been sent through the frontend")
            print("   2. Or messages are not being saved to the database")
        else:
            print(f"📝 Last {len(records)} real chat messages:\n")
            
            for i, record in enumerate(records, 1):
                msg_id, user_id, timestamp, question, response, provider, feedback = record
                
                print(f"{i}. Message ID: {msg_id}")
                print(f"   User: {user_id}")
                print(f"   Time: {timestamp}")
                print(f"   Question: {question[:60]}{'...' if len(question) > 60 else ''}")
                print(f"   Response: {response[:60]}{'...' if len(response) > 60 else ''}")
                print(f"   Provider: {provider}")
                print(f"   Feedback: {feedback or 'None'}")
                print()
        
        conn.close()
        return len(records)
        
    except Exception as e:
        print(f"❌ Error showing records: {e}")
        return 0

def show_feedback_stats():
    """Show feedback statistics"""
    print_section("STEP 5: Feedback Statistics")
    
    DB_PATH = Path("data/database/feedback.db")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get feedback stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN feedback_type = 'thumbs_up' THEN 1 END) as thumbs_up,
                COUNT(CASE WHEN feedback_type = 'thumbs_down' THEN 1 END) as thumbs_down,
                COUNT(CASE WHEN feedback_type IS NULL THEN 1 END) as no_feedback
            FROM feedback_interactions
            WHERE user_id NOT LIKE '%test%'
        """)
        
        stats = cursor.fetchone()
        total, thumbs_up, thumbs_down, no_feedback = stats
        
        print(f"📊 Total messages: {total}")
        print(f"   👍 Thumbs up: {thumbs_up}")
        print(f"   👎 Thumbs down: {thumbs_down}")
        print(f"   ⏸️  No feedback: {no_feedback}")
        
        if thumbs_up + thumbs_down > 0:
            satisfaction = (thumbs_up / (thumbs_up + thumbs_down)) * 100
            print(f"   😊 Satisfaction rate: {satisfaction:.1f}%")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error getting feedback stats: {e}")

def check_backend_running():
    """Check if backend is running"""
    print_section("STEP 6: Backend Status")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ Backend is running on http://localhost:8000")
            return True
        else:
            print(f"⚠️  Backend responded with status: {response.status_code}")
            return False
            
    except Exception as e:
        print("❌ Backend is NOT running or not reachable")
        print(f"   Error: {e}")
        print("\n💡 Start backend with: cd backend && python main.py")
        return False

def test_database_write():
    """Test if we can write to database"""
    print_section("STEP 7: Database Write Test")
    
    DB_PATH = Path("data/database/feedback.db")
    
    try:
        import uuid
        from datetime import datetime
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        test_id = str(uuid.uuid4())
        test_msg_id = f"verify_test_{uuid.uuid4().hex[:8]}"
        
        cursor.execute("""
            INSERT INTO feedback_interactions 
            (id, user_id, session_id, message_id, timestamp, question, response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            "verify_test_user",
            "verify_test_session",
            test_msg_id,
            datetime.utcnow().isoformat(),
            "Verification test question",
            "Verification test response"
        ))
        
        conn.commit()
        
        # Verify
        cursor.execute(
            "SELECT COUNT(*) FROM feedback_interactions WHERE message_id = ?",
            (test_msg_id,)
        )
        count = cursor.fetchone()[0]
        
        conn.close()
        
        if count > 0:
            print(f"✅ Database write test PASSED")
            print(f"   Test record saved with message_id: {test_msg_id}")
            return True
        else:
            print(f"❌ Database write test FAILED")
            print(f"   Record not found after insert")
            return False
            
    except Exception as e:
        print(f"❌ Database write test FAILED: {e}")
        return False

def main():
    """Run all verification checks"""
    print_header("CHAT DATABASE VERIFICATION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all checks
    results = {
        'file_exists': check_database_file(),
        'table_structure': check_table_structure(),
    }
    
    total_records, real_records = count_records()
    results['has_records'] = total_records > 0
    results['has_real_messages'] = real_records > 0
    
    recent_count = show_recent_records()
    show_feedback_stats()
    
    results['backend_running'] = check_backend_running()
    results['can_write'] = test_database_write()
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    all_passed = all(results.values())
    
    if all_passed and real_records > 0:
        print("✅✅✅ EVERYTHING IS WORKING! ✅✅✅")
        print(f"\n✓ Database file exists")
        print(f"✓ Table structure is correct")
        print(f"✓ Has {total_records} total records ({real_records} real messages)")
        print(f"✓ Backend is running")
        print(f"✓ Database is writable")
        print(f"\n💡 Chat messages ARE being saved successfully!")
        
    elif all_passed and real_records == 0:
        print("⚠️  SETUP IS CORRECT BUT NO MESSAGES YET")
        print(f"\n✓ Database file exists")
        print(f"✓ Table structure is correct")
        print(f"✓ Database is writable")
        
        if results['backend_running']:
            print(f"✓ Backend is running")
            print(f"\n💡 Everything is ready! Now:")
            print(f"   1. Open Streamlit frontend (streamlit run frontend/app.py)")
            print(f"   2. Send a test message")
            print(f"   3. Run this script again to verify it was saved")
        else:
            print(f"✗ Backend is NOT running")
            print(f"\n💡 Start backend first:")
            print(f"   cd backend")
            print(f"   python main.py")
        
    else:
        print("❌ ISSUES DETECTED")
        print("\n❌ Failed checks:")
        for check, passed in results.items():
            if not passed:
                print(f"   ✗ {check}")
        
        print("\n🔧 Troubleshooting steps:")
        
        if not results['file_exists']:
            print("   1. Run: cd backend && python main.py")
            print("      This will create the database file")
        
        if not results['backend_running']:
            print("   2. Start backend: cd backend && python main.py")
        
        if not results['can_write']:
            print("   3. Check file permissions on data/database/feedback.db")
        
        if not results['has_real_messages']:
            print("   4. Send a test message through the Streamlit frontend")
            print("   5. Check backend logs for database save errors")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()