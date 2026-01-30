"""
Emergency Routes - Updated SOS trigger with community broadcast integration
This extends your existing emergency.py - merge the changes or replace it.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import uuid

from .auth import get_optional_user
from ..services.supabase_service import supabase_service
from ..services.community_service import community_broadcast_service

# Import your existing services (adjust paths as needed)
# from ..services.sms_service import sms_service
# from ..services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/emergency", tags=["Emergency"])


# ============================================
# Request/Response Models
# ============================================

class EmergencyContact(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    priority: int = 1


class LocationData(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None
    timestamp: Optional[str] = None


class UserInfo(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None


class SOSTriggerRequest(BaseModel):
    user: UserInfo
    location: LocationData
    contacts: List[EmergencyContact]
    # New: Community broadcast settings
    community_broadcast: bool = True
    broadcast_radius_meters: int = Field(default=500, ge=100, le=5000)


class SOSTriggerResponse(BaseModel):
    success: bool
    sos_id: str
    message: str
    # New: Community stats
    community_broadcast_enabled: bool = False
    responders_notified: int = 0
    street_address: Optional[str] = None


# ============================================
# Background Tasks
# ============================================

async def broadcast_to_community(
    sos_event_id: str,
    victim_id: Optional[str],
    victim_name: str,
    latitude: float,
    longitude: float,
    radius_meters: int
):
    """Background task to broadcast SOS to nearby community responders"""
    try:
        result = await community_broadcast_service.broadcast_sos(
            sos_event_id=sos_event_id,
            victim_id=victim_id,
            victim_name=victim_name,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters
        )
        logger.info(f"Community broadcast result: {result}")
    except Exception as e:
        logger.error(f"Community broadcast failed: {e}")


# ============================================
# Routes
# ============================================

@router.post("/sos/trigger", response_model=SOSTriggerResponse)
async def trigger_sos(
    request: SOSTriggerRequest,
    background_tasks: BackgroundTasks,
    user: Optional[dict] = Depends(get_optional_user)
):
    """
    Trigger an SOS emergency alert.
    
    This will:
    1. Send SMS/email to emergency contacts (existing behavior)
    2. Create SOS event in database (new)
    3. Broadcast to nearby community responders (new)
    
    Works for both authenticated and unauthenticated users.
    """
    sos_id = str(uuid.uuid4())
    
    # Get authenticated user ID if available
    auth_user_id = user["id"] if user else None
    
    try:
        # ============================================
        # 1. EXISTING BEHAVIOR: Send alerts to contacts
        # ============================================
        # Keep your existing SMS/email logic here
        # Example (uncomment and adjust based on your existing code):
        
        # from ..services.sms_service import send_sms
        # from ..services.email_service import send_emergency_email
        # 
        # for contact in request.contacts:
        #     # Send SMS
        #     await send_sms(
        #         to=contact.phone,
        #         message=f"EMERGENCY: {request.user.name} needs help! "
        #                 f"Location: https://maps.google.com/?q={request.location.latitude},{request.location.longitude}"
        #     )
        #     
        #     # Send email
        #     if contact.email:
        #         await send_emergency_email(
        #             to=contact.email,
        #             victim_name=request.user.name,
        #             latitude=request.location.latitude,
        #             longitude=request.location.longitude
        #         )
        
        logger.info(f"SOS triggered by {request.user.name} at {request.location.latitude}, {request.location.longitude}")
        
        # ============================================
        # 2. NEW: Create SOS event in Supabase
        # ============================================
        community_result = {
            "responders_notified": 0,
            "street_address": None
        }
        
        if supabase_service.is_configured() and request.community_broadcast:
            # Get street-level address first
            street_address = await community_broadcast_service.get_street_level_address(
                request.location.latitude,
                request.location.longitude
            )
            
            # Create SOS event
            sos_event = await supabase_service.create_sos_event(
                victim_id=auth_user_id,
                victim_name=request.user.name,
                victim_phone=request.user.phone,
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                street_address=street_address,
                community_broadcast=request.community_broadcast,
                broadcast_radius=request.broadcast_radius_meters
            )
            
            if sos_event:
                sos_id = sos_event.get("id", sos_id)
                
                # Update victim's SOS count if authenticated
                if auth_user_id:
                    profile = await supabase_service.get_profile(auth_user_id)
                    if profile:
                        await supabase_service.update_profile(auth_user_id, {
                            "total_sos_triggered": (profile.get("total_sos_triggered", 0) or 0) + 1
                        })
                
                # ============================================
                # 3. NEW: Broadcast to community (background)
                # ============================================
                background_tasks.add_task(
                    broadcast_to_community,
                    sos_event_id=sos_id,
                    victim_id=auth_user_id,
                    victim_name=request.user.name,
                    latitude=request.location.latitude,
                    longitude=request.location.longitude,
                    radius_meters=request.broadcast_radius_meters
                )
                
                community_result["street_address"] = street_address
                # Note: responders_notified will be updated by background task
        
        return SOSTriggerResponse(
            success=True,
            sos_id=sos_id,
            message="SOS alert sent successfully",
            community_broadcast_enabled=request.community_broadcast and supabase_service.is_configured(),
            responders_notified=community_result["responders_notified"],
            street_address=community_result["street_address"]
        )
        
    except Exception as e:
        logger.error(f"SOS trigger error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger SOS: {str(e)}"
        )


@router.post("/sos/cancel/{sos_id}")
async def cancel_sos(
    sos_id: str,
    user: Optional[dict] = Depends(get_optional_user)
):
    """
    Cancel an active SOS alert.
    """
    try:
        if supabase_service.is_configured():
            # Get the event
            event = await supabase_service.get_sos_event(sos_id)
            
            if not event:
                # If not in Supabase, it might be an old-style SOS
                return {"success": True, "message": "SOS cancelled"}
            
            # Verify ownership if authenticated
            if user and event.get("victim_id") and event.get("victim_id") != user["id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot cancel another user's SOS"
                )
            
            # Resolve as self-cancelled
            await supabase_service.resolve_sos_event(
                event_id=sos_id,
                resolved_by=user["id"] if user else None,
                resolution_type="self_cancelled",
                notes="Cancelled by user"
            )
            
            # Notify responders
            notified = await community_broadcast_service.notify_sos_resolved(
                sos_event_id=sos_id,
                resolution_type="self_cancelled"
            )
            
            return {
                "success": True,
                "message": "SOS cancelled",
                "responders_notified": notified
            }
        
        return {"success": True, "message": "SOS cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SOS cancel error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel SOS: {str(e)}"
        )


@router.get("/sos/{sos_id}/status")
async def get_sos_status(
    sos_id: str,
    user: Optional[dict] = Depends(get_optional_user)
):
    """
    Get status of an SOS event including responder activity.
    """
    try:
        if not supabase_service.is_configured():
            return {
                "sos_id": sos_id,
                "status": "unknown",
                "message": "Community features not configured"
            }
        
        event = await supabase_service.get_sos_event(sos_id)
        
        if not event:
            raise HTTPException(status_code=404, detail="SOS event not found")
        
        # Get responder actions
        actions = await supabase_service.get_responder_actions(sos_id)
        
        # Count helpers
        helpers_offering = 0
        helpers_en_route = 0
        helpers_arrived = 0
        
        for action in actions:
            action_type = action.get("action_type")
            if action_type == "offered_help":
                helpers_offering += 1
            elif action_type == "en_route":
                helpers_en_route += 1
            elif action_type == "arrived":
                helpers_arrived += 1
        
        return {
            "sos_id": sos_id,
            "status": event.get("status", "unknown"),
            "created_at": event.get("created_at"),
            "resolved_at": event.get("resolved_at"),
            "resolution_type": event.get("resolution_type"),
            "street_address": event.get("street_address"),
            "responders_notified": event.get("responders_notified", 0),
            "helpers_offering": helpers_offering,
            "helpers_en_route": helpers_en_route,
            "helpers_arrived": helpers_arrived,
            "total_actions": len(actions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SOS status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get SOS status: {str(e)}"
        )


@router.post("/sos/{sos_id}/location-update")
async def update_sos_location(
    sos_id: str,
    location: LocationData,
    user: Optional[dict] = Depends(get_optional_user)
):
    """
    Update location during an active SOS.
    """
    try:
        if supabase_service.is_configured():
            event = await supabase_service.get_sos_event(sos_id)
            
            if not event:
                return {"success": False, "message": "SOS event not found"}
            
            if event.get("status") != "active":
                return {"success": False, "message": "SOS is no longer active"}
            
            # Update location
            street_address = await community_broadcast_service.get_street_level_address(
                location.latitude,
                location.longitude
            )
            
            await supabase_service.update_sos_event(sos_id, {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "street_address": street_address
            })
            
            # TODO: Notify active helpers of location update
            
            return {
                "success": True,
                "message": "Location updated",
                "street_address": street_address
            }
        
        return {"success": True, "message": "Location update received"}
        
    except Exception as e:
        logger.error(f"Location update error: {e}")
        return {"success": False, "message": str(e)}


@router.get("/health")
async def emergency_health():
    """Health check for emergency services"""
    return {
        "status": "ok",
        "supabase_configured": supabase_service.is_configured(),
        "timestamp": datetime.utcnow().isoformat()
    }
