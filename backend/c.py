"""
Complete Diagnostic and Fix Script
Identifies and fixes database saving issues
"""
import sys
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "=" * 70)
print("COMPREHENSIVE DATABASE DIAGNOSTIC & FIX")
print("=" * 70 + "\n")

# Step 1: Check database file
print("STEP 1: Checking database file...")
print("-" * 70)
DB_PATH = Path("data/database/feedback.db")

if not DB_PATH.exists():
    print("❌ Database file doesn't exist!")
    print("   Creating directory...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("   ✅ Directory created")
else:
    print(f"✅ Database file exists: {DB_PATH}")
    print(f"   Size: {DB_PATH.stat().st_size / 1024:.2f} KB")

# Step 2: Test SQLite direct write
print("\nSTEP 2: Testing direct SQLite write...")
print("-" * 70)

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_interactions (
            id VARCHAR PRIMARY KEY NOT NULL,
            user_id VARCHAR NOT NULL,
            session_id VARCHAR NOT NULL,
            message_id VARCHAR NOT NULL UNIQUE,
            timestamp DATETIME NOT NULL,
            question TEXT NOT NULL,
            response TEXT NOT NULL,
            provider_used VARCHAR,
            tokens_used INTEGER,
            feedback_type VARCHAR,
            feedback_comment TEXT,
            feedback_timestamp DATETIME
        )
    """)
    
    # Insert test record
    test_id = str(uuid.uuid4())
    test_msg_id = f"direct_test_{uuid.uuid4().hex[:8]}"
    
    cursor.execute("""
        INSERT INTO feedback_interactions 
        (id, user_id, session_id, message_id, timestamp, question, response)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        test_id,
        "direct_test_user",
        "direct_test_session",
        test_msg_id,
        datetime.utcnow().isoformat(),
        "Direct SQLite test question",
        "Direct SQLite test response"
    ))
    
    conn.commit()
    print("✅ Direct SQLite write successful")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM feedback_interactions WHERE message_id = ?", (test_msg_id,))
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"✅ Verified: Test record found in database")
    else:
        print(f"❌ ERROR: Record not found after insert!")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Direct SQLite write failed: {e}")
    sys.exit(1)

# Step 3: Test SQLAlchemy
print("\nSTEP 3: Testing SQLAlchemy...")
print("-" * 70)

try:
    from database import init_db, FeedbackInteraction
    from database.connection import SessionLocal
    
    print("✅ Imports successful")
    
    # Initialize
    init_db()
    print("✅ Database initialized")
    
    # Create session
    db = SessionLocal()
    print("✅ Session created")
    
    # Create test interaction
    test_msg_id = f"sqlalchemy_test_{uuid.uuid4().hex[:8]}"
    interaction = FeedbackInteraction(
        user_id="sqlalchemy_test_user",
        session_id="sqlalchemy_test_session",
        message_id=test_msg_id,
        question="SQLAlchemy test question",
        response="SQLAlchemy test response",
        provider_used="test_provider",
        tokens_used=100
    )
    
    print("✅ Interaction object created")
    
    # Save
    db.add(interaction)
    print("✅ Added to session")
    
    db.commit()
    print("✅ Committed")
    
    db.refresh(interaction)
    print(f"✅ Refreshed - ID: {interaction.id}")
    
    # Verify
    check = db.query(FeedbackInteraction).filter(
        FeedbackInteraction.message_id == test_msg_id
    ).first()
    
    if check:
        print(f"✅ VERIFIED: SQLAlchemy record found!")
        print(f"   ID: {check.id}")
        print(f"   Message ID: {check.message_id}")
        print(f"   Question: {check.question}")
    else:
        print(f"❌ ERROR: Record not found!")
    
    db.close()
    
except Exception as e:
    print(f"❌ SQLAlchemy test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Check total records
print("\nSTEP 4: Checking total records...")
print("-" * 70)

try:
    db = SessionLocal()
    total = db.query(FeedbackInteraction).count()
    print(f"📊 Total records in database: {total}")
    
    if total > 0:
        print("\n📝 Recent records:")
        recent = db.query(FeedbackInteraction).order_by(
            FeedbackInteraction.timestamp.desc()
        ).limit(5).all()
        
        for i, record in enumerate(recent, 1):
            print(f"\n{i}. Message ID: {record.message_id}")
            print(f"   User: {record.user_id}")
            print(f"   Question: {record.question[:50]}...")
            print(f"   Time: {record.timestamp}")
    
    db.close()
    
except Exception as e:
    print(f"❌ Failed to check records: {e}")

# Step 5: Test FastAPI dependency injection
print("\nSTEP 5: Testing FastAPI dependency...")
print("-" * 70)

try:
    from database import get_db
    
    # Simulate FastAPI dependency injection
    db_gen = get_db()
    db = next(db_gen)
    
    print("✅ get_db() dependency works")
    
    # Test save through dependency
    test_msg_id = f"fastapi_dep_test_{uuid.uuid4().hex[:8]}"
    interaction = FeedbackInteraction(
        user_id="fastapi_test_user",
        session_id="fastapi_test_session",
        message_id=test_msg_id,
        question="FastAPI dependency test",
        response="FastAPI dependency test response",
        provider_used="test_provider",
        tokens_used=50
    )
    
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    
    # Verify
    check = db.query(FeedbackInteraction).filter(
        FeedbackInteraction.message_id == test_msg_id
    ).first()
    
    if check:
        print(f"✅ VERIFIED: FastAPI dependency save works!")
    else:
        print(f"❌ ERROR: FastAPI dependency save failed!")
    
    # Close using the generator
    try:
        next(db_gen)
    except StopIteration:
        pass
    
except Exception as e:
    print(f"❌ FastAPI dependency test failed: {e}")
    import traceback
    traceback.print_exc()

# Step 6: Summary and recommendations
print("\n" + "=" * 70)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 70)

db = SessionLocal()
total = db.query(FeedbackInteraction).count()
db.close()

print(f"\n📊 Total records now in database: {total}")

if total > 2:
    print("\n✅ Database saving is working!")
    print("\n🔍 If chat messages still aren't saving, the issue is in:")
    print("   1. The chat endpoint not being called")
    print("   2. The database dependency not being injected")
    print("   3. An exception being caught and suppressed")
    print("\n📋 Next steps:")
    print("   1. Send a chat message through the frontend")
    print("   2. Check backend logs for the 🔍 debug messages")
    print("   3. Look for any error messages")
    print("   4. Run: python check_database.py")
else:
    print("\n⚠️  Only test records exist")
    print("\n🔧 Possible issues:")
    print("   1. Chat endpoint database code not updated")
    print("   2. Backend not restarted after code changes")
    print("   3. Frontend not sending user_id")
    print("\n📋 Fix steps:")
    print("   1. Make sure chat.py has the debug logging code")
    print("   2. Restart backend: python main.py")
    print("   3. Send a NEW chat message")
    print("   4. Check backend logs for 🔍 messages")

print("\n✨ Diagnostic complete!\n")