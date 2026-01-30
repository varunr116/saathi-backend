"""
Community Routes - SOS broadcast, responder actions, emergency management
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from .auth import get_current_user, get_optional_user
from ..services.supabase_service import supabase_service
from ..services.community_service import community_broadcast_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/community", tags=["Community"])


# ============================================
# Request/Response Models
# ============================================

class SOSEventResponse(BaseModel):
    id: str
    victim_name: Optional[str] = None
    street_address: Optional[str] = None
    latitude: Optional[float] = None  # Only shown to helpers
    longitude: Optional[float] = None  # Only shown to helpers
    status: str
    distance_meters: Optional[int] = None
    created_at: str
    my_action: Optional[str] = None  # What action current user has taken


class SOSDetailResponse(SOSEventResponse):
    """Extended response with full details (for helpers)"""
    victim_phone: Optional[str] = None
    responders_notified: int = 0
    actions: List[dict] = []


class AcknowledgeRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class OfferHelpRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    notes: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str  # 'en_route', 'arrived', 'helped', 'cancelled'
    notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ResolveSOSRequest(BaseModel):
    resolution_type: str  # 'self_cancelled', 'responder_helped', 'emergency_services', 'false_alarm'
    notes: Optional[str] = None


# ============================================
# Routes
# ============================================

@router.get("/active-sos", response_model=List[SOSEventResponse])
async def get_active_sos_events(user: dict = Depends(get_current_user)):
    """
    Get active SOS events that the current user has been notified about.
    Shows street-level location only (exact location revealed after offering help).
    """
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Get SOS events where user was notified
    try:
        # Query responder_actions for events user was notified about
        actions = await supabase_service.client.table("responder_actions").select(
            "sos_event_id, action_type, distance_meters, sos_events(*)"
        ).eq("responder_id", user["id"]).execute()
        
        # Group by event and get latest action per event
        events_map = {}
        for action in actions.data or []:
            event_id = action.get("sos_event_id")
            event_data = action.get("sos_events")
            
            if event_data and event_data.get("status") == "active":
                if event_id not in events_map:
                    events_map[event_id] = {
                        "event": event_data,
                        "my_action": action.get("action_type"),
                        "distance": action.get("distance_meters")
                    }
                else:
                    # Update to latest action
                    events_map[event_id]["my_action"] = action.get("action_type")
        
        # Build response
        result = []
        for event_id, data in events_map.items():
            event = data["event"]
            my_action = data["my_action"]
            
            response = SOSEventResponse(
                id=event["id"],
                victim_name=event.get("victim_name"),
                street_address=event.get("street_address"),
                status=event.get("status", "active"),
                distance_meters=data.get("distance"),
                created_at=event.get("created_at", ""),
                my_action=my_action
            )
            
            # Only reveal exact location if user has offered help
            if my_action == "offered_help":
                response.latitude = event.get("latitude")
                response.longitude = event.get("longitude")
            
            result.append(response)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting active SOS events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get SOS events")


@router.get("/sos/{event_id}", response_model=SOSDetailResponse)
async def get_sos_details(
    event_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get details of a specific SOS event.
    Full details (including exact location) only shown to users who offered help.
    """
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Get the event
    event = await supabase_service.get_sos_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="SOS event not found")
    
    # Check user's involvement
    has_offered_help = await supabase_service.has_user_responded(
        event_id, user["id"], "offered_help"
    )
    is_victim = event.get("victim_id") == user["id"]
    
    # Get user's action on this event
    my_action = None
    actions = await supabase_service.get_responder_actions(event_id)
    for action in actions:
        if action.get("responder_id") == user["id"]:
            my_action = action.get("action_type")
    
    # Build response
    response = SOSDetailResponse(
        id=event["id"],
        victim_name=event.get("victim_name"),
        street_address=event.get("street_address"),
        status=event.get("status", "active"),
        created_at=event.get("created_at", ""),
        my_action=my_action,
        responders_notified=event.get("responders_notified", 0),
        actions=actions if (has_offered_help or is_victim) else []
    )
    
    # Reveal exact location only to helpers or victim
    if has_offered_help or is_victim:
        response.latitude = event.get("latitude")
        response.longitude = event.get("longitude")
        response.victim_phone = event.get("victim_phone")
    
    return response


