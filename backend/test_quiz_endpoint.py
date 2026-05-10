#!/usr/bin/env python3
"""
Test script for the Quiz Generation Endpoint

This script demonstrates how to test the quiz generation endpoint
with various scenarios including authentication, error handling, and caching.

Usage:
    python test_quiz_endpoint.py

Requirements:
    - Backend server running on localhost:8000
    - Valid Supabase JWT token (get from frontend/auth)
    - Test file uploaded to the system
"""

import asyncio
import httpx
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
TEST_FILE_ID = "your-file-id-here"  # Replace with actual file ID
SUPABASE_JWT_TOKEN = "your-jwt-token-here"  # Replace with actual JWT token

class QuizEndpointTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def test_ai_quiz_generation(self) -> bool:
        """Test the AI quiz generation without authentication."""
        print("🧪 Testing AI Quiz Generation...")
        
        try:
            response = await self.client.post(f"{self.base_url}/test-ai-quiz")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ AI Quiz Test Successful!")
                print(f"   Questions generated: {data['question_count']}")
                print(f"   AI Generated: {data['is_ai_generated']}")
                
                # Display sample questions
                if data['questions']:
                    print("\n📝 Sample Questions:")
                    for i, q in enumerate(data['questions'][:2], 1):
                        print(f"   {i}. {q['question']}")
                        print(f"      Options: {q['options']}")
                        print(f"      Answer: {q['answer_index']}")
                
                return True
            else:
                print(f"❌ AI Quiz Test Failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ AI Quiz Test Error: {e}")
            return False
    
    async def test_quiz_generation(self, file_id: str, token: str) -> Optional[dict]:
        """Test quiz generation for a specific file."""
        print(f"📚 Testing Quiz Generation for File: {file_id}")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/quiz/{file_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Quiz Generation Successful!")
                print(f"   Quiz ID: {data['quiz_id']}")
                print(f"   Cached: {data['cached']}")
                print(f"   Question Count: {data['question_count']}")
                
                # Display questions
                if data['questions']:
                    print("\n📝 Generated Questions:")
                    for i, q in enumerate(data['questions'], 1):
                        print(f"   {i}. {q['question']}")
                        print(f"      Options: {q['options']}")
                        print(f"      Correct Answer: {q['answer_index']} ({q['options'][q['answer_index']]})")
                        print()
                
                return data
            else:
                print(f"❌ Quiz Generation Failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Quiz Generation Error: {e}")
            return None
    
    async def test_quiz_caching(self, file_id: str, token: str) -> bool:
        """Test that quiz generation returns cached results."""
        print("🔄 Testing Quiz Caching...")
        
        # First call
        quiz1 = await self.test_quiz_generation(file_id, token)
        if not quiz1:
            return False
        
        # Second call should return cached result
        quiz2 = await self.test_quiz_generation(file_id, token)
        if not quiz2:
            return False
        
        # Check if second call was cached
        if quiz2['cached'] and quiz1['quiz_id'] == quiz2['quiz_id']:
            print("✅ Quiz Caching Working Correctly!")
            return True
        else:
            print("❌ Quiz Caching Failed!")
            return False
    
    async def test_quiz_deletion(self, file_id: str, token: str) -> bool:
        """Test quiz deletion."""
        print("🗑️  Testing Quiz Deletion...")
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/quiz/{file_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Quiz Deletion Successful!")
                print(f"   Message: {data['message']}")
                return True
            else:
                print(f"❌ Quiz Deletion Failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Quiz Deletion Error: {e}")
            return False
    
    async def test_error_scenarios(self):
        """Test various error scenarios."""
        print("🚨 Testing Error Scenarios...")
        
        # Test with invalid file ID
        print("\n1. Testing with invalid file ID...")
        try:
            response = await self.client.post(
                f"{self.base_url}/quiz/invalid-file-id",
                headers={
                    "Authorization": f"Bearer invalid-token",
                    "Content-Type": "application/json"
                }
            )
            print(f"   Status: {response.status_code} (Expected: 401 or 404)")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test without authentication
        print("\n2. Testing without authentication...")
        try:
            response = await self.client.post(f"{self.base_url}/quiz/{TEST_FILE_ID}")
            print(f"   Status: {response.status_code} (Expected: 401)")
        except Exception as e:
            print(f"   Error: {e}")
    
    async def run_all_tests(self, file_id: str = TEST_FILE_ID, token: str = SUPABASE_JWT_TOKEN):
        """Run all tests."""
        print("🚀 Starting Quiz Endpoint Tests...")
        print("=" * 50)
        
        # Test 1: AI Quiz Generation (no auth)
        await self.test_ai_quiz_generation()
        print()
        
        # Test 2: Quiz Generation (with auth)
        if file_id != "your-file-id-here" and token != "your-jwt-token-here":
            quiz_data = await self.test_quiz_generation(file_id, token)
            print()
            
            if quiz_data:
                # Test 3: Quiz Caching
                await self.test_quiz_caching(file_id, token)
                print()
                
                # Test 4: Quiz Deletion
                await self.test_quiz_deletion(file_id, token)
                print()
        else:
            print("⚠️  Skipping authenticated tests - please provide valid file_id and token")
            print()
        
        # Test 5: Error Scenarios
        await self.test_error_scenarios()
        
        print("\n" + "=" * 50)
        print("🏁 Tests Completed!")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def main():
    """Main test function."""
    tester = QuizEndpointTester()
    
    try:
        await tester.run_all_tests()
    finally:
        await tester.close()

if __name__ == "__main__":
    print("Quiz Endpoint Test Script")
    print("=" * 30)
    print()
    print("Before running tests:")
    print("1. Start the backend server: uvicorn app.main:app --reload")
    print("2. Update TEST_FILE_ID and SUPABASE_JWT_TOKEN in this script")
    print("3. Ensure you have uploaded a file with text content")
    print()
    
    # Run the tests
    asyncio.run(main())
