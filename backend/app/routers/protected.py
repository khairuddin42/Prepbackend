import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
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


class UpdateFullNameRequest(BaseModel):
    full_name: str

    @validator('full_name')
    def validate_full_name(cls, v):
        if len(v.strip()) > 80:
            raise ValueError('Full name must be less than 80 characters')
        return v.strip()


class ProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str


def _service_headers(extra: Optional[dict] = None) -> dict:
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
    }
    if extra:
        headers.update(extra)
    return headers


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


async def _compute_quiz_stats(client: httpx.AsyncClient, user_id: str) -> dict:
    """Return total distinct quizzes completed and overall accuracy (average score)."""
    try:
        resp = await client.get(
            f"{settings.SUPABASE_URL}/rest/v1/quiz_interactions",
            headers=_service_headers({"Content-Type": "application/json"}),
            params={
                "user_id": f"eq.{user_id}",
                "select": "quiz_id,is_correct",
            },
        )
        if resp.status_code != 200:
            return {"total_quizzes_taken": 0, "average_score": 0.0}

        interactions = resp.json()
        if not interactions:
            return {"total_quizzes_taken": 0, "average_score": 0.0}

        total_attempted = len(interactions)
        total_correct = sum(1 for i in interactions if i.get("is_correct", False))
        distinct_quizzes = len({i.get("quiz_id") for i in interactions if i.get("quiz_id")})
        average_score = (total_correct / total_attempted * 100) if total_attempted > 0 else 0.0

        return {
            "total_quizzes_taken": distinct_quizzes,
            "average_score": round(average_score, 1),
        }
    except Exception:
        return {"total_quizzes_taken": 0, "average_score": 0.0}


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's full profile, including avatar, full name, streak and quiz stats.
    """
    profile_row: dict = {}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles",
                headers=_service_headers({"Content-Type": "application/json"}),
                params={
                    "user_id": f"eq.{current_user.id}",
                    "select": "username,full_name,profile_picture_url,current_streak,longest_streak,created_at",
                    "limit": "1",
                },
            )
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    profile_row = rows[0]

            quiz_stats = await _compute_quiz_stats(client, current_user.id)
    except httpx.RequestError:
        quiz_stats = {"total_quizzes_taken": 0, "average_score": 0.0}

    def _as_int(value) -> int:
        try:
            return int(value) if value is not None else 0
        except (ValueError, TypeError):
            return 0

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "user_id": current_user.id,
            "username": profile_row.get("username") or current_user.username,
            "email": current_user.email,
            "full_name": profile_row.get("full_name"),
            "avatar_url": profile_row.get("profile_picture_url"),
            "study_streak": _as_int(profile_row.get("current_streak")),
            "longest_streak": _as_int(profile_row.get("longest_streak")),
            "total_quizzes_taken": quiz_stats["total_quizzes_taken"],
            "average_score": quiz_stats["average_score"],
            "created_at": profile_row.get("created_at"),
        },
    )


@router.api_route("/profile/username", methods=["PUT", "PATCH"], response_model=ProfileResponse)
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
                headers=_service_headers(),
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
                headers=_service_headers({
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                }),
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


@router.api_route("/profile/fullname", methods=["PUT", "PATCH"])
async def update_full_name(
    request: UpdateFullNameRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update user's full name.
    """
    try:
        async with httpx.AsyncClient() as client:
            update_response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{current_user.id}",
                headers=_service_headers({
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                }),
                json={
                    "full_name": request.full_name or None,
                    "updated_at": "now()",
                },
            )

            if update_response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update full name",
                )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"full_name": request.full_name},
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile service unavailable",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update full name: {str(e)}",
        )


_ALLOWED_AVATAR_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
_EXT_TO_CONTENT_TYPE = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}
_AVATAR_BUCKET = "avatars"
_MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5MB


def _resolve_avatar_type(content_type: str, filename: Optional[str]) -> Optional[tuple]:
    """Return (normalized_content_type, extension) or None if unsupported.

    Falls back to the filename extension when the client sends a generic
    content type such as application/octet-stream (common from mobile uploads).
    """
    content_type = (content_type or "").lower()
    if content_type in _ALLOWED_AVATAR_TYPES:
        return content_type, _ALLOWED_AVATAR_TYPES[content_type]

    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in _EXT_TO_CONTENT_TYPE:
            return _EXT_TO_CONTENT_TYPE[ext], "jpg" if ext == "jpeg" else ext

    return None


async def _ensure_avatar_bucket(client: httpx.AsyncClient) -> None:
    """Create the public avatars bucket if it does not already exist (idempotent)."""
    try:
        await client.post(
            f"{settings.SUPABASE_URL}/storage/v1/bucket",
            headers=_service_headers({"Content-Type": "application/json"}),
            json={
                "id": _AVATAR_BUCKET,
                "name": _AVATAR_BUCKET,
                "public": True,
                "file_size_limit": _MAX_AVATAR_BYTES,
            },
        )
    except Exception:
        # Bucket likely already exists; ignore.
        pass


@router.post("/profile/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a profile picture to Supabase Storage and save its public URL.
    """
    resolved = _resolve_avatar_type(avatar.content_type or "", avatar.filename)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Use JPG, PNG, WEBP, or GIF.",
        )
    content_type, ext = resolved

    file_bytes = await avatar.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded.",
        )
    if len(file_bytes) > _MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large (>5MB).",
        )

    object_path = f"profile-pictures/{current_user.id}-{int(time.time())}.{ext}"

    try:
        async with httpx.AsyncClient() as client:
            await _ensure_avatar_bucket(client)

            upload_response = await client.post(
                f"{settings.SUPABASE_URL}/storage/v1/object/{_AVATAR_BUCKET}/{object_path}",
                headers=_service_headers({
                    "Content-Type": content_type,
                    "x-upsert": "true",
                    "cache-control": "3600",
                }),
                content=file_bytes,
            )

            if upload_response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload avatar: {upload_response.text}",
                )

            public_url = (
                f"{settings.SUPABASE_URL}/storage/v1/object/public/"
                f"{_AVATAR_BUCKET}/{object_path}"
            )

            update_response = await client.patch(
                f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{current_user.id}",
                headers=_service_headers({
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                }),
                json={
                    "profile_picture_url": public_url,
                    "updated_at": "now()",
                },
            )

            if update_response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Avatar uploaded but failed to save URL.",
                )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"avatar_url": public_url},
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service unavailable",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}",
        )


@router.delete("/account")
async def delete_account(current_user: User = Depends(get_current_user)):
    """
    Permanently delete the current user's account and profile.

    Deletes the Supabase auth user via the admin API using the service role key.
    Related rows in user_profiles and user content are removed via the database's
    ON DELETE CASCADE foreign keys against auth.users.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Best-effort removal of the profile row first (in case no cascade).
            try:
                await client.delete(
                    f"{settings.SUPABASE_URL}/rest/v1/user_profiles?user_id=eq.{current_user.id}",
                    headers=_service_headers({"Prefer": "return=minimal"}),
                )
            except Exception:
                pass

            delete_response = await client.delete(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users/{current_user.id}",
                headers=_service_headers(),
            )

            if delete_response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete account: {delete_response.text}",
                )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"deleted": True},
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account service unavailable",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}",
        )
