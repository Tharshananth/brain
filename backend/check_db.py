"""
Direct Chat Endpoint Test
Tests the chat endpoint directly to verify it saves to database
"""
import requests
import json
import time
from pathlib import Path

API_URL = "http://localhost:8000/api/chat/"

def test_chat_endpoint():
    """Test the chat endpoint directly"""
    
    print("\n" + "=" * 70)
    print("TESTING CHAT ENDPOINT DIRECTLY")
    print("=" * 70 + "\n")
    
    # Create test payload
    payload = {
        "message": "What is VoxelBox?",
        "conversation_history": [],
        "session_id": f"test_session_{int(time.time())}",
        "provider": None,
        "user_id": f"test_user_{int(time.time())}"
    }
    
    print("📤 Sending request to backend...")
    print(f"   URL: {API_URL}")
    print(f"   Message: {payload['message']}")
    print(f"   User ID: {payload['user_id']}")
    print(f"   Session ID: {payload['session_id']}")
    
    try:
        # Send request
        response = requests.post(
            API_URL,
            json=payload,
            timeout=120
        )
        
        print(f"\n📥 Response received:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success!")
            print(f"\n📋 Response data:")
            print(f"   Message ID: {data.get('message_id', 'N/A')}")
            print(f"   Provider: {data.get('provider_used', 'N/A')}")
            print(f"   Session ID: {data.get('session_id', 'N/A')}")
            print(f"   Response length: {len(data.get('response', ''))} chars")
            print(f"\n💬 Response preview:")
            print(f"   {data.get('response', '')[:200]}...")
            
            # Now verify in database
            print(f"\n🔍 Verifying in database...")
            verify_in_database(data.get('message_id'))
            
            return True
        else:
            print(f"   ❌ Error!")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to backend!")
        print(f"   Make sure backend is running: cd backend && python main.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def verify_in_database(message_id):
    """Verify the message was saved in database"""
    
    import sqlite3
    from pathlib import Path
    
    DB_PATH = Path("data/database/feedback.db")
    
    if not DB_PATH.exists():
        print(f"   ❌ Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                user_id, 
                session_id, 
                question, 
                response, 
                provider_used
            FROM feedback_interactions
            WHERE message_id = ?
        """, (message_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"   ✅✅✅ MESSAGE FOUND IN DATABASE!")
            user_id, session_id, question, response, provider = row
            print(f"\n   📊 Database record:")
            print(f"      User ID: {user_id}")
            print(f"      Session ID: {session_id}")
            print(f"      Question: {question[:50]}...")
            print(f"      Response: {response[:50]}...")
            print(f"      Provider: {provider}")
            return True
        else:
            print(f"   ❌❌❌ MESSAGE NOT FOUND IN DATABASE!")
            print(f"   This means the save code isn't working")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking database: {e}")
        return False


def count_total_records():
    """Count all records in database"""
    
    import sqlite3
    from pathlib import Path
    
    DB_PATH = Path("data/database/feedback.db")
    
    print(f"\n📊 Database stats:")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM feedback_interactions")
        total = cursor.fetchone()[0]
        
        # Test vs real
        cursor.execute("""
            SELECT COUNT(*) FROM feedback_interactions 
            WHERE user_id LIKE '%test%'
        """)
        test_count = cursor.fetchone()[0]
        
        real_count = total - test_count
        
        print(f"   Total records: {total}")
        print(f"   Test records: {test_count}")
        print(f"   Real messages: {real_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    print("\n🧪 This script tests the chat endpoint directly")
    print("   It bypasses the Streamlit frontend")
    print("   If this works, the problem is in the frontend")
    print("   If this fails, the problem is in the backend\n")
    
    input("Press Enter to start the test...")
    
    success = test_chat_endpoint()
    
    print("\n" + "=" * 70)
    
    if success:
        print("✅ ENDPOINT TEST PASSED!")
        print("\nIf the database verification also passed:")
        print("   → Backend is working correctly")
        print("   → Problem is in the Streamlit frontend")
        print("   → Check frontend code for user_id passing")
        print("\nIf the database verification failed:")
        print("   → Backend endpoint works but save code fails")
        print("   → Check backend logs for database errors")
    else:
        print("❌ ENDPOINT TEST FAILED!")
        print("\nPossible issues:")
        print("   1. Backend not running")
        print("   2. Backend crashed")
        print("   3. API endpoint error")
        print("\nCheck backend logs for errors")
    
    print("=" * 70)
    
    count_total_records()
    
    print("\n")
    