@router.post("/sos/{event_id}/acknowledge")
async def acknowledge_sos(
    event_id: str,
    request: AcknowledgeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Acknowledge seeing an SOS alert.
    This just logs that the user saw it - doesn't commit to helping.
    """
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Verify event exists and is active
    event = await supabase_service.get_sos_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="SOS event not found")
    if event.get("status") != "active":
        raise HTTPException(status_code=400, detail="SOS event is no longer active")
    
    # Check if already acknowledged
    already_acked = await supabase_service.has_user_responded(
        event_id, user["id"], "acknowledged"
    )
    if already_acked:
        return {"success": True, "message": "Already acknowledged"}
    
    # Log the acknowledgment
    await supabase_service.create_responder_action(
        sos_event_id=event_id,
        responder_id=user["id"],
        action_type="acknowledged",
        latitude=request.latitude,
        longitude=request.longitude
    )
    
    return {
        "success": True,
        "message": "SOS acknowledged",
        "event_id": event_id
    }


@router.post("/sos/{event_id}/offer-help")
async def offer_help(
    event_id: str,
    request: OfferHelpRequest,
    user: dict = Depends(get_current_user)
):
    """
    Offer to help with an SOS emergency.
    This reveals the exact location to the responder and notifies the victim.
    """
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Verify event exists and is active
    event = await supabase_service.get_sos_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="SOS event not found")
    if event.get("status") != "active":
        raise HTTPException(status_code=400, detail="SOS event is no longer active")
    
    # Can't help yourself
    if event.get("victim_id") == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot respond to your own SOS")
    
    # Check if already offered help
    already_offered = await supabase_service.has_user_responded(
        event_id, user["id"], "offered_help"
    )
    if already_offered:
        # Return the location anyway
        return {
            "success": True,
            "message": "Already offered help",
            "event_id": event_id,
            "victim_location": {
                "latitude": event.get("latitude"),
                "longitude": event.get("longitude"),
                "street_address": event.get("street_address")
            },
            "victim_name": event.get("victim_name"),
            "victim_phone": event.get("victim_phone")
        }
    
    # Calculate distance
    from math import radians, sin, cos, sqrt, atan2
    
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth's radius in meters
        phi1, phi2 = radians(lat1), radians(lat2)
        delta_phi = radians(lat2 - lat1)
        delta_lambda = radians(lon2 - lon1)
        a = sin(delta_phi/2)**2 + cos(phi1)*cos(phi2)*sin(delta_lambda/2)**2
        return int(2 * R * atan2(sqrt(a), sqrt(1-a)))
    
    distance = haversine(
        request.latitude, request.longitude,
        float(event.get("latitude", 0)), float(event.get("longitude", 0))
    )
    
    # Log the action
    await supabase_service.create_responder_action(
        sos_event_id=event_id,
        responder_id=user["id"],
        action_type="offered_help",
        latitude=request.latitude,
        longitude=request.longitude,
        distance_meters=distance,
        notes=request.notes
    )
    
    # Update user's response count
    profile = await supabase_service.get_profile(user["id"])
    if profile:
        await supabase_service.update_profile(user["id"], {
            "total_responses": (profile.get("total_responses", 0) or 0) + 1
        })
    
    # Notify the victim
    responder_name = profile.get("name") if profile else "A community member"
    await community_broadcast_service.notify_victim_help_offered(
        sos_event_id=event_id,
        responder_id=user["id"],
        responder_name=responder_name,
        distance_meters=distance
    )
    
    return {
        "success": True,
        "message": "Thank you for offering help!",
        "event_id": event_id,
        "victim_location": {
            "latitude": event.get("latitude"),
            "longitude": event.get("longitude"),
            "street_address": event.get("street_address")
        },
        "victim_name": event.get("victim_name"),
        "victim_phone": event.get("victim_phone"),
        "distance_meters": distance
    }


@router.post("/sos/{event_id}/update-status")
async def update_help_status(
    event_id: str,
    request: UpdateStatusRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update status of help being provided (en_route, arrived, helped, cancelled).
    """
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    valid_statuses = ["en_route", "arrived", "helped", "cancelled"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    # Verify user has offered help
    has_offered = await supabase_service.has_user_responded(
        event_id, user["id"], "offered_help"
    )
    if not has_offered:
        raise HTTPException(
            status_code=403, 
            detail="Must offer help before updating status"
        )
    
    # Log the action
    await supabase_service.create_responder_action(
        sos_event_id=event_id,
        responder_id=user["id"],
        action_type=request.status,
        latitude=request.latitude,
        longitude=request.longitude,
        notes=request.notes
    )
    
    # If helped, update successful_helps count
    if request.status == "helped":
        profile = await supabase_service.get_profile(user["id"])
        if profile:
            await supabase_service.update_profile(user["id"], {
                "successful_helps": (profile.get("successful_helps", 0) or 0) + 1
            })
    
    return {
        "success": True,
        "message": f"Status updated to: {request.status}",
        "event_id": event_id
    }


@router.post("/sos/{event_id}/resolve")
async def resolve_sos(
    event_id: str,
    request: ResolveSOSRequest,
    user: dict = Depends(get_current_user)
):
    """
    Mark an SOS event as resolved.
    Only the victim can resolve their own SOS.
    """
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    valid_types = ["self_cancelled", "responder_helped", "emergency_services", "false_alarm"]
    if request.resolution_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resolution type. Must be one of: {valid_types}"
        )
    
    # Get the event
    event = await supabase_service.get_sos_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="SOS event not found")
    
    # Verify ownership
    if event.get("victim_id") != user["id"]:
        raise HTTPException(
            status_code=403, 
            detail="Only the victim can resolve their SOS"
        )
    
    if event.get("status") != "active":
        raise HTTPException(status_code=400, detail="SOS is already resolved")
    
    # Resolve the event
    success = await supabase_service.resolve_sos_event(
        event_id=event_id,
        resolved_by=user["id"],
        resolution_type=request.resolution_type,
        notes=request.notes
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to resolve SOS")
    
    # Notify all responders that it's resolved
    notified = await community_broadcast_service.notify_sos_resolved(
        sos_event_id=event_id,
        resolution_type=request.resolution_type
    )
    
    return {
        "success": True,
        "message": "SOS resolved",
        "event_id": event_id,
        "responders_notified": notified
    }


@router.get("/my-responses")
async def get_my_responses(user: dict = Depends(get_current_user)):
    """
    Get SOS events where the current user has offered help.
    """
    if not supabase_service.is_configured():
        raise HTTPException(status_code=500, detail="Database not configured")
    
    responses = await supabase_service.get_user_active_responses(user["id"])
    
    return {
        "active_responses": responses,
        "count": len(responses)
    }
