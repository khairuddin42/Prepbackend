from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, validator
import httpx
from app.deps import get_current_user, User
from app.config import settings

router = APIRouter()

# Pydantic models for profile management
class UpdateUsernameRequest(BaseModel):
    username: str
    
    @validator('username')
    def validate_username(cls, v):
        # Username validation
        if len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v.strip()) > 30:
            raise ValueError('Username must be less than 30 characters')
        # Allow alphanumeric characters, underscores, and hyphens
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.strip()

class ProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str

@router.get("/ping")
async def protected_ping(current_user: User = Depends(get_current_user)):
    """
    Protected endpoint that requires authentication.
    Returns a simple ping response with user information.
    """
    return {
        "msg": "pong",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username
        }
    }

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile information.
    """
    return ProfileResponse(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email
    )

@router.put("/profile/username", response_model=ProfileResponse)
async def update_username(
    request: UpdateUsernameRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update user's username.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Check if username is already taken
            check_response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles?username=eq.{request.username}&select=user_id",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )
            
            if check_response.status_code == 200:
                existing_profiles = check_response.json()
                if existing_profiles and len(existing_profiles) > 0:
                    # Check if it's not the current user's username
                    if existing_profiles[0]["user_id"] != current_user.id:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Username is already taken"
                        )
            
            # Update username in user_profiles table
            update_response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{current_user.id}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "username": request.username,
                    "updated_at": "now()"
                }
            )
            
            if update_response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update username"
                )
            
            return ProfileResponse(
                user_id=current_user.id,
                username=request.username,
                email=current_user.email
            )
            
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile service unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update username: {str(e)}"
        )
