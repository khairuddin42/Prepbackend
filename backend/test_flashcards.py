"""
Simple test script for flashcard generation endpoint
Run from backend directory: python test_flashcards.py
"""

import requests
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
# You'll need to set these after authentication
AUTH_TOKEN: Optional[str] = None  # Set this to your actual token
FILE_ID: Optional[str] = None  # Set this to an actual file_id


def test_flashcard_generation(file_id: str, auth_token: str, count: int = 10):
    """
    Test flashcard generation endpoint.
    
    Args:
        file_id: UUID of the file to generate flashcards from
        auth_token: Authentication bearer token
        count: Number of flashcards to generate (5-30)
    """
    print(f"\n{'='*60}")
    print(f"Testing Flashcard Generation")
    print(f"{'='*60}")
    
    # Setup headers
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Generate flashcards
    print(f"\n1. Generating {count} flashcards for file {file_id}...")
    response = requests.post(
        f"{BASE_URL}/flashcards/{file_id}?count={count}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Flashcard ID: {data['flashcard_id']}")
        print(f"   Card Count: {data['card_count']}")
        print(f"   Cached: {data['cached']}")
        print(f"   Filename: {data.get('filename', 'N/A')}")
        
        print(f"\n   Generated Flashcards:")
        for i, card in enumerate(data['cards'][:3], 1):  # Show first 3
            print(f"\n   Card {i}:")
            print(f"      Front: {card['front']}")
            print(f"      Back: {card['back'][:100]}{'...' if len(card['back']) > 100 else ''}")
        
        if len(data['cards']) > 3:
            print(f"\n   ... and {len(data['cards']) - 3} more cards")
        
        flashcard_id = data['flashcard_id']
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.json()}")
        return
    
    # Test 2: Get cached flashcards
    print(f"\n2. Fetching cached flashcards (should be instant)...")
    response = requests.post(
        f"{BASE_URL}/flashcards/{file_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        if data['cached']:
            print(f"✅ Cached response received!")
            print(f"   Flashcard ID: {data['flashcard_id']}")
            print(f"   Card Count: {data['card_count']}")
        else:
            print(f"⚠️  Response not cached (unexpected)")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.json()}")
    
    # Test 3: Delete flashcards
    print(f"\n3. Deleting flashcards...")
    response = requests.delete(
        f"{BASE_URL}/flashcards/{file_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Deleted successfully!")
        print(f"   Message: {data['message']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.json()}")
    
    # Test 4: Generate new flashcards (should regenerate)
    print(f"\n4. Regenerating flashcards (should create new ones)...")
    response = requests.post(
        f"{BASE_URL}/flashcards/{file_id}?count={count + 5}",  # Different count
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Regenerated successfully!")
        print(f"   New Flashcard ID: {data['flashcard_id']}")
        print(f"   Card Count: {data['card_count']}")
        print(f"   Cached: {data['cached']}")
        
        if data['flashcard_id'] != flashcard_id:
            print(f"   ✓ New flashcard set created")
        else:
            print(f"   ⚠️  Same flashcard ID (unexpected)")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.json()}")
    
    print(f"\n{'='*60}")
    print("Test Complete!")
    print(f"{'='*60}\n")


def test_validation_errors(file_id: str, auth_token: str):
    """Test validation error handling."""
    print(f"\n{'='*60}")
    print(f"Testing Validation Errors")
    print(f"{'='*60}")
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # Test invalid count (too low)
    print(f"\n1. Testing count < 5 (should fail)...")
    response = requests.post(
        f"{BASE_URL}/flashcards/{file_id}?count=3",
        headers=headers
    )
    if response.status_code == 422:
        print(f"✅ Validation error caught correctly")
        print(f"   Status: {response.status_code}")
    else:
        print(f"⚠️  Expected 422, got {response.status_code}")
    
    # Test invalid count (too high)
    print(f"\n2. Testing count > 30 (should fail)...")
    response = requests.post(
        f"{BASE_URL}/flashcards/{file_id}?count=50",
        headers=headers
    )
    if response.status_code == 422:
        print(f"✅ Validation error caught correctly")
        print(f"   Status: {response.status_code}")
    else:
        print(f"⚠️  Expected 422, got {response.status_code}")
    
    # Test invalid file_id
    print(f"\n3. Testing invalid file_id (should fail)...")
    response = requests.post(
        f"{BASE_URL}/flashcards/invalid-uuid-here",
        headers=headers
    )
    if response.status_code in [404, 422]:
        print(f"✅ Error caught correctly")
        print(f"   Status: {response.status_code}")
    else:
        print(f"⚠️  Expected 404/422, got {response.status_code}")
    
    print(f"\n{'='*60}")
    print("Validation Tests Complete!")
    print(f"{'='*60}\n")


def main():
    """Main test runner."""
    print("\n" + "="*60)
    print("Flashcard Generation Endpoint Test Suite")
    print("="*60)
    
    # Check configuration
    if not AUTH_TOKEN:
        print("\n⚠️  ERROR: AUTH_TOKEN not set!")
        print("   Please set AUTH_TOKEN in the script configuration")
        print("   Example: AUTH_TOKEN = 'your_token_here'")
        return
    
    if not FILE_ID:
        print("\n⚠️  ERROR: FILE_ID not set!")
        print("   Please set FILE_ID in the script configuration")
        print("   Example: FILE_ID = '123e4567-e89b-12d3-a456-426614174000'")
        return
    
    # Run tests
    try:
        # Test normal operation
        test_flashcard_generation(FILE_ID, AUTH_TOKEN, count=10)
        
        # Test validation
        test_validation_errors(FILE_ID, AUTH_TOKEN)
        
        print("\n✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error!")
        print("   Make sure the server is running at:", BASE_URL)
        print("   Start server with: uvicorn app.main:app --reload")
    
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


