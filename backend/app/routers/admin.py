from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
import httpx
from datetime import datetime, timezone, timedelta
from app.deps import get_admin_user, User
from app.config import settings

router = APIRouter()

class DashboardStats(BaseModel):
    total_users: int
    total_quizzes_taken: int
    total_flashcards_reviewed: int
    total_notes_generated: int
    total_ai_chat_interactions: int
    daily_active_users: int

class UserInfo(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_admin: bool
    is_active: bool
    created_at: str

class TopicPerformance(BaseModel):
    topic_name: str
    average_score: float
    total_attempts: int

class TopicAttempts(BaseModel):
    topic_name: str
    attempt_count: int

class FlashcardDifficulty(BaseModel):
    again_count: int
    good_count: int
    easy_count: int

class DailyActivity(BaseModel):
    date: str
    quiz_count: int
    flashcard_count: int
    total_actions: int

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    admin_user: User = Depends(get_admin_user)
):
    """
    Get admin dashboard statistics.
    Only accessible to admin users.
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Prefer": "count=exact"
            }
            
            # Get today's date in UTC
            today = datetime.now(timezone.utc).date()
            today_start = f"{today}T00:00:00+00:00"
            today_end = f"{today}T23:59:59+00:00"
            
            # Helper function to get count from Supabase response
            async def get_count(table_name: str, filters: dict = None) -> int:
                """Get count from a Supabase table"""
                url = f"{settings.SUPABASE_URL}/rest/v1/{table_name}"
                params = {"select": "id"}
                if filters:
                    for key, value in filters.items():
                        params[key] = value
                
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return len(data)
                    # Try to get from Content-Range header
                    content_range = response.headers.get("Content-Range", "")
                    if content_range:
                        parts = content_range.split("/")
                        if len(parts) > 1 and parts[1] != "*":
                            return int(parts[1])
                return 0
            
            # 1. Total Users - count from user_profiles
            total_users = await get_count("user_profiles")
            
            # 2. Total Quizzes Taken - count from quiz_interactions
            total_quizzes_taken = await get_count("quiz_interactions")
            
            # 3. Total Flashcards Reviewed - count from flashcard_reviews
            total_flashcards_reviewed = await get_count("flashcard_reviews")
            
            # 4. Total Notes Generated - count from summaries
            total_notes_generated = await get_count("summaries")
            
            # 5. Total AI Chat Interactions - count from quiz_interactions, flashcard_reviews, and summaries
            # Since chat isn't stored separately, we'll use a combination of activities
            # For now, we'll use quiz_interactions + flashcard_reviews as a proxy
            # In a real system, you'd want to log chat interactions separately
            total_ai_chat_interactions = total_quizzes_taken + total_flashcards_reviewed
            
            # 6. Daily Active Users - count distinct users who have activity today
            # Check quiz_interactions, flashcard_reviews, summaries, files created today
            daily_active_set = set()
            
            # Helper function to get distinct user_ids from a table for today
            async def get_daily_active_users(table_name: str, date_column: str) -> set:
                """Get distinct user_ids from a table for today"""
                url = f"{settings.SUPABASE_URL}/rest/v1/{table_name}"
                # Supabase PostgREST format: column.gte=value&column.lte=value
                params = {
                    "select": "user_id",
                    f"{date_column}.gte": today_start,
                    f"{date_column}.lte": today_end
                }
                response = await client.get(url, headers=headers, params=params)
                user_set = set()
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            if item.get("user_id"):
                                user_set.add(item["user_id"])
                return user_set
            
            # Check quiz_interactions today
            daily_active_set.update(await get_daily_active_users("quiz_interactions", "answered_at"))
            
            # Check flashcard_reviews today
            daily_active_set.update(await get_daily_active_users("flashcard_reviews", "reviewed_at"))
            
            # Check summaries created today
            daily_active_set.update(await get_daily_active_users("summaries", "created_at"))
            
            # Check files created today
            daily_active_set.update(await get_daily_active_users("files", "created_at"))
            
            daily_active_users = len(daily_active_set)
            
            return DashboardStats(
                total_users=total_users,
                total_quizzes_taken=total_quizzes_taken,
                total_flashcards_reviewed=total_flashcards_reviewed,
                total_notes_generated=total_notes_generated,
                total_ai_chat_interactions=total_ai_chat_interactions,
                daily_active_users=daily_active_users
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard statistics: {str(e)}"
        )

@router.get("/users", response_model=List[UserInfo])
async def get_users(
    search: Optional[str] = Query(None, description="Search by username or email"),
    admin_user: User = Depends(get_admin_user)
):
    """
    Get list of all users (admin only).
    Supports optional search by username or email.
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get users from user_profiles and join with auth.users for email
            # We need to get user_profiles first, then get emails from auth.users
            url = f"{settings.SUPABASE_URL}/rest/v1/user_profiles"
            params = {
                "select": "user_id,username,full_name,is_admin,is_active,created_at"
            }
            
            # Add search filter if provided
            if search:
                # Supabase PostgREST doesn't support OR in simple queries, so we'll filter in Python
                # But we can still use ilike for username
                params["username"] = f"ilike.*{search}*"
            
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch users"
                )
            
            profiles = response.json()
            if not isinstance(profiles, list):
                profiles = []
            
            # Get emails from auth.users (using Supabase Admin API)
            # Note: We need to use the admin API to access auth.users
            users_list = []
            for profile in profiles:
                user_id = profile.get("user_id")
                
                # Get email from auth.users using admin API
                # Since we can't directly query auth.users via REST, we'll use the admin API
                # For now, we'll make a request to get user info
                auth_url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}"
                auth_response = await client.get(
                    auth_url,
                    headers={
                        "apikey": settings.SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                    }
                )
                
                email = "N/A"
                if auth_response.status_code == 200:
                    auth_data = auth_response.json()
                    email = auth_data.get("email", "N/A")
                
                # Apply search filter for email if search is provided
                if search and search.lower() not in email.lower() and search.lower() not in profile.get("username", "").lower():
                    continue
                
                users_list.append(UserInfo(
                    user_id=user_id,
                    username=profile.get("username", ""),
                    email=email,
                    full_name=profile.get("full_name"),
                    is_admin=profile.get("is_admin", False),
                    is_active=profile.get("is_active", True),
                    created_at=profile.get("created_at", "")
                ))
            
            return users_list
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )

