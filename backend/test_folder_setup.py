#!/usr/bin/env python3
"""
Test script to verify folder setup and database connectivity
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

async def test_database_setup():
    """Test if the folders table and related setup is working"""
    print("Testing database setup...")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            # Test 1: Check if folders table exists
            print("1. Testing folders table access...")
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/folders?limit=1",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
                }
            )
            
            if response.status_code == 200:
                print("SUCCESS: Folders table is accessible")
            else:
                print(f"ERROR: Folders table error: {response.status_code} - {response.text}")
                return False
            
            # Test 2: Check if files table has folder_id column
            print("2. Testing files table with folder_id...")
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/files?limit=1&select=id,folder_id",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
                }
            )
            
            if response.status_code == 200:
                print("SUCCESS: Files table has folder_id column")
            else:
                print(f"ERROR: Files table folder_id error: {response.status_code} - {response.text}")
                return False
            
            # Test 3: Check if summaries table has folder_id column
            print("3. Testing summaries table with folder_id...")
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/summaries?limit=1&select=id,folder_id",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
                }
            )
            
            if response.status_code == 200:
                print("SUCCESS: Summaries table has folder_id column")
            else:
                print(f"ERROR: Summaries table folder_id error: {response.status_code} - {response.text}")
                return False
            
            # Test 4: Check if quizzes table has folder_id column
            print("4. Testing quizzes table with folder_id...")
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/quizzes?limit=1&select=id,folder_id",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
                }
            )
            
            if response.status_code == 200:
                print("SUCCESS: Quizzes table has folder_id column")
            else:
                print(f"ERROR: Quizzes table folder_id error: {response.status_code} - {response.text}")
                return False
            
            # Test 5: Check if flashcards table has folder_id column
            print("5. Testing flashcards table with folder_id...")
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/flashcards?limit=1&select=id,folder_id",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
                }
            )
            
            if response.status_code == 200:
                print("SUCCESS: Flashcards table has folder_id column")
            else:
                print(f"ERROR: Flashcards table folder_id error: {response.status_code} - {response.text}")
                return False
            
            print("\nSUCCESS: All database tests passed!")
            return True
            
    except Exception as e:
        print(f"ERROR: Database test failed: {e}")
        return False

async def test_folder_creation():
    """Test creating a folder via API"""
    print("\nTesting folder creation...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Create a test folder
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/folders",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "user_id": "00000000-0000-0000-0000-000000000000",  # Test UUID
                    "name": "Test Folder",
                    "color": "#E9D5FF"
                }
            )
            
            if response.status_code in [200, 201]:
                folder_data = response.json()
                print(f"SUCCESS: Folder creation test passed: {folder_data}")
                
                # Clean up - delete the test folder
                folder_id = folder_data[0]["id"]
                await client.delete(
                    f"{SUPABASE_URL}/rest/v1/folders?id=eq.{folder_id}",
                    headers={
                        "apikey": SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
                    }
                )
                print("SUCCESS: Test folder cleaned up")
                return True
            else:
                print(f"ERROR: Folder creation failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"ERROR: Folder creation test failed: {e}")
        return False

if __name__ == "__main__":
    async def main():
        print("Testing AI Exam-Prep Tutor Database Setup")
        print("=" * 50)
        
        db_ok = await test_database_setup()
        if db_ok:
            folder_ok = await test_folder_creation()
            if folder_ok:
                print("\nSUCCESS: All tests passed! Database is ready.")
            else:
                print("\nERROR: Folder creation test failed.")
        else:
            print("\nERROR: Database setup test failed.")
            print("\nTIP: Try running: supabase db push")
    
    asyncio.run(main())
