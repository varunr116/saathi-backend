"""
Authentication Routes - Magic link email authentication via Supabase
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import logging
from supabase import create_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Supabase client for auth operations
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ============================================
# Request/Response Models
# ============================================

class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    success: bool
    message: str


class VerifyTokenRequest(BaseModel):
    token: str
    type: str = "magiclink"  # or "recovery"


class AuthResponse(BaseModel):
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    error: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ============================================
# Routes
# ============================================

@router.post("/magic-link", response_model=MagicLinkResponse)
async def send_magic_link(request: MagicLinkRequest):
    """
    Send a magic link to the user's email for passwordless login.
    User clicks link → redirected to app → automatically logged in.
    """
    try:
        client = get_supabase_client()
        
        # Get the redirect URL from environment or use default
        redirect_url = os.getenv(
            "AUTH_REDIRECT_URL", 
            "saathiai://auth/callback"  # Deep link for mobile app
        )
        
        # Send magic link email
        response = client.auth.sign_in_with_otp({
            "email": request.email,
            "options": {
                "email_redirect_to": redirect_url
            }
        })
        
        logger.info(f"Magic link sent to {request.email}")
        
        return MagicLinkResponse(
            success=True,
            message=f"Magic link sent to {request.email}. Check your inbox!"
        )
        
    except Exception as e:
        logger.error(f"Magic link error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to send magic link: {str(e)}"
        )


@router.post("/verify", response_model=AuthResponse)
async def verify_token(request: VerifyTokenRequest):
    """
    Verify the magic link token and return session tokens.
    Called after user clicks the magic link.
    """
    try:
        client = get_supabase_client()
        
        # Verify the OTP token
        response = client.auth.verify_otp({
            "token": request.token,
            "type": request.type
        })
        
        if response.user and response.session:
            return AuthResponse(
                success=True,
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user_id=response.user.id,
                email=response.user.email
            )
        else:
            return AuthResponse(
                success=False,
                error="Invalid or expired token"
            )
            
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_session(request: RefreshTokenRequest):
    """
    Refresh the access token using a refresh token.
    """
    try:
        client = get_supabase_client()
        
        response = client.auth.refresh_session(request.refresh_token)
        
        if response.session:
            return AuthResponse(
                success=True,
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user_id=response.user.id if response.user else None,
                email=response.user.email if response.user else None
            )
        else:
            return AuthResponse(
                success=False,
                error="Failed to refresh session"
            )
            
    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        return AuthResponse(
            success=False,
            error=str(e)
        )


@router.post("/logout")
async def logout(authorization: str = Header(None)):
    """
    Sign out the current user.
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        client = get_supabase_client()
        client.auth.sign_out()
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# Helper: Get Current User from Token
# ============================================

async def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Dependency to get current user from Authorization header.
    Usage: user = Depends(get_current_user)
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        client = get_supabase_client()
        response = client.auth.get_user(token)
        
        if response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "token": token
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid token")
            
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_optional_user(authorization: str = Header(None)) -> Optional[dict]:
    """
    Dependency to optionally get current user.
    Returns None if not authenticated (doesn't raise error).
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        return await get_current_user(authorization)
    except:
        return None
