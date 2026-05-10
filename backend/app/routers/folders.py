from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

from app.deps import get_current_user, User
from app.config import settings
import httpx

router = APIRouter()

# Pydantic models for request/response
class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Folder name")
    color: str = Field(default="#E9D5FF", pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")

class FolderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Folder name")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")
    picture_url: Optional[str] = Field(None, description="URL to folder picture")

class FolderResponse(BaseModel):
    id: str
    name: str
    color: str
    picture_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    materials_count: int = 0

class MaterialCount(BaseModel):
    files: int = 0
    summaries: int = 0
    quizzes: int = 0
    flashcards: int = 0

class FolderWithMaterials(FolderResponse):
    materials: MaterialCount

# Color palette for folders (from tech-stack.md)
FOLDER_COLORS = [
    "#E9D5FF",  # Light Lavender
    "#BAE6FD",  # Sky Blue
    "#BBF7D0",  # Mint Green
    "#FEF9C3",  # Soft Yellow
    "#FBCFE8",  # Blush Pink
    "#FED7AA",  # Pale Orange
]

@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new folder for the current user"""
    try:
        # Get user's existing folders to determine next color
        existing_folders = await get_user_folders_from_db(current_user.id)
        used_colors = [folder["color"] for folder in existing_folders]
        
        # Find next available color from palette
        folder_color = folder_data.color
        if folder_color in used_colors:
            for color in FOLDER_COLORS:
                if color not in used_colors:
                    folder_color = color
                    break
        
        # Create folder in Supabase
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/folders",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "user_id": current_user.id,
                    "name": folder_data.name,
                    "color": folder_color
                }
            )
            
            if response.status_code != 201:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create folder"
                )
            
            folder = response.json()[0]
            
            return FolderResponse(
                id=folder["id"],
                name=folder["name"],
                color=folder["color"],
                picture_url=folder.get("picture_url"),
                created_at=folder["created_at"],
                updated_at=folder["updated_at"],
                materials_count=0
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating folder: {str(e)}"
        )

@router.get("/", response_model=List[FolderWithMaterials])
async def get_user_folders(
    current_user: User = Depends(get_current_user)
):
    """Get all folders for the current user with material counts"""
    try:
        folders = await get_user_folders_from_db(current_user.id)
        
        # Get material counts for each folder
        folders_with_materials = []
        for folder in folders:
            materials_count = await get_folder_materials_count(folder["id"])
            
            folders_with_materials.append(FolderWithMaterials(
                id=folder["id"],
                name=folder["name"],
                color=folder["color"],
                picture_url=folder.get("picture_url"),
                created_at=folder["created_at"],
                updated_at=folder["updated_at"],
                materials_count=materials_count.summaries + materials_count.quizzes + materials_count.flashcards,  # Only count generated content
                materials=materials_count
            ))
        
        return folders_with_materials
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching folders: {str(e)}"
        )

@router.get("/{folder_id}", response_model=FolderWithMaterials)
async def get_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific folder by ID with material counts"""
    try:
        # Get folder from database
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/folders?id=eq.{folder_id}&user_id=eq.{current_user.id}",
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )
            
            if response.status_code != 200 or not response.json():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found"
                )
            
            folder = response.json()[0]
            
            # Get material counts
            materials_count = await get_folder_materials_count(folder_id)
            
            return FolderWithMaterials(
                id=folder["id"],
                name=folder["name"],
                color=folder["color"],
                picture_url=folder.get("picture_url"),
                created_at=folder["created_at"],
                updated_at=folder["updated_at"],
                materials_count=materials_count.summaries + materials_count.quizzes + materials_count.flashcards,  # Only count generated content
                materials=materials_count
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching folder: {str(e)}"
        )

