from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, validator
import httpx
from app.config import settings

router = APIRouter()

# Pydantic models for request/response
class SignupRequest(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: str
    
    @validator('email')
    def validate_email(cls, v):
        # Basic email validation for development
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower()
    
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
    
    @validator('password')
    def validate_password(cls, v):
        # Password validation
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v
    
    @validator('confirm_password')
    def validate_confirm_password(cls, v, values):
        # Confirm password validation
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class LoginRequest(BaseModel):
    email: str
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        # Basic email validation for development
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower()

class AuthResponse(BaseModel):
    user_id: str
    username: str
    email: str
    message: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str
    username: str
    email: str

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    """
    Create a new user account in Supabase Auth.
    """
    try:
        print(f"Signup attempt for email: {request.email}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/signup",
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "email": request.email,
                    "password": request.password
                }
            )
            
            # Debug: Print response details
            print(f"Supabase Response Status: {response.status_code}")
            print(f"Supabase Response Text: {response.text}")
            
            # Handle successful responses (200, 201, or any 2xx status)
            if 200 <= response.status_code < 300:
                user_data = response.json()
                print(f"User data structure: {user_data}")
                
                # Extract user ID and email from different possible response structures
                user_id = user_data.get("id") or user_data.get("user", {}).get("id")
                email = user_data.get("email") or user_data.get("user", {}).get("email")
                
                if not user_id or not email:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Unexpected response structure: {user_data}"
                    )
                
                # Save username to user_profiles table
                try:
                    profile_response = await client.post(
                        f"{settings.SUPABASE_URL}/rest/v1/user_profiles",
                        headers={
                            "apikey": settings.SUPABASE_SERVICE_KEY,
                            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                            "Content-Type": "application/json",
                            "Prefer": "return=minimal"
                        },
                        json={
                            "user_id": user_id,
                            "username": request.username
                        }
                    )
                    
                    if profile_response.status_code not in [200, 201]:
                        print(f"Failed to create user profile: {profile_response.text}")
                        # Continue anyway - user is created, profile can be added later
                        
                except Exception as profile_error:
                    print(f"Error creating user profile: {profile_error}")
                    # Continue anyway - user is created, profile can be added later
                
                # Create default "Untitled" folder for the new user
                try:
                    folder_response = await client.post(
                        f"{settings.SUPABASE_URL}/rest/v1/folders",
                        headers={
                            "apikey": settings.SUPABASE_SERVICE_KEY,
                            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                            "Content-Type": "application/json",
                            "Prefer": "return=minimal"
                        },
                        json={
                            "user_id": user_id,
                            "name": "Untitled",
                            "color": "#E9D5FF"
                        }
                    )
                    
                    if folder_response.status_code not in [200, 201]:
                        print(f"Failed to create default folder: {folder_response.text}")
                        # Continue anyway - user is created, folder can be created later
                        
                except Exception as folder_error:
                    print(f"Error creating default folder: {folder_error}")
                    # Continue anyway - user is created, folder can be created later
                
                return AuthResponse(
                    user_id=user_id,
                    username=request.username,
                    email=email,
                    message="User created successfully"
                )
            elif response.status_code == 422:
                error_data = response.json()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid input: {error_data.get('msg', 'Validation error')}"
                )
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("msg", "Invalid input")
                print(f"400 Error Details: {error_msg}")
                
                if "already registered" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="User with this email already exists"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Signup failed: {error_msg}"
                    )
            else:
                error_data = response.json() if response.content else {}
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create user: {error_data.get('msg', 'Unknown error')}"
                )
                
    except httpx.RequestError as e:
        print(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unavailable: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error in signup: {str(e)}")
        print(f"Error type: {type(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return access/refresh tokens.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "email": request.email,
                    "password": request.password
                }
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                user_data = auth_data.get("user", {})
                user_id = user_data["id"]
                
                # Fetch username from user_profiles table
                username = "Unknown"  # Default fallback
                try:
                    profile_response = await client.get(
                        f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{user_id}&select=username",
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
                
                return LoginResponse(
                    access_token=auth_data["access_token"],
                    refresh_token=auth_data["refresh_token"],
                    expires_in=auth_data.get("expires_in", 3600),
                    user_id=user_id,
                    username=username,
                    email=user_data["email"]
                )
            elif response.status_code == 400:
                error_data = response.json()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_data.get("error_description", "Invalid credentials")
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
                
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )
