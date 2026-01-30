"""
User Routes - Profile management, location updates, responder settings
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from .auth import get_current_user
from ..services.supabase_service import supabase_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


# ============================================
# Request/Response Models
# ============================================

class EmergencyContact(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    relationship: Optional[str] = None
    priority: int = 1


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    emergency_contacts: Optional[List[EmergencyContact]] = None


class ProfileResponse(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    is_responder_enabled: bool = False
    responder_radius_meters: int = 500
    emergency_contacts: List[dict] = []
    total_sos_triggered: int = 0
    total_responses: int = 0
    successful_helps: int = 0
    has_location: bool = False
    created_at: Optional[str] = None


class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ResponderSettings(BaseModel):
    is_enabled: bool
    radius_meters: int = Field(default=500, ge=100, le=5000)


class FCMTokenUpdate(BaseModel):
    fcm_token: str


# ============================================
# Routes
# ============================================

@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    profile = await supabase_service.get_profile(user["id"])
    
    if not profile:
        # Profile should auto-create on signup, but handle edge case
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return ProfileResponse(
        id=profile["id"],
        email=user.get("email"),
        name=profile.get("name"),
        phone=profile.get("phone"),
        is_responder_enabled=profile.get("is_responder_enabled", False),
        responder_radius_meters=profile.get("responder_radius_meters", 500),
        emergency_contacts=profile.get("emergency_contacts", []),
        total_sos_triggered=profile.get("total_sos_triggered", 0),
        total_responses=profile.get("total_responses", 0),
        successful_helps=profile.get("successful_helps", 0),
        has_location=profile.get("current_location") is not None,
        created_at=profile.get("created_at")
    )


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    update: ProfileUpdate,
    user: dict = Depends(get_current_user)
):
    """Update current user's profile"""
    
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Build update data (only include non-None fields)
    update_data = {}
    if update.name is not None:
        update_data["name"] = update.name
    if update.phone is not None:
        update_data["phone"] = update.phone
    if update.emergency_contacts is not None:
        update_data["emergency_contacts"] = [c.dict() for c in update.emergency_contacts]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    profile = await supabase_service.update_profile(user["id"], update_data)
    
    if not profile:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    
    return ProfileResponse(
        id=profile["id"],
        email=user.get("email"),
        name=profile.get("name"),
        phone=profile.get("phone"),
        is_responder_enabled=profile.get("is_responder_enabled", False),
        responder_radius_meters=profile.get("responder_radius_meters", 500),
        emergency_contacts=profile.get("emergency_contacts", []),
        total_sos_triggered=profile.get("total_sos_triggered", 0),
        total_responses=profile.get("total_responses", 0),
        successful_helps=profile.get("successful_helps", 0),
        has_location=profile.get("current_location") is not None,
        created_at=profile.get("created_at")
    )


@router.put("/location")
async def update_my_location(
    location: LocationUpdate,
    user: dict = Depends(get_current_user)
):
    """Update current user's location"""
    
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    success = await supabase_service.update_user_location(
        user_id=user["id"],
        latitude=location.latitude,
        longitude=location.longitude
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update location")
    
    return {
        "success": True,
        "message": "Location updated",
        "latitude": location.latitude,
        "longitude": location.longitude
    }


@router.put("/responder-settings")
async def update_responder_settings(
    settings: ResponderSettings,
    user: dict = Depends(get_current_user)
):
    """Enable/disable responder mode and set radius"""
    
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    success = await supabase_service.set_responder_settings(
        user_id=user["id"],
        is_enabled=settings.is_enabled,
        radius_meters=settings.radius_meters
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update settings")
    
    status = "enabled" if settings.is_enabled else "disabled"
    
    return {
        "success": True,
        "message": f"Responder mode {status}",
        "is_responder_enabled": settings.is_enabled,
        "responder_radius_meters": settings.radius_meters
    }


@router.put("/fcm-token")
async def update_fcm_token(
    data: FCMTokenUpdate,
    user: dict = Depends(get_current_user)
):
    """Update FCM token for push notifications"""
    
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    success = await supabase_service.update_fcm_token(
        user_id=user["id"],
        fcm_token=data.fcm_token
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update FCM token")
    
    return {
        "success": True,
        "message": "FCM token registered"
    }


@router.get("/stats")
async def get_my_stats(user: dict = Depends(get_current_user)):
    """Get user's community stats"""
    
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    profile = await supabase_service.get_profile(user["id"])
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {
        "total_sos_triggered": profile.get("total_sos_triggered", 0),
        "total_responses": profile.get("total_responses", 0),
        "successful_helps": profile.get("successful_helps", 0),
        "is_responder_enabled": profile.get("is_responder_enabled", False)
    }
