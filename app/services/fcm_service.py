"""
Firebase Cloud Messaging Service - Push notifications for Community Safety Network
"""
import os
import json
import logging
from typing import List, Dict, Optional
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)


class FCMService:
    def __init__(self):
        self.initialized = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if already initialized
            try:
                firebase_admin.get_app()
                self.initialized = True
                return
            except ValueError:
                pass
            
            # Try to get credentials from environment
            cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
            cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            
            if cred_json:
                # Credentials provided as JSON string
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
            elif cred_path and os.path.exists(cred_path):
                # Credentials provided as file path
                cred = credentials.Certificate(cred_path)
            else:
                logger.warning("Firebase credentials not configured")
                return
            
            firebase_admin.initialize_app(cred)
            self.initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.initialized = False
    
    def is_configured(self) -> bool:
        return self.initialized
    
    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        priority: str = "high"
    ) -> bool:
        """Send push notification to a single device"""
        if not self.initialized:
            logger.warning("FCM not initialized, skipping notification")
            return False
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=token,
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        icon="ic_notification",
                        color="#FF6F00",
                        sound="emergency",
                        channel_id="emergency_channel",
                        priority="max" if priority == "high" else "default"
                    )
                )
            )
            
            response = messaging.send(message)
            logger.info(f"FCM notification sent: {response}")
            return True
            
        except messaging.UnregisteredError:
            logger.warning(f"FCM token no longer valid: {token[:20]}...")
            return False
        except Exception as e:
            logger.error(f"FCM send error: {e}")
            return False
    
    async def send_sos_alert(
        self,
        token: str,
        sos_event_id: str,
        street_location: str,
        distance_meters: int,
        victim_name: Optional[str] = None
    ) -> bool:
        """Send SOS emergency alert to a responder"""
        
        # Format distance for display
        if distance_meters < 1000:
            distance_str = f"~{int(distance_meters)}m away"
        else:
            distance_str = f"~{distance_meters/1000:.1f}km away"
        
        title = "🚨 Emergency Nearby!"
        body = f"Someone needs help {distance_str}\n📍 {street_location}"
        
        data = {
            "type": "sos_alert",
            "sos_event_id": sos_event_id,
            "street_location": street_location,
            "distance_meters": str(distance_meters),
            "click_action": "OPEN_SOS_ALERT"
        }
        
        return await self.send_notification(
            token=token,
            title=title,
            body=body,
            data=data,
            priority="high"
        )
    
    async def send_sos_alert_batch(
        self,
        responders: List[Dict],
        sos_event_id: str,
        street_location: str
    ) -> Dict[str, int]:
        """Send SOS alerts to multiple responders"""
        if not self.initialized:
            logger.warning("FCM not initialized, skipping batch notifications")
            return {"sent": 0, "failed": 0}
        
        sent = 0
        failed = 0
        
        for responder in responders:
            token = responder.get("fcm_token")
            distance = responder.get("distance_meters", 0)
            
            if token:
                success = await self.send_sos_alert(
                    token=token,
                    sos_event_id=sos_event_id,
                    street_location=street_location,
                    distance_meters=int(distance)
                )
                if success:
                    sent += 1
                else:
                    failed += 1
            else:
                failed += 1
        
        logger.info(f"SOS batch notifications: {sent} sent, {failed} failed")
        return {"sent": sent, "failed": failed}
    
    async def send_sos_update(
        self,
        token: str,
        sos_event_id: str,
        update_type: str,
        message: str
    ) -> bool:
        """Send SOS status update to a responder"""
        
        titles = {
            "resolved": "✅ Emergency Resolved",
            "cancelled": "Emergency Cancelled",
            "helper_arrived": "Helper Arrived",
            "location_update": "📍 Location Updated"
        }
        
        title = titles.get(update_type, "SOS Update")
        
        data = {
            "type": "sos_update",
            "sos_event_id": sos_event_id,
            "update_type": update_type,
            "click_action": "OPEN_SOS_UPDATE"
        }
        
        return await self.send_notification(
            token=token,
            title=title,
            body=message,
            data=data,
            priority="high" if update_type != "resolved" else "normal"
        )
    
    async def send_help_offered_notification(
        self,
        victim_token: str,
        sos_event_id: str,
        responder_name: str,
        distance_meters: int
    ) -> bool:
        """Notify victim that someone offered help"""
        
        if distance_meters < 1000:
            distance_str = f"{int(distance_meters)}m away"
        else:
            distance_str = f"{distance_meters/1000:.1f}km away"
        
        title = "🆘 Help is Coming!"
        body = f"{responder_name or 'A community member'} is coming to help ({distance_str})"
        
        data = {
            "type": "help_offered",
            "sos_event_id": sos_event_id,
            "responder_name": responder_name or "Anonymous",
            "click_action": "OPEN_SOS_STATUS"
        }
        
        return await self.send_notification(
            token=victim_token,
            title=title,
            body=body,
            data=data,
            priority="high"
        )


# Singleton instance
fcm_service = FCMService()