@router.get("/users/{user_id}", response_model=UserInfo)
async def get_user_details(
    user_id: str,
    admin_user: User = Depends(get_admin_user)
):
    """
    Get detailed information about a specific user (admin only).
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get user profile
            url = f"{settings.SUPABASE_URL}/rest/v1/user_profiles"
            params = {
                "user_id": f"eq.{user_id}",
                "select": "user_id,username,full_name,is_admin,is_active,created_at"
            }
            
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            profiles = response.json()
            if not profiles or len(profiles) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            profile = profiles[0]
            
            # Get email from auth.users
            auth_url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}"
            auth_response = await client.get(
                auth_url,
                headers={
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"
                }
            )
            
            email = "N/A"
            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                email = auth_data.get("email", "N/A")
            
            return UserInfo(
                user_id=user_id,
                username=profile.get("username", ""),
                email=email,
                full_name=profile.get("full_name"),
                is_admin=profile.get("is_admin", False),
                is_active=profile.get("is_active", True),
                created_at=profile.get("created_at", "")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user details: {str(e)}"
        )

@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    admin_user: User = Depends(get_admin_user)
):
    """
    Deactivate a user account (admin only).
    Prevents the user from logging in.
    """
    try:
        # Prevent deactivating yourself
        if user_id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            
            # Update is_active to False in user_profiles
            url = f"{settings.SUPABASE_URL}/rest/v1/user_profiles"
            params = {"user_id": f"eq.{user_id}"}
            data = {"is_active": False}
            
            response = await client.patch(url, headers=headers, params=params, json=data)
            
            if response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to deactivate user"
                )
            
            return {"message": "User deactivated successfully", "user_id": user_id}
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deactivating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate user: {str(e)}"
        )

@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    admin_user: User = Depends(get_admin_user)
):
    """
    Activate a user account (admin only).
    Allows the user to log in again.
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            
            # Update is_active to True in user_profiles
            url = f"{settings.SUPABASE_URL}/rest/v1/user_profiles"
            params = {"user_id": f"eq.{user_id}"}
            data = {"is_active": True}
            
            response = await client.patch(url, headers=headers, params=params, json=data)
            
            if response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to activate user"
                )
            
            return {"message": "User activated successfully", "user_id": user_id}
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error activating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate user: {str(e)}"
        )

