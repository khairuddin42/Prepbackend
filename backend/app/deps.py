from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from typing import Dict, Any
from app.config import settings

security = HTTPBearer()

class User:
    def __init__(self, id: str, email: str, username: str, token: str):
        self.id = id
        self.email = email
        self.username = username
        self.token = token

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Dependency to validate JWT token and get current user from Supabase Auth.
    """
    token = credentials.credentials
    
    try:
        # Call Supabase Auth API to verify token and get user info
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_KEY
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_data = response.json()
            
            if not user_data.get("id") or not user_data.get("email"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user data",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Fetch username from user_profiles table
            username = "Unknown"  # Default fallback
            try:
                profile_response = await client.get(
                    f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{user_data['id']}&select=username",
                    headers={
                        "apikey": settings.SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                    }
                )
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    if profile_data and len(profile_data) > 0:
                        username = profile_data[0]["username"]
                        
            except Exception as profile_error:
                print(f"Error fetching user profile: {profile_error}")
                # Continue with default username
            
            return User(id=user_data["id"], email=user_data["email"], username=username, token=token)
            
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to check if the current user is an admin.
    Raises 403 if user is not an admin.
    """
    token = current_user.token
    
    try:
        async with httpx.AsyncClient() as client:
            # Check if user is admin in user_profiles table
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{current_user.id}&select=is_admin",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )
            
            if response.status_code == 200:
                profile_data = response.json()
                if profile_data and len(profile_data) > 0:
                    is_admin = profile_data[0].get("is_admin", False)
                    if is_admin:
                        return current_user
            
            # User is not an admin
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error checking admin status: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )