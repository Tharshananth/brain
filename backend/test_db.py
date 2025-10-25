"""
Test Database Save Functionality
Directly tests if we can save to the database
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, SessionLocal, FeedbackInteraction
from datetime import datetime
import uuid

def test_database_save():
    """Test saving data to database"""
    
    print("\n" + "=" * 60)
    print("DATABASE SAVE TEST")
    print("=" * 60 + "\n")
    
    try:
        # Initialize database
        print("1️⃣  Initializing database...")
        init_db()
        print("   ✅ Database initialized\n")
        
        # Create a test interaction
        print("2️⃣  Creating test interaction...")
        test_interaction = FeedbackInteraction(
            user_id="test_user",
            session_id="test_session",
            message_id=f"test_msg_{uuid.uuid4().hex[:8]}",
            question="This is a test question",
            response="This is a test response",
            provider_used="test_provider",
            tokens_used=100
        )
        print("   ✅ Test interaction created\n")
        
        # Save to database
        print("3️⃣  Saving to database...")
        db = SessionLocal()
        
        try:
            db.add(test_interaction)
            db.commit()
            db.refresh(test_interaction)
            print(f"   ✅ Saved with ID: {test_interaction.id}\n")
            
            # Verify it was saved
            print("4️⃣  Verifying save...")
            saved = db.query(FeedbackInteraction).filter(
                FeedbackInteraction.message_id == test_interaction.message_id
            ).first()
            
            if saved:
                print("   ✅ Found in database!")
                print(f"      Message ID: {saved.message_id}")
                print(f"      Question: {saved.question}")
                print(f"      Response: {saved.response}\n")
                
                # Count total records
                total = db.query(FeedbackInteraction).count()
                print(f"📊 Total records in database: {total}\n")
                
                print("=" * 60)
                print("✅ DATABASE SAVE TEST PASSED!")
                print("=" * 60)
                print("\n💡 If this works but chat doesn't save, the issue is in")
                print("   the chat endpoint's database dependency injection.\n")
                
                return True
            else:
                print("   ❌ Not found in database after save!")
                return False
                
        except Exception as e:
            print(f"   ❌ Error during save: {e}")
            db.rollback()
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_database_save()
    
    if success:
        print("\n✨ Next step: Send a chat message and check if it saves")
        print("   Run: python check_database.py")
    else:
        print("\n❌ Database save is not working. Check the error above.")