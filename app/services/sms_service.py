"""
SMS Service - Twilio Integration for Emergency Alerts
"""
from twilio.rest import Client
from typing import Dict, Any, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS alerts via Twilio"""
    
    def __init__(self):
        """Initialize Twilio client"""
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.from_number = settings.TWILIO_PHONE_NUMBER
            self.enabled = True
            logger.info("[SMS] Twilio initialized successfully")
        else:
            self.client = None
            self.enabled = False
            logger.warning("[SMS] Twilio credentials not configured - SMS disabled")
    
    async def send_emergency_alert(
        self,
        to_number: str,
        user_name: str,
        location_link: str,
        coordinates: Dict[str, float],
        timestamp: str
    ) -> Dict[str, Any]:
        """
        Send emergency SMS alert
        
        Args:
            to_number: Recipient phone number (with country code, e.g., +919876543210)
            user_name: Name of person in emergency
            location_link: Google Maps link to location
            coordinates: Dict with 'latitude' and 'longitude'
            timestamp: ISO timestamp of emergency
        
        Returns:
            Dict with success status and message SID
        """
        if not self.enabled:
            logger.warning("[SMS] SMS service not enabled - skipping")
            return {
                "success": False,
                "error": "SMS service not configured"
            }
        
        try:
            # Format emergency message
            message_body = f"""⚠️ EMERGENCY ALERT from {user_name}

Location: {location_link}
GPS: {coordinates['latitude']}, {coordinates['longitude']}
Time: {timestamp}

This is an automated emergency alert from Saathi AI.
{user_name} needs immediate help.

Reply STOP to unsubscribe."""

            # Send SMS via Twilio
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=to_number
            )
            
            logger.info(f"[SMS] Emergency alert sent to {to_number} - SID: {message.sid}")
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "to": to_number
            }
            
        except Exception as e:
            logger.error(f"[SMS] Failed to send to {to_number}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "to": to_number
            }
    
    async def send_bulk_alerts(
        self,
        contacts: List[Dict[str, str]],
        user_name: str,
        location_link: str,
        coordinates: Dict[str, float],
        timestamp: str
    ) -> Dict[str, Any]:
        """
        Send emergency alerts to multiple contacts
        
        Args:
            contacts: List of dicts with 'phone' and 'name' keys
            user_name: Name of person in emergency
            location_link: Google Maps link
            coordinates: GPS coordinates
            timestamp: ISO timestamp
        
        Returns:
            Dict with overall success and individual results
        """
        results = []
        success_count = 0
        
        for contact in contacts:
            result = await self.send_emergency_alert(
                to_number=contact['phone'],
                user_name=user_name,
                location_link=location_link,
                coordinates=coordinates,
                timestamp=timestamp
            )
            
            result['contact_name'] = contact.get('name', 'Unknown')
            results.append(result)
            
            if result['success']:
                success_count += 1
        
        logger.info(f"[SMS] Sent {success_count}/{len(contacts)} emergency alerts")
        
        return {
            "success": success_count > 0,
            "total_contacts": len(contacts),
            "successful": success_count,
            "failed": len(contacts) - success_count,
            "results": results
        }
    
    async def send_cancellation_alert(
        self,
        to_number: str,
        user_name: str,
        reason: str = "False alarm"
    ) -> Dict[str, Any]:
        """Send SOS cancellation message"""
        if not self.enabled:
            return {"success": False, "error": "SMS not configured"}
        
        try:
            message_body = f"""✅ FALSE ALARM - {user_name} is safe

Previous emergency alert was: {reason}

{user_name} has cancelled the SOS alert and confirms they are safe.

- Saathi AI"""

            message = self.client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=to_number
            )
            
            logger.info(f"[SMS] Cancellation sent to {to_number}")
            
            return {
                "success": True,
                "message_sid": message.sid
            }
            
        except Exception as e:
            logger.error(f"[SMS] Cancellation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
sms_service = SMSService()
