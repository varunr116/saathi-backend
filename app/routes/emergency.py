"""
Emergency Routes - SOS Alert with SMS/Email + Community Broadcast
Merged version: Original SMS/Email + New Community Features
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging

# Original services (SMS/Email)
from app.services.sms_service import sms_service
from app.services.email_service import email_service
from app.services.location_service import location_service

# New services (Community)
from app.services.supabase_service import supabase_service
from app.services.community_service import community_broadcast_service
from app.routes.auth import get_optional_user

router = APIRouter(prefix="/api/emergency", tags=["Emergency"])
logger = logging.getLogger(__name__)


# ============================================
# Request/Response Models
# ============================================

class EmergencyContact(BaseModel):
    """Emergency contact model"""
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')  # E.164 format
    email: Optional[str] = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    relationship: Optional[str] = None
    priority: int = Field(1, ge=1, le=10)


class MedicalInfo(BaseModel):
    """User medical information"""
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    conditions: Optional[str] = None


class LocationData(BaseModel):
    """Location coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None
    timestamp: Optional[str] = None


class UserInfo(BaseModel):
    """User information"""
    name: str = Field(..., min_length=1, max_length=100)
    phone: str
    email: Optional[str] = None


class SOSTriggerRequest(BaseModel):
    """SOS trigger request - supports both old and new mobile app format"""
    # New format (nested objects)
    user: Optional[UserInfo] = None
    location: Optional[LocationData] = None
    
    # Old format (flat fields) - for backward compatibility
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    trigger_method: Optional[str] = "voice"
    
    # Common fields
    contacts: List[EmergencyContact] = Field(..., min_items=1)
    medical_info: Optional[MedicalInfo] = None
    
    # New: Community broadcast
    community_broadcast: bool = True
    broadcast_radius_meters: int = Field(default=500, ge=100, le=5000)
    
    @validator('contacts')
    def validate_contacts(cls, v):
        if not v:
            raise ValueError("At least one emergency contact required")
        return v


class SOSTriggerResponse(BaseModel):
    """SOS trigger response"""
    success: bool
    sos_id: str
    timestamp: str
    location_link: str
    alerts_sent: Dict[str, Any]
    tracking_started: bool
    message: str
    # New fields
    community_broadcast_enabled: bool = False
    responders_notified: int = 0
    street_address: Optional[str] = None


# In-memory storage for active SOS alerts
active_sos_alerts: Dict[str, Dict[str, Any]] = {}


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
        logger.info(f"[SOS] Community broadcast: {result['responders_notified']} notified")
    except Exception as e:
        logger.error(f"[SOS] Community broadcast failed: {e}")


# ============================================
# Main SOS Trigger Endpoint
# ============================================

@router.post("/sos/trigger", response_model=SOSTriggerResponse)
async def trigger_sos(
    request: SOSTriggerRequest,
    background_tasks: BackgroundTasks,
    user: Optional[dict] = Depends(get_optional_user)
):
    """
    Trigger emergency SOS alert
    
    This endpoint:
    1. Sends SMS to all emergency contacts (Twilio)
    2. Sends email to all emergency contacts (SendGrid)
    3. Creates SOS event in Supabase
    4. Broadcasts to nearby community responders (push notifications)
    
    Supports both authenticated and unauthenticated users.
    Supports both old (flat) and new (nested) payload formats.
    """
    try:
        # ============================================
        # Parse request (support both formats)
        # ============================================
        if request.user and request.location:
            # New format (nested objects)
            user_name = request.user.name
            user_phone = request.user.phone
            user_email = request.user.email
            latitude = request.location.latitude
            longitude = request.location.longitude
            accuracy = request.location.accuracy
            user_id = user["id"] if user else None
        else:
            # Old format (flat fields)
            user_name = request.user_name
            user_phone = request.user_phone
            user_email = None
            latitude = request.latitude
            longitude = request.longitude
            accuracy = request.accuracy
            user_id = request.user_id or (user["id"] if user else None)
        
        # Generate SOS ID
        sos_id = f"SOS-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.utcnow().isoformat()
        
        logger.info(f"[SOS] Triggered by {user_name} at ({latitude}, {longitude})")
        
        # ============================================
        # 1. SEND SMS ALERTS (Original behavior)
        # ============================================
        location_link = location_service.create_google_maps_link(latitude, longitude)
        coordinates = {"latitude": latitude, "longitude": longitude}
        
        # Start location tracking
        tracking_result = location_service.start_sos_tracking(
            sos_id=sos_id,
            user_id=user_id or "anonymous",
            initial_location=coordinates
        )
        
        # Send SMS
        contacts_for_sms = [
            {"name": c.name, "phone": c.phone}
            for c in sorted(request.contacts, key=lambda x: x.priority)
        ]
        
        sms_results = await sms_service.send_bulk_alerts(
            contacts=contacts_for_sms,
            user_name=user_name,
            location_link=location_link,
            coordinates=coordinates,
            timestamp=timestamp
        )
        
        # ============================================
        # 2. SEND EMAIL ALERTS (Original behavior)
        # ============================================
        contacts_for_email = [
            {"name": c.name, "email": c.email}
            for c in sorted(request.contacts, key=lambda x: x.priority)
            if c.email
        ]
        
        medical_info_dict = None
        if request.medical_info:
            medical_info_dict = request.medical_info.dict()
        
        email_results = await email_service.send_bulk_alerts(
            contacts=contacts_for_email,
            user_name=user_name,
            location_link=location_link,
            coordinates=coordinates,
            timestamp=timestamp,
            user_phone=user_phone,
            medical_info=medical_info_dict
        )
        
        # ============================================
        # 3. CREATE SOS EVENT IN SUPABASE (New)
        # ============================================
        community_result = {
            "responders_notified": 0,
            "street_address": None,
            "broadcast_enabled": False
        }
        
        if supabase_service.is_configured() and request.community_broadcast:
            # Get street-level address
            street_address = await community_broadcast_service.get_street_level_address(
                latitude, longitude
            )
            
            # Create SOS event in database
            sos_event = await supabase_service.create_sos_event(
                victim_id=user_id,
                victim_name=user_name,
                victim_phone=user_phone,
                latitude=latitude,
                longitude=longitude,
                street_address=street_address,
                community_broadcast=request.community_broadcast,
                broadcast_radius=request.broadcast_radius_meters
            )
            
            if sos_event:
                sos_id = sos_event.get("id", sos_id)  # Use Supabase ID if available
                
                # Update user's SOS count if authenticated
                if user_id:
                    profile = await supabase_service.get_profile(user_id)
                    if profile:
                        await supabase_service.update_profile(user_id, {
                            "total_sos_triggered": (profile.get("total_sos_triggered", 0) or 0) + 1
                        })
                
                # ============================================
                # 4. BROADCAST TO COMMUNITY (Background)
                # ============================================
                background_tasks.add_task(
                    broadcast_to_community,
                    sos_event_id=sos_id,
                    victim_id=user_id,
                    victim_name=user_name,
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=request.broadcast_radius_meters
                )
                
                community_result["street_address"] = street_address
                community_result["broadcast_enabled"] = True
        
        # Store in memory (for backward compatibility)
        active_sos_alerts[sos_id] = {
            "sos_id": sos_id,
            "user_id": user_id or "anonymous",
            "user_name": user_name,
            "triggered_at": timestamp,
            "status": "active",
            "trigger_method": request.trigger_method or "voice",
            "location": coordinates,
            "contacts_alerted": len(request.contacts)
        }
        
        logger.info(f"[SOS] Alert {sos_id} sent to {len(request.contacts)} contacts")
        
        return SOSTriggerResponse(
            success=True,
            sos_id=sos_id,
            timestamp=timestamp,
            location_link=location_link,
            alerts_sent={
                "sms": sms_results,
                "email": email_results
            },
            tracking_started=tracking_result.get("success", False),
            message=f"Emergency alert sent to {len(request.contacts)} contacts",
            community_broadcast_enabled=community_result["broadcast_enabled"],
            responders_notified=community_result["responders_notified"],
            street_address=community_result["street_address"]
        )
        
    except Exception as e:
        logger.error(f"[SOS] Trigger failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger SOS: {str(e)}"
        )


