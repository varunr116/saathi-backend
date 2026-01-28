"""
Emergency Routes - SOS Alert Endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging

from app.services.sms_service import sms_service
from app.services.email_service import email_service
from app.services.location_service import location_service

router = APIRouter(prefix="/api/emergency", tags=["Emergency"])
logger = logging.getLogger(__name__)


# Request/Response Models
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


class SOSAlert(BaseModel):
    """SOS Alert trigger request"""
    user_id: str = Field(..., min_length=1)
    user_name: str = Field(..., min_length=1, max_length=100)
    user_phone: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None
    contacts: List[EmergencyContact] = Field(..., min_items=1)
    medical_info: Optional[MedicalInfo] = None
    trigger_method: str = Field("voice", pattern=r'^(voice|button|gesture|smartwatch)$')
    
    @validator('contacts')
    def validate_contacts(cls, v):
        if not v:
            raise ValueError("At least one emergency contact required")
        return v


class LocationUpdate(BaseModel):
    """Location update during active SOS"""
    sos_id: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None


class SOSCancellation(BaseModel):
    """Cancel active SOS"""
    sos_id: str
    user_id: str
    reason: str = Field("False alarm", max_length=200)


# In-memory storage for active SOS alerts
# In production, use database
active_sos_alerts: Dict[str, Dict[str, Any]] = {}


@router.post("/sos/trigger")
async def trigger_sos(
    alert: SOSAlert,
    background_tasks: BackgroundTasks
):
    """
    Trigger emergency SOS alert
    
    Sends SMS and email to all emergency contacts with location
    """
    try:
        # Generate unique SOS ID
        sos_id = f"SOS-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.utcnow().isoformat()
        
        logger.info(f"[SOS] Alert triggered by {alert.user_name} - ID: {sos_id}")
        
        # Create Google Maps link
        location_link = location_service.create_google_maps_link(
            alert.latitude,
            alert.longitude
        )
        
        coordinates = {
            "latitude": alert.latitude,
            "longitude": alert.longitude
        }
        
        # Start location tracking
        tracking_result = location_service.start_sos_tracking(
            sos_id=sos_id,
            user_id=alert.user_id,
            initial_location=coordinates
        )
        
        # Prepare contact lists
        contacts_for_sms = [
            {"name": c.name, "phone": c.phone}
            for c in sorted(alert.contacts, key=lambda x: x.priority)
        ]
        
        contacts_for_email = [
            {"name": c.name, "email": c.email}
            for c in sorted(alert.contacts, key=lambda x: x.priority)
            if c.email
        ]
        
        # Send SMS alerts
        sms_results = await sms_service.send_bulk_alerts(
            contacts=contacts_for_sms,
            user_name=alert.user_name,
            location_link=location_link,
            coordinates=coordinates,
            timestamp=timestamp
        )
        
        # Send Email alerts
        medical_info_dict = None
        if alert.medical_info:
            medical_info_dict = alert.medical_info.dict()
        
        email_results = await email_service.send_bulk_alerts(
            contacts=contacts_for_email,
            user_name=alert.user_name,
            location_link=location_link,
            coordinates=coordinates,
            timestamp=timestamp,
            user_phone=alert.user_phone,
            medical_info=medical_info_dict
        )
        
        # Store active SOS alert
        active_sos_alerts[sos_id] = {
            "sos_id": sos_id,
            "user_id": alert.user_id,
            "user_name": alert.user_name,
            "triggered_at": timestamp,
            "status": "active",
            "trigger_method": alert.trigger_method,
            "location": coordinates,
            "contacts_alerted": len(alert.contacts)
        }
        
        logger.info(f"[SOS] Alert {sos_id} sent to {len(alert.contacts)} contacts")
        
        return {
            "success": True,
            "sos_id": sos_id,
            "timestamp": timestamp,
            "location_link": location_link,
            "alerts_sent": {
                "sms": sms_results,
                "email": email_results
            },
            "tracking_started": tracking_result.get("success", False),
            "message": f"Emergency alert sent to {len(alert.contacts)} contacts"
        }
        
    except Exception as e:
        logger.error(f"[SOS] Trigger failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger SOS: {str(e)}")


@router.post("/sos/location-update")
async def update_location(update: LocationUpdate):
    """
    Update location during active SOS
    
    Sends location update to emergency contacts
    """
    try:
        # Check if SOS is active
        if update.sos_id not in active_sos_alerts:
            raise HTTPException(status_code=404, detail="SOS alert not found or already cancelled")
        
        # Update location tracking
        result = location_service.update_sos_location(
            sos_id=update.sos_id,
            new_location={
                "latitude": update.latitude,
                "longitude": update.longitude,
                "accuracy": update.accuracy
            }
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to update location"))
        
        logger.info(f"[SOS] Location updated for {update.sos_id}")
        
        return {
            "success": True,
            "sos_id": update.sos_id,
            "location_count": result["location_count"],
            "latest_location": result["latest_location"],
            "message": "Location updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOS] Location update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update location: {str(e)}")


@router.post("/sos/cancel")
async def cancel_sos(cancellation: SOSCancellation):
    """
    Cancel active SOS alert
    
    Sends cancellation message to all emergency contacts
    """
    try:
        # Check if SOS exists
        if cancellation.sos_id not in active_sos_alerts:
            raise HTTPException(status_code=404, detail="SOS alert not found")
        
        sos_alert = active_sos_alerts[cancellation.sos_id]
        
        # Verify user
        if sos_alert["user_id"] != cancellation.user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to cancel this SOS")
        
        # Stop location tracking
        location_service.stop_sos_tracking(cancellation.sos_id)
        
        # Update status
        sos_alert["status"] = "cancelled"
        sos_alert["cancelled_at"] = datetime.utcnow().isoformat()
        sos_alert["cancellation_reason"] = cancellation.reason
        
        # Remove from active alerts
        del active_sos_alerts[cancellation.sos_id]
        
        logger.info(f"[SOS] Alert {cancellation.sos_id} cancelled - Reason: {cancellation.reason}")
        
        return {
            "success": True,
            "sos_id": cancellation.sos_id,
            "status": "cancelled",
            "message": "SOS alert cancelled successfully",
            "cancellation_reason": cancellation.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SOS] Cancellation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel SOS: {str(e)}")


@router.get("/sos/{sos_id}/status")
async def get_sos_status(sos_id: str):
    """Get status of an SOS alert"""
    if sos_id not in active_sos_alerts:
        raise HTTPException(status_code=404, detail="SOS alert not found or already cancelled")
    
    return {
        "success": True,
        **active_sos_alerts[sos_id]
    }


@router.get("/sos/{sos_id}/location-history")
async def get_location_history(sos_id: str):
    """Get full location tracking history for an SOS"""
    result = location_service.get_sos_location_history(sos_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail="SOS not found")
    
    return result


@router.get("/health")
async def emergency_health():
    """Health check for emergency services"""
    return {
        "service": "Emergency SOS",
        "status": "healthy",
        "active_alerts": len(active_sos_alerts),
        "sms_enabled": sms_service.enabled,
        "email_enabled": email_service.enabled
    }
