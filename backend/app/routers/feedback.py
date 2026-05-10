"""
Feedback Router
Handles user feedback submission and admin feedback retrieval
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
import httpx
from app.deps import get_current_user, User
from app.config import settings

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackSubmit(BaseModel):
    feedback_text: str
    category: str
    rating: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    feedback_text: str
    category: str
    rating: Optional[str]
    status: str
    admin_notes: Optional[str]
    created_at: str
    updated_at: str
    user_email: Optional[str] = None
    username: Optional[str] = None


class FeedbackUpdate(BaseModel):
    status: Optional[str] = None
    admin_notes: Optional[str] = None


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback: FeedbackSubmit,
    current_user: User = Depends(get_current_user)
):
    """
    Submit user feedback
    """
    try:
        # Validate category
        valid_categories = ['bugs', 'feature_request', 'uploading_files', 'notes_ai', 'flashcards_ai', 'quizfetch']
        if feedback.category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )

        # Validate rating if provided
        if feedback.rating and feedback.rating not in ['good', 'bad']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid rating. Must be 'good' or 'bad'"
            )

        # Insert feedback using Supabase REST API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/user_feedback",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "user_id": current_user.id,
                    "feedback_text": feedback.feedback_text.strip(),
                    "category": feedback.category,
                    "rating": feedback.rating,
                    "status": "pending"
                }
            )

            if response.status_code not in [200, 201]:
                print(f"Error submitting feedback: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to submit feedback"
                )

            result_data = response.json()
            if isinstance(result_data, list) and len(result_data) > 0:
                return {
                    "message": "Feedback submitted successfully",
                    "feedback_id": result_data[0]['id']
                }
            elif isinstance(result_data, dict) and 'id' in result_data:
                return {
                    "message": "Feedback submitted successfully",
                    "feedback_id": result_data['id']
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to submit feedback"
                )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get("/my-feedback", response_model=List[FeedbackResponse])
async def get_my_feedback(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's feedback submissions
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/user_feedback?user_id=eq.{current_user.id}&order=created_at.desc",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch feedback"
                )

            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch feedback"
        )


@router.get("/admin/all")
async def get_all_feedback(
    status_filter: Optional[str] = Query(None),
    category_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Admin endpoint: Get all feedback submissions with user details
    """
    try:
        async with httpx.AsyncClient() as client:
            # Check if user is admin
            profile_response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{current_user.id}&select=is_admin",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )

            if profile_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            profile_data = profile_response.json()
            if not profile_data or len(profile_data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            is_admin = profile_data[0].get('is_admin', False)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            # Build query URL
            query_params = []
            
            if status_filter:
                query_params.append(f"status=eq.{status_filter}")
            if category_filter:
                query_params.append(f"category=eq.{category_filter}")
            
            query_params.append("order=created_at.desc")
            
            query_url = f"{settings.SUPABASE_URL}/rest/v1/user_feedback"
            if query_params:
                query_url += "?" + "&".join(query_params)
            
            # Get feedback with user profiles
            feedback_response = await client.get(
                query_url,
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )

            if feedback_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch feedback"
                )

            feedback_list = feedback_response.json()
            if not isinstance(feedback_list, list):
                feedback_list = []

            # Get user profiles for all feedback items
            user_ids = list(set([item.get('user_id') for item in feedback_list if item.get('user_id')]))
            
            # Fetch user profiles
            profiles_map = {}
            if user_ids:
                # Query user_profiles for all user IDs (Supabase uses parentheses for IN clause)
                user_ids_str = ",".join(user_ids)
                profiles_response = await client.get(
                    f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=in.({user_ids_str})&select=user_id,username,full_name",
                    headers={
                        "apikey": settings.SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                    }
                )
                
                if profiles_response.status_code == 200:
                    profiles = profiles_response.json()
                    if isinstance(profiles, list):
                        for profile in profiles:
                            profiles_map[profile.get('user_id')] = profile

            # Format response to include user info
            formatted_feedback = []
            for item in feedback_list:
                user_id = item.get('user_id')
                profile = profiles_map.get(user_id, {})
                
                formatted_feedback.append({
                    'id': item['id'],
                    'user_id': user_id,
                    'username': profile.get('username', 'Unknown'),
                    'full_name': profile.get('full_name', 'Unknown'),
                    'feedback_text': item['feedback_text'],
                    'category': item['category'],
                    'rating': item.get('rating'),
                    'status': item['status'],
                    'admin_notes': item.get('admin_notes'),
                    'created_at': item['created_at'],
                    'updated_at': item['updated_at']
                })

            return formatted_feedback

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching all feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch feedback"
        )


@router.put("/admin/{feedback_id}", status_code=status.HTTP_200_OK)
async def update_feedback(
    feedback_id: str,
    update_data: FeedbackUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Admin endpoint: Update feedback status and admin notes
    """
    try:
        async with httpx.AsyncClient() as client:
            # Check if user is admin
            profile_response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{current_user.id}&select=is_admin",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )

            if profile_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            profile_data = profile_response.json()
            if not profile_data or len(profile_data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            is_admin = profile_data[0].get('is_admin', False)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            # Validate status if provided
            if update_data.status and update_data.status not in ['pending', 'reviewed', 'resolved']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status. Must be 'pending', 'reviewed', or 'resolved'"
                )

            # Build update data
            update_dict = {}
            if update_data.status:
                update_dict['status'] = update_data.status
            if update_data.admin_notes is not None:
                update_dict['admin_notes'] = update_data.admin_notes

            if not update_dict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No data to update"
                )

            # Update feedback
            update_response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/user_feedback?id=eq.{feedback_id}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=update_dict
            )

            if update_response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Feedback not found"
                )

            result_data = update_response.json()
            if isinstance(result_data, list) and len(result_data) > 0:
                return {
                    "message": "Feedback updated successfully",
                    "feedback": result_data[0]
                }
            elif isinstance(result_data, dict):
                return {
                    "message": "Feedback updated successfully",
                    "feedback": result_data
                }
            else:
                return {
                    "message": "Feedback updated successfully"
                }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update feedback"
        )


@router.get("/admin/stats")
async def get_feedback_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Admin endpoint: Get feedback statistics
    """
    try:
        async with httpx.AsyncClient() as client:
            # Check if user is admin
            profile_response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{current_user.id}&select=is_admin",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )

            if profile_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            profile_data = profile_response.json()
            if not profile_data or len(profile_data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            is_admin = profile_data[0].get('is_admin', False)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

            # Get all feedback
            feedback_response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/user_feedback",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )

            if feedback_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch feedback statistics"
                )

            all_feedback = feedback_response.json()
            if not isinstance(all_feedback, list):
                all_feedback = []

            # Calculate stats
            total = len(all_feedback)
            by_status = {}
            by_category = {}
            by_rating = {'good': 0, 'bad': 0, 'none': 0}

            for item in all_feedback:
                # Count by status
                status_val = item.get('status', 'pending')
                by_status[status_val] = by_status.get(status_val, 0) + 1

                # Count by category
                category = item.get('category', 'unknown')
                by_category[category] = by_category.get(category, 0) + 1

                # Count by rating
                rating = item.get('rating')
                if rating == 'good':
                    by_rating['good'] += 1
                elif rating == 'bad':
                    by_rating['bad'] += 1
                else:
                    by_rating['none'] += 1

            return {
                'total_feedback': total,
                'by_status': by_status,
                'by_category': by_category,
                'by_rating': by_rating
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching feedback stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch feedback statistics"
        )
