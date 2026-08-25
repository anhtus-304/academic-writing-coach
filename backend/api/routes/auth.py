from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import get_db
from security import create_access_token
from models.user import User
from services.auth_service import GoogleAuthService
from api.dependencies import get_current_user
from config import settings
import uuid, secrets

router = APIRouter(prefix="/auth", tags=["auth"])
google_auth_service = GoogleAuthService()

class DevLoginRequest(BaseModel):
    email: str = "demo@student.edu.vn"
    name: str = "Thúy Vi"

@router.get("/google/login")
async def google_login():
    state = secrets.token_urlsafe(16)
    auth_url = google_auth_service.get_authorization_url(state)
    return RedirectResponse(auth_url)

@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    try:
        token_data = await google_auth_service.fetch_token(code)
        user_info = await google_auth_service.get_user_info(token_data["access_token"])
    except Exception:
        raise HTTPException(status_code=400, detail="Google authentication failed")

    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Email not found")

    result = await db.execute(
        select(User).where((User.google_id == google_id) | (User.email == email))
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            display_name=name,
            google_id=google_id,
            avatar_url=picture,
            credit_balance=120
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if not user.google_id:
            user.google_id = google_id
        user.avatar_url = picture
        user.display_name = name
        await db.commit()
        await db.refresh(user)

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    frontend_url = "http://localhost:3000"
    if settings.BACKEND_CORS_ORIGINS:
        frontend_url = str(settings.BACKEND_CORS_ORIGINS[0]).rstrip("/")
    return RedirectResponse(f"{frontend_url}/auth/callback?token={access_token}")

@router.post("/dev-login")
async def dev_login(data: DevLoginRequest = DevLoginRequest(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=data.email,
            display_name=data.name,
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100",
            credit_balance=120
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.display_name,
            "avatar_url": user.avatar_url,
            "credits": user.credit_balance
        }
    }

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "credits": current_user.credit_balance
    }