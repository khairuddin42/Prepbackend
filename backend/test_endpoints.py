import httpx
import asyncio
import os
import sys

# Force UTF-8 for stdout if possible, or just use ASCII
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

BASE_URL = "http://localhost:8000"
TEST_USER = {
    "email": "test@example.com",
    "password": "password123"
}

async def login():
    async with httpx.AsyncClient() as client:
        try:
            print("Logging in...")
            response = await client.post(
                f"{BASE_URL}/auth/login",
                json=TEST_USER
            )
            if response.status_code == 200:
                print("[OK] Login successful")
                return response.json()["access_token"]
            else:
                print(f"[FAIL] Login failed: {response.status_code} {response.text}")
                # Try signup if login fails
                print("Trying signup...")
                signup = await client.post(
                    f"{BASE_URL}/auth/signup",
                    json={**TEST_USER, "username": "testuser", "confirm_password": "password123"}
                )
                if signup.status_code in [200, 201]:
                    print("[OK] Signup successful. Logging in again...")
                    response = await client.post(f"{BASE_URL}/auth/login", json=TEST_USER)
                    return response.json()["access_token"]
                else:
                    print(f"[FAIL] Signup failed: {signup.status_code} {signup.text}")
                    return None
        except Exception as e:
            print(f"[FAIL] Error during login: {e}")
            return None

async def test_create_folder(token):
    async with httpx.AsyncClient() as client:
        print("\nTesting Create Folder...")
        response = await client.post(
            f"{BASE_URL}/folders/",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test Folder", "color": "#E9D5FF"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code in [200, 201]:
            print("[OK] Folder created")
            return response.json()["id"]
        else:
            print("[FAIL] Failed to create folder")
            return None

async def test_upload_file(token, folder_id):
    async with httpx.AsyncClient() as client:
        print("\nTesting Upload File...")
        
        # Create a dummy file
        with open("test.txt", "w") as f:
            f.write("This is a test file content.")
            
        try:
            files = {'file': ('test.txt', open('test.txt', 'rb'), 'text/plain')}
            data = {'folder_id': folder_id} if folder_id else {}
            
            response = await client.post(
                f"{BASE_URL}/files/upload_file",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=data
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code in [200, 201]:
                print("[OK] File uploaded")
            else:
                print("[FAIL] Failed to upload file")
                
        finally:
            if os.path.exists("test.txt"):
                os.remove("test.txt")

async def main():
    token = await login()
    if token:
        folder_id = await test_create_folder(token)
        if folder_id:
            await test_upload_file(token, folder_id)

if __name__ == "__main__":
    asyncio.run(main())
