"""
Test script to verify database saves are working for REAL messages
Run this to simulate a real frontend request
"""
import requests
import json
import time
import hashlib

# Configuration
API_BASE_URL = "http://localhost:8000"

def generate_user_id():
    """Generate a unique user ID like the frontend does"""
    unique_string = f"{time.time()}_{hash(str(time.time()))}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:16]

def test_real_chat_message():
    """Test sending a real chat message like the frontend does"""
    
    print("\n" + "=" * 80)
    print("TESTING REAL CHAT MESSAGE SAVE")
    print("=" * 80)
    
    # Generate IDs like frontend does
    user_id = generate_user_id()
    session_id = f"session_{int(time.time())}"
    
    print(f"\n[TEST] Generated user_id: {user_id}")
    print(f"[TEST] Generated session_id: {session_id}")
    
    # Prepare payload exactly like frontend sends it
    payload = {
        "message": "What is VoxelBox Explore? This is a real test from frontend simulation.",
        "conversation_history": [],
        "session_id": session_id,
        "provider": None,  # Use default provider
        "user_id": user_id  # This is the critical field!
    }
    
    print(f"\n[TEST] Sending request to {API_BASE_URL}/api/chat/")
    print(f"[TEST] Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Send request
        print("\n[TEST] Sending POST request...")
        response = requests.post(
            f"{API_BASE_URL}/api/chat/",
            json=payload,
            timeout=120
        )
        
        print(f"\n[TEST] Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[TEST] ✅ Chat request successful!")
            print(f"[TEST] Message ID: {result.get('message_id')}")
            print(f"[TEST] Provider used: {result.get('provider_used')}")
            print(f"[TEST] Response length: {len(result.get('response', ''))} chars")
            
            message_id = result.get('message_id')
            
            # Wait a moment for DB to fully commit
            print("\n[TEST] Waiting 2 seconds for DB commit...")
            time.sleep(2)
            
            # Now verify it's in the database
            print("\n[TEST] Verifying database save...")
            print(f"[TEST] Run this command to check:")
            print(f"       python test_db.py")
            print(f"\n[TEST] Or check for message_id: {message_id}")
            
            return True
            
        else:
            print(f"[TEST] ❌ Request failed with status {response.status_code}")
            print(f"[TEST] Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n[TEST] ❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def check_backend_health():
    """Check if backend is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    print("\n" + "=" * 80)
    print("REAL MESSAGE DATABASE SAVE TEST")
    print("=" * 80)
    
    # Check backend
    print("\n[CHECK] Checking if backend is running...")
    if not check_backend_health():
        print("[CHECK] ❌ Backend is not running!")
        print("[CHECK] Start backend with: cd backend && python main.py")
        return
    
    print("[CHECK] ✅ Backend is running")
    
    # Test real message
    success = test_real_chat_message()
    
    # Final instructions
    print("\n" + "=" * 80)
    if success:
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\n📋 Next steps:")
        print("   1. Run: python test_db.py")
        print("   2. Look for 'REAL' messages in the output")
        print("   3. Check section '5. RECENT REAL CHAT MESSAGES'")
        print("\nIf you see your test message, the database save is working! ✅")
    else:
        print("TEST FAILED!")
        print("=" * 80)
        print("\n🔧 Troubleshooting:")
        print("   1. Check backend logs for errors")
        print("   2. Make sure chat.py is using the fixed version")
        print("   3. Restart the backend server")
    
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    main()