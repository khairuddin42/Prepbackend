import httpx
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.deps import get_current_user, User
from app.config import settings

router = APIRouter()

async def verify_resource_ownership(resource_id: str, table_name: str, user_id: str) -> Dict[str, Any]:
    """
    Verify that the resource belongs to the current user and return the resource data.
    
    Args:
        resource_id: The ID of the resource to verify
        table_name: The table name (files, summaries, quizzes, flashcards)
        user_id: The current user's ID
        
    Returns:
        Dict containing the resource data if found and owned by user
        
    Raises:
        HTTPException: 404 if resource not found, 403 if not owned by user
    """
    try:
        async with httpx.AsyncClient() as client:
            # Query the resource and verify ownership
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{table_name}?id=eq.{resource_id}&select=*",
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database query failed"
                )
            
            data = response.json()
            
            if not data or len(data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{table_name[:-1].capitalize()} not found"
                )
            
            resource = data[0]
            
            # Verify ownership
            if resource.get("user_id") != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete your own resources"
                )
            
            return resource
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify resource ownership: {str(e)}"
        )

async def delete_resource(table_name: str, resource_id: str) -> bool:
    """
    Delete a resource from the specified table.
    
    Args:
        table_name: Table name (files, summaries, quizzes, flashcards)
        resource_id: ID of the resource to delete
        
    Returns:
        True if deletion was successful
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{settings.SUPABASE_URL}/rest/v1/{table_name}?id=eq.{resource_id}",
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_KEY
                }
            )
            
            if response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete {table_name[:-1]}"
                )
            
            return True
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during deletion: {str(e)}"
        )

@router.delete("/file/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete an uploaded file and all its related summaries, quizzes, and flashcards.
    
    Due to CASCADE DELETE constraints in the database:
    - Deleting a file automatically deletes all associated summaries
    - Deleting a file automatically deletes all associated quizzes  
    - Deleting a file automatically deletes all associated flashcards
    
    Only the file owner can perform this action.
    """
    
    # Verify ownership before deletion
    await verify_resource_ownership(file_id, "files", current_user.id)
    
    # Delete the file (CASCADE will handle related records)
    await delete_resource("files", file_id)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"deleted": True}
    )

@router.delete("/summary/{summary_id}")
async def delete_summary(
    summary_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific summary.
    
    Only the summary owner can perform this action.
    This does NOT delete the associated file or other related content.
    """
    
    # Verify ownership before deletion
    await verify_resource_ownership(summary_id, "summaries", current_user.id)
    
    # Delete the summary
    await delete_resource("summaries", summary_id)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"deleted": True}
    )

@router.delete("/quiz/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific quiz.
    
    Only the quiz owner can perform this action.
    This does NOT delete the associated file or other related content.
    """
    
    # Verify ownership before deletion
    await verify_resource_ownership(quiz_id, "quizzes", current_user.id)
    
    # Delete the quiz
    await delete_resource("quizzes", quiz_id)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"deleted": True}
    )

@router.delete("/flashcard/{flashcard_id}")
async def delete_flashcard(
    flashcard_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific flashcard set.
    
    Only the flashcard owner can perform this action.
    This does NOT delete the associated file or other related content.
    """
    
    # Verify ownership before deletion
    await verify_resource_ownership(flashcard_id, "flashcards", current_user.id)
    
    # Delete the flashcard
    await delete_resource("flashcards", flashcard_id)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"deleted": True}
    )

# Soft-delete implementation example (not implemented but shows how to extend)
"""
To implement soft-delete, you would need to:

1. Add deleted_at column to each table:
   ALTER TABLE files ADD COLUMN deleted_at TIMESTAMPTZ;
   ALTER TABLE summaries ADD COLUMN deleted_at TIMESTAMPTZ;
   ALTER TABLE quizzes ADD COLUMN deleted_at TIMESTAMPTZ;
   ALTER TABLE flashcards ADD COLUMN deleted_at TIMESTAMPTZ;

2. Modify queries to exclude soft-deleted records:
   SELECT * FROM files WHERE deleted_at IS NULL;

3. Update delete endpoints to set deleted_at instead of actual deletion:
   UPDATE files SET deleted_at = NOW() WHERE id = $1;

4. Add restore endpoint to un-delete:
   UPDATE files SET deleted_at = NULL WHERE id = $1;

5. Add purged_at column for permanent deletion after 30 days:
   ALTER TABLE files ADD COLUMN purged_at TIMESTAMPTZ;
   CREATE INDEX idx_files_deleted_at ON files(deleted_at);
"""

