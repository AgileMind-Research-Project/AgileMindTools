"""
Test script for MySQL database connection
This script tests the database connection using the credentials from .env file
"""

from database import create_database_connection
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_connection():
    """Test the database connection"""
    try:
        print("=" * 60)
        print("Testing MySQL Database Connection")
        print("=" * 60)
        
        # Create connection using default schema from .env
        print("\n1. Testing connection with default schema (agilemind_db)...")
        engine = create_database_connection()
        
        # Test the connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"   ✓ Connection successful! Test query returned: {row[0]}")
        
        # Test database access
        print("\n2. Testing database access...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT DATABASE() as current_db"))
            row = result.fetchone()
            print(f"   ✓ Current database: {row[0]}")
        
        # List tables
        print("\n3. Listing tables in database...")
        with engine.connect() as connection:
            result = connection.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            if tables:
                print(f"   ✓ Found {len(tables)} table(s):")
                for table in tables:
                    print(f"     • {table[0]}")
            else:
                print("   ⚠ No tables found in database")
        
        print("\n" + "=" * 60)
        print("Database connection test completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Connection test failed!")
        print(f"Error: {str(e)}")
        print("\nPlease check:")
        print("1. All credentials in .env file are correct")
        print("2. Required packages are installed: sqlalchemy, pymysql, python-dotenv")
        print("3. Database server is accessible")
        return False

if __name__ == "__main__":
    test_connection()
