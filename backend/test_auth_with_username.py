#!/usr/bin/env python3
"""
Test script for the updated authentication system with username support.
This script tests the signup, login, and profile management endpoints.
"""

import httpx
import asyncio
import json

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": "testuser123",
    "email": "test@example.com",
    "password": "password123",
    "confirm_password": "password123"
}

async def test_signup():
    """Test the signup endpoint with username and confirm_password."""
    print("🧪 Testing signup endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/auth/signup",
                json=TEST_USER
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 201:
                print("✅ Signup successful!")
                return response.json()
            else:
                print("❌ Signup failed!")
                return None
                
        except Exception as e:
            print(f"❌ Signup error: {e}")
            return None

async def test_login():
    """Test the login endpoint."""
    print("\n🧪 Testing login endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": TEST_USER["email"],
                    "password": TEST_USER["password"]
                }
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Login successful!")
                return response.json()
            else:
                print("❌ Login failed!")
                return None
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return None

async def test_profile_endpoints(access_token):
    """Test profile management endpoints."""
    print("\n🧪 Testing profile endpoints...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Test get profile
            print("Testing GET /protected/profile...")
            response = await client.get(
                f"{BASE_URL}/protected/profile",
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("✅ Get profile successful!")
                
                # Test update username
                print("\nTesting PUT /protected/profile/username...")
                new_username = "updateduser456"
                
                update_response = await client.put(
                    f"{BASE_URL}/protected/profile/username",
                    headers=headers,
                    json={"username": new_username}
                )
                
                print(f"Status Code: {update_response.status_code}")
                print(f"Response: {update_response.json()}")
                
                if update_response.status_code == 200:
                    print("✅ Update username successful!")
                else:
                    print("❌ Update username failed!")
            else:
                print("❌ Get profile failed!")
                
        except Exception as e:
            print(f"❌ Profile endpoints error: {e}")

async def test_password_validation():
    """Test password validation."""
    print("\n🧪 Testing password validation...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test mismatched passwords
            response = await client.post(
                f"{BASE_URL}/auth/signup",
                json={
                    "username": "testuser456",
                    "email": "test2@example.com",
                    "password": "password123",
                    "confirm_password": "differentpassword"
                }
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 422:
                print("✅ Password validation working correctly!")
            else:
                print("❌ Password validation not working!")
                
        except Exception as e:
            print(f"❌ Password validation error: {e}")

async def main():
    """Run all tests."""
    print("🚀 Starting authentication system tests...\n")
    
    # Test password validation first
    await test_password_validation()
    
    # Test signup
    signup_result = await test_signup()
    
    if signup_result:
        # Test login
        login_result = await test_login()
        
        if login_result:
            # Test profile endpoints
            await test_profile_endpoints(login_result["access_token"])
    
    print("\n🏁 Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())