@router.get("/analytics/quiz-performance-by-topic", response_model=List[TopicPerformance])
async def get_quiz_performance_by_topic(
    user_id: Optional[str] = Query(None, description="Filter by specific user ID"),
    admin_user: User = Depends(get_admin_user)
):
    """
    Get quiz performance by topic (average score per topic).
    Only accessible to admin users.
    Optionally filter by specific user_id.
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get all quiz interactions with quiz info
            # We need to join quiz_interactions with quizzes to get custom_name
            # Since Supabase PostgREST doesn't support complex joins easily, we'll fetch separately
            
            # First, get all quiz interactions
            interactions_url = f"{settings.SUPABASE_URL}/rest/v1/quiz_interactions"
            interactions_params = {
                "select": "quiz_id,is_correct,user_id"
            }
            if user_id:
                interactions_params["user_id"] = f"eq.{user_id}"
            interactions_response = await client.get(interactions_url, headers=headers, params=interactions_params)
            
            if interactions_response.status_code != 200:
                return []
            
            interactions = interactions_response.json()
            if not isinstance(interactions, list):
                return []
            
            # Get all quizzes with custom_name
            quizzes_url = f"{settings.SUPABASE_URL}/rest/v1/quizzes"
            quizzes_params = {
                "select": "id,custom_name"
            }
            quizzes_response = await client.get(quizzes_url, headers=headers, params=quizzes_params)
            
            if quizzes_response.status_code != 200:
                return []
            
            quizzes = quizzes_response.json()
            if not isinstance(quizzes, list):
                return []
            
            # Create a map of quiz_id to custom_name
            quiz_map = {}
            for quiz in quizzes:
                quiz_id = quiz.get("id")
                custom_name = quiz.get("custom_name") or f"Quiz {quiz_id[:8]}"
                quiz_map[quiz_id] = custom_name
            
            # Group interactions by quiz_id and calculate average score
            topic_stats = {}
            for interaction in interactions:
                quiz_id = interaction.get("quiz_id")
                is_correct = interaction.get("is_correct", False)
                
                if quiz_id not in quiz_map:
                    continue
                
                topic_name = quiz_map[quiz_id]
                
                if topic_name not in topic_stats:
                    topic_stats[topic_name] = {"total": 0, "correct": 0}
                
                topic_stats[topic_name]["total"] += 1
                if is_correct:
                    topic_stats[topic_name]["correct"] += 1
            
            # Calculate average scores
            result = []
            for topic_name, stats in topic_stats.items():
                average_score = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
                result.append(TopicPerformance(
                    topic_name=topic_name,
                    average_score=round(average_score, 2),
                    total_attempts=stats["total"]
                ))
            
            # Sort by average_score descending
            result.sort(key=lambda x: x.average_score, reverse=True)
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching quiz performance by topic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch quiz performance by topic: {str(e)}"
        )

@router.get("/analytics/most-attempted-topics", response_model=List[TopicAttempts])
async def get_most_attempted_topics(
    user_id: Optional[str] = Query(None, description="Filter by specific user ID"),
    admin_user: User = Depends(get_admin_user)
):
    """
    Get most attempted quiz topics (count of attempts per topic).
    Only accessible to admin users.
    Optionally filter by specific user_id.
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get all quiz interactions
            interactions_url = f"{settings.SUPABASE_URL}/rest/v1/quiz_interactions"
            interactions_params = {
                "select": "quiz_id"
            }
            if user_id:
                interactions_params["user_id"] = f"eq.{user_id}"
            interactions_response = await client.get(interactions_url, headers=headers, params=interactions_params)
            
            if interactions_response.status_code != 200:
                return []
            
            interactions = interactions_response.json()
            if not isinstance(interactions, list):
                return []
            
            # Get all quizzes with custom_name
            quizzes_url = f"{settings.SUPABASE_URL}/rest/v1/quizzes"
            quizzes_params = {
                "select": "id,custom_name"
            }
            quizzes_response = await client.get(quizzes_url, headers=headers, params=quizzes_params)
            
            if quizzes_response.status_code != 200:
                return []
            
            quizzes = quizzes_response.json()
            if not isinstance(quizzes, list):
                return []
            
            # Create a map of quiz_id to custom_name
            quiz_map = {}
            for quiz in quizzes:
                quiz_id = quiz.get("id")
                custom_name = quiz.get("custom_name") or f"Quiz {quiz_id[:8]}"
                quiz_map[quiz_id] = custom_name
            
            # Count attempts by topic
            topic_counts = {}
            for interaction in interactions:
                quiz_id = interaction.get("quiz_id")
                
                if quiz_id not in quiz_map:
                    continue
                
                topic_name = quiz_map[quiz_id]
                topic_counts[topic_name] = topic_counts.get(topic_name, 0) + 1
            
            # Convert to result format
            result = [
                TopicAttempts(topic_name=topic_name, attempt_count=count)
                for topic_name, count in topic_counts.items()
            ]
            
            # Sort by attempt_count descending
            result.sort(key=lambda x: x.attempt_count, reverse=True)
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching most attempted topics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch most attempted topics: {str(e)}"
        )