# ============================================
# Other Endpoints (Keep original behavior)
# ============================================

@router.post("/sos/location-update")
async def update_location(
    sos_id: str,
    latitude: float,
    longitude: float,
    accuracy: Optional[float] = None
):
    """Update location during active SOS"""
    try:
        if sos_id not in active_sos_alerts:
            raise HTTPException(status_code=404, detail="SOS alert not found")
        
        result = location_service.update_sos_location(
            sos_id=sos_id,
            new_location={
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy
            }
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        # Also update in Supabase if configured
        if supabase_service.is_configured():
            street_address = await community_broadcast_service.get_street_level_address(
                latitude, longitude
            )
            await supabase_service.update_sos_event(sos_id, {
                "latitude": latitude,
                "longitude": longitude,
                "street_address": street_address
            })
        
        return {
            "success": True,
            "sos_id": sos_id,
            "location_count": result["location_count"],
            "message": "Location updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOS] Location update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sos/cancel/{sos_id}")
async def cancel_sos(
    sos_id: str,
    user: Optional[dict] = Depends(get_optional_user)
):
    """Cancel active SOS alert"""
    try:
        if sos_id not in active_sos_alerts:
            if supabase_service.is_configured():
                event = await supabase_service.get_sos_event(sos_id)
                if not event:
                    raise HTTPException(status_code=404, detail="SOS not found")
            else:
                raise HTTPException(status_code=404, detail="SOS not found")
        
        # Stop location tracking
        location_service.stop_sos_tracking(sos_id)
        
        # Update Supabase
        if supabase_service.is_configured():
            await supabase_service.resolve_sos_event(
                event_id=sos_id,
                resolved_by=user["id"] if user else None,
                resolution_type="self_cancelled",
                notes="Cancelled by user"
            )
            
            # Notify responders
            await community_broadcast_service.notify_sos_resolved(
                sos_event_id=sos_id,
                resolution_type="self_cancelled"
            )
        
        # Remove from memory
        if sos_id in active_sos_alerts:
            del active_sos_alerts[sos_id]
        
        return {
            "success": True,
            "sos_id": sos_id,
            "status": "cancelled",
            "message": "SOS cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOS] Cancel failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sos/{sos_id}/status")
async def get_sos_status(sos_id: str):
    """Get SOS status"""
    # Check memory first
    if sos_id in active_sos_alerts:
        return {"success": True, **active_sos_alerts[sos_id]}
    
    # Check Supabase
    if supabase_service.is_configured():
        event = await supabase_service.get_sos_event(sos_id)
        if event:
            actions = await supabase_service.get_responder_actions(sos_id)
            return {
                "success": True,
                "sos_id": sos_id,
                "status": event.get("status"),
                "created_at": event.get("created_at"),
                "responders_notified": event.get("responders_notified", 0),
                "total_actions": len(actions)
            }
    
    raise HTTPException(status_code=404, detail="SOS not found")


@router.get("/health")
async def emergency_health():
    """Health check"""
    return {
        "service": "Emergency SOS",
        "status": "healthy",
        "active_alerts": len(active_sos_alerts),
        "sms_enabled": sms_service.enabled,
        "email_enabled": email_service.enabled,
        "supabase_configured": supabase_service.is_configured()
    }