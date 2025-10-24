"""Manually initialize the database"""
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db
from database.connection import DB_PATH

print("🔧 Initializing database...")
print(f"📍 Database path: {DB_PATH}")

# Create directories
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
print(f"✅ Created directory: {DB_PATH.parent}")

# Initialize database
try:
    init_db()
    print("✅ Database initialized successfully!")
    
    # Verify
    if DB_PATH.exists():
        print(f"✅ Database file created: {DB_PATH}")
        print(f"📊 File size: {DB_PATH.stat().st_size} bytes")
    else:
        print("❌ Database file not created!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()