@router.get("/analytics/flashcard-difficulty", response_model=FlashcardDifficulty)
async def get_flashcard_difficulty(
    user_id: Optional[str] = Query(None, description="Filter by specific user ID"),
    admin_user: User = Depends(get_admin_user)
):
    """
    Get flashcard review difficulty distribution (again/good/easy counts).
    Only accessible to admin users.
    Optionally filter by specific user_id.
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get all flashcard reviews
            reviews_url = f"{settings.SUPABASE_URL}/rest/v1/flashcard_reviews"
            reviews_params = {
                "select": "rating"
            }
            if user_id:
                reviews_params["user_id"] = f"eq.{user_id}"
            reviews_response = await client.get(reviews_url, headers=headers, params=reviews_params)
            
            if reviews_response.status_code != 200:
                return FlashcardDifficulty(again_count=0, good_count=0, easy_count=0)
            
            reviews = reviews_response.json()
            if not isinstance(reviews, list):
                return FlashcardDifficulty(again_count=0, good_count=0, easy_count=0)
            
            # Count by rating
            again_count = 0
            good_count = 0
            easy_count = 0
            
            for review in reviews:
                rating = review.get("rating", "").lower()
                if rating == "again":
                    again_count += 1
                elif rating == "good":
                    good_count += 1
                elif rating == "easy":
                    easy_count += 1
            
            return FlashcardDifficulty(
                again_count=again_count,
                good_count=good_count,
                easy_count=easy_count
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching flashcard difficulty: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch flashcard difficulty: {str(e)}"
        )

@router.get("/analytics/daily-study-activity", response_model=List[DailyActivity])
async def get_daily_study_activity(
    days: int = Query(30, description="Number of days to retrieve", ge=1, le=365),
    user_id: Optional[str] = Query(None, description="Filter by specific user ID"),
    admin_user: User = Depends(get_admin_user)
):
    """
    Get daily study activity (quiz + flashcard activities per day).
    Only accessible to admin users.
    Optionally filter by specific user_id.
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Calculate date range
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days - 1)
            
            # Initialize date range dictionary
            date_range = {}
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.isoformat()
                date_range[date_str] = {"quiz_count": 0, "flashcard_count": 0}
                current_date += timedelta(days=1)
            
            # Get quiz interactions in date range
            interactions_url = f"{settings.SUPABASE_URL}/rest/v1/quiz_interactions"
            interactions_params = {
                "select": "answered_at",
                "answered_at.gte": f"{start_date}T00:00:00+00:00",
                "answered_at.lte": f"{end_date}T23:59:59+00:00"
            }
            if user_id:
                interactions_params["user_id"] = f"eq.{user_id}"
            interactions_response = await client.get(interactions_url, headers=headers, params=interactions_params)
            
            if interactions_response.status_code == 200:
                interactions = interactions_response.json()
                if isinstance(interactions, list):
                    # Count unique quiz interactions per day (group by user_id and quiz_id per day)
                    # For simplicity, we'll count all interactions per day
                    daily_quiz_counts = {}
                    for interaction in interactions:
                        answered_at = interaction.get("answered_at")
                        if answered_at:
                            # Parse date from timestamp
                            try:
                                dt = datetime.fromisoformat(answered_at.replace('Z', '+00:00'))
                                date_str = dt.date().isoformat()
                                daily_quiz_counts[date_str] = daily_quiz_counts.get(date_str, 0) + 1
                            except:
                                pass
                    
                    # Update date_range with quiz counts
                    for date_str, count in daily_quiz_counts.items():
                        if date_str in date_range:
                            date_range[date_str]["quiz_count"] = count
            
            # Get flashcard reviews in date range
            reviews_url = f"{settings.SUPABASE_URL}/rest/v1/flashcard_reviews"
            reviews_params = {
                "select": "reviewed_at",
                "reviewed_at.gte": f"{start_date}T00:00:00+00:00",
                "reviewed_at.lte": f"{end_date}T23:59:59+00:00"
            }
            if user_id:
                reviews_params["user_id"] = f"eq.{user_id}"
            reviews_response = await client.get(reviews_url, headers=headers, params=reviews_params)
            
            if reviews_response.status_code == 200:
                reviews = reviews_response.json()
                if isinstance(reviews, list):
                    # Count flashcard reviews per day
                    daily_flashcard_counts = {}
                    for review in reviews:
                        reviewed_at = review.get("reviewed_at")
                        if reviewed_at:
                            try:
                                dt = datetime.fromisoformat(reviewed_at.replace('Z', '+00:00'))
                                date_str = dt.date().isoformat()
                                daily_flashcard_counts[date_str] = daily_flashcard_counts.get(date_str, 0) + 1
                            except:
                                pass
                    
                    # Update date_range with flashcard counts
                    for date_str, count in daily_flashcard_counts.items():
                        if date_str in date_range:
                            date_range[date_str]["flashcard_count"] = count
            
            # Convert to result format
            result = []
            for date_str in sorted(date_range.keys()):
                data = date_range[date_str]
                result.append(DailyActivity(
                    date=date_str,
                    quiz_count=data["quiz_count"],
                    flashcard_count=data["flashcard_count"],
                    total_actions=data["quiz_count"] + data["flashcard_count"]
                ))
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching daily study activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch daily study activity: {str(e)}"
        )