@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    folder_update: FolderUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a folder (rename or change color)"""
    try:
        # Prepare update data
        update_data = {}
        if folder_update.name is not None:
            update_data["name"] = folder_update.name
        if folder_update.color is not None:
            update_data["color"] = folder_update.color
        # Allow setting picture_url to None (null) to remove picture
        # Check if picture_url was provided in the request (even if None)
        if 'picture_url' in folder_update.model_dump(exclude_unset=True):
            update_data["picture_url"] = folder_update.picture_url
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Update folder in database
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/folders?id=eq.{folder_id}&user_id=eq.{current_user.id}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=update_data
            )
            
            if response.status_code != 200 or not response.json():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found"
                )
            
            folder = response.json()[0]
            
            return FolderResponse(
                id=folder["id"],
                name=folder["name"],
                color=folder["color"],
                picture_url=folder.get("picture_url"),
                created_at=folder["created_at"],
                updated_at=folder["updated_at"],
                materials_count=0  # Will be calculated separately if needed
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating folder: {str(e)}"
        )

@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a folder and move its materials to the default folder"""
    try:
        # Get or create the user's default folder (Untitled)
        default_folder = await get_or_create_default_folder(current_user.id)
        target_folder_id = default_folder["id"]
        # If we're deleting the default folder itself, create a new Untitled first and move materials there
        if folder_id == target_folder_id:
            async with httpx.AsyncClient() as client:
                create_resp = await client.post(
                    f"{settings.SUPABASE_URL}/rest/v1/folders",
                    headers={
                        "apikey": settings.SUPABASE_ANON_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=representation"
                    },
                    json={
                        "user_id": current_user.id,
                        "name": "Untitled",
                        "color": FOLDER_COLORS[0]
                    }
                )
                if create_resp.status_code not in (200, 201) or not create_resp.json():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot delete default folder: could not create replacement"
                    )
                target_folder_id = create_resp.json()[0]["id"]
        # Move all materials from the folder to default (or new) folder
        await move_folder_materials_to_default(folder_id, target_folder_id)
        
        # Delete the folder
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{settings.SUPABASE_URL}/rest/v1/folders?id=eq.{folder_id}&user_id=eq.{current_user.id}",
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )
            
            if response.status_code != 204:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting folder: {str(e)}"
        )

# Helper functions
async def get_user_folders_from_db(user_id: str) -> List[dict]:
    """Get all folders for a user from database"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.SUPABASE_URL}/rest/v1/folders?user_id=eq.{user_id}&order=created_at.asc",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        return []

async def get_folder_materials_count(folder_id: str) -> MaterialCount:
    """Get count of materials in a folder"""
    async with httpx.AsyncClient() as client:
        # Get counts for each material type using HEAD requests for count
        files_response = await client.head(
            f"{settings.SUPABASE_URL}/rest/v1/files?folder_id=eq.{folder_id}",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Prefer": "count=exact"
            }
        )
        
        summaries_response = await client.head(
            f"{settings.SUPABASE_URL}/rest/v1/summaries?folder_id=eq.{folder_id}",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Prefer": "count=exact"
            }
        )
        
        quizzes_response = await client.head(
            f"{settings.SUPABASE_URL}/rest/v1/quizzes?folder_id=eq.{folder_id}",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Prefer": "count=exact"
            }
        )
        
        flashcards_response = await client.head(
            f"{settings.SUPABASE_URL}/rest/v1/flashcards?folder_id=eq.{folder_id}",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Prefer": "count=exact"
            }
        )
        
        return MaterialCount(
            files=int(files_response.headers.get("content-range", "0").split("/")[-1]) if files_response.status_code == 200 else 0,
            summaries=int(summaries_response.headers.get("content-range", "0").split("/")[-1]) if summaries_response.status_code == 200 else 0,
            quizzes=int(quizzes_response.headers.get("content-range", "0").split("/")[-1]) if quizzes_response.status_code == 200 else 0,
            flashcards=int(flashcards_response.headers.get("content-range", "0").split("/")[-1]) if flashcards_response.status_code == 200 else 0
        )

async def get_default_folder(user_id: str) -> Optional[dict]:
    """Get the default 'Untitled' folder for a user"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.SUPABASE_URL}/rest/v1/folders?user_id=eq.{user_id}&name=eq.Untitled",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
            }
        )
        
        if response.status_code == 200 and response.json():
            return response.json()[0]
        return None


async def get_or_create_default_folder(user_id: str) -> dict:
    """Get the default 'Untitled' folder for a user, creating it if it doesn't exist"""
    default_folder = await get_default_folder(user_id)
    if default_folder:
        return default_folder
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.SUPABASE_URL}/rest/v1/folders",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            json={
                "user_id": user_id,
                "name": "Untitled",
                "color": FOLDER_COLORS[0]
            }
        )
        if response.status_code not in (200, 201) or not response.json():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default folder not found and could not be created"
            )
        return response.json()[0]

async def move_folder_materials_to_default(folder_id: str, default_folder_id: str):
    """Move all materials from a folder to the default folder"""
    async with httpx.AsyncClient() as client:
        # Move files
        await client.patch(
            f"{settings.SUPABASE_URL}/rest/v1/files?folder_id=eq.{folder_id}",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            },
            json={"folder_id": default_folder_id}
        )
        
        # Move summaries
        await client.patch(
            f"{settings.SUPABASE_URL}/rest/v1/summaries?folder_id=eq.{folder_id}",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            },
            json={"folder_id": default_folder_id}
        )
        
        # Move quizzes
        await client.patch(
            f"{settings.SUPABASE_URL}/rest/v1/quizzes?folder_id=eq.{folder_id}",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            },
            json={"folder_id": default_folder_id}
        )
        
        # Move flashcards
        await client.patch(
            f"{settings.SUPABASE_URL}/rest/v1/flashcards?folder_id=eq.{folder_id}",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            },
            json={"folder_id": default_folder_id}
        )
