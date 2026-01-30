"""
Community Broadcast Service - Orchestrates SOS alerts to nearby responders
"""
import logging
from typing import Optional, Dict, List
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from .supabase_service import supabase_service
from .fcm_service import fcm_service

logger = logging.getLogger(__name__)

# Initialize geocoder for reverse geocoding (coordinates -> address)
geolocator = Nominatim(user_agent="saathi-ai")


class CommunityBroadcastService:
    
    async def get_street_level_address(
        self, 
        latitude: float, 
        longitude: float
    ) -> str:
        """
        Get approximate street-level address from coordinates.
        Returns area name without exact house number for privacy.
        """
        try:
            location = geolocator.reverse(
                f"{latitude}, {longitude}",
                exactly_one=True,
                language="en"
            )
            
            if location and location.raw.get("address"):
                addr = location.raw["address"]
                
                # Build street-level address (no house number)
                parts = []
                
                # Neighborhood/area
                for key in ["neighbourhood", "suburb", "locality"]:
                    if addr.get(key):
                        parts.append(addr[key])
                        break
                
                # Road/street (without house number)
                if addr.get("road"):
                    parts.append(addr["road"])
                
                # City/district
                for key in ["city", "town", "district", "state_district"]:
                    if addr.get(key):
                        parts.append(addr[key])
                        break
                
                if parts:
                    return ", ".join(parts[:3])  # Max 3 parts
            
            # Fallback: rounded coordinates
            return f"{round(latitude, 3)}°N, {round(longitude, 3)}°E"
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding failed: {e}")
            return f"{round(latitude, 3)}°N, {round(longitude, 3)}°E"
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return f"{round(latitude, 3)}°N, {round(longitude, 3)}°E"
    
    async def broadcast_sos(
        self,
        sos_event_id: str,
        victim_id: Optional[str],
        victim_name: str,
        latitude: float,
        longitude: float,
        radius_meters: int = 500
    ) -> Dict:
        """
        Broadcast SOS to nearby responders.
        Returns stats about the broadcast.
        """
        result = {
            "success": False,
            "responders_found": 0,
            "notifications_sent": 0,
            "notifications_failed": 0,
            "street_address": None,
            "error": None
        }
        
        try:
            # 1. Get street-level address for privacy
            street_address = await self.get_street_level_address(latitude, longitude)
            result["street_address"] = street_address
            
            # 2. Update SOS event with street address
            await supabase_service.update_sos_event(sos_event_id, {
                "street_address": street_address
            })
            
            # 3. Find nearby responders
            responders = await supabase_service.find_nearby_responders(
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
                exclude_user_id=victim_id  # Don't notify the victim
            )
            
            result["responders_found"] = len(responders)
            logger.info(f"Found {len(responders)} nearby responders for SOS {sos_event_id}")
            
            if not responders:
                result["success"] = True  # No responders, but not an error
                return result
            
            # 4. Send push notifications
            fcm_result = await fcm_service.send_sos_alert_batch(
                responders=responders,
                sos_event_id=sos_event_id,
                street_location=street_address
            )
            
            result["notifications_sent"] = fcm_result["sent"]
            result["notifications_failed"] = fcm_result["failed"]
            
            # 5. Log 'notified' action for each responder
            for responder in responders:
                await supabase_service.create_responder_action(
                    sos_event_id=sos_event_id,
                    responder_id=responder["user_id"],
                    action_type="notified",
                    distance_meters=int(responder.get("distance_meters", 0))
                )
            
            # 6. Update notified count on SOS event
            await supabase_service.update_responders_notified_count(
                sos_event_id, 
                len(responders)
            )
            
            result["success"] = True
            logger.info(f"SOS broadcast complete: {result}")
            
        except Exception as e:
            logger.error(f"Error broadcasting SOS: {e}")
            result["error"] = str(e)
        
        return result
    
    async def notify_sos_resolved(
        self,
        sos_event_id: str,
        resolution_type: str
    ) -> int:
        """
        Notify all responders who interacted with this SOS that it's resolved.
        Returns count of notifications sent.
        """
        try:
            # Get all responder actions for this event
            actions = await supabase_service.get_responder_actions(sos_event_id)
            
            # Get unique responders who were notified or helped
            notified_responders = set()
            for action in actions:
                responder_id = action.get("responder_id")
                if responder_id:
                    notified_responders.add(responder_id)
            
            messages = {
                "self_cancelled": "The person cancelled their emergency alert.",
                "responder_helped": "Emergency resolved - help arrived. Thank you!",
                "emergency_services": "Emergency services responded. Thank you for being ready!",
                "false_alarm": "This was a false alarm. Thank you for being ready to help!",
                "timeout": "Emergency alert expired."
            }
            
            message = messages.get(resolution_type, "Emergency has been resolved.")
            sent = 0
            
            for responder_id in notified_responders:
                profile = await supabase_service.get_profile(responder_id)
                if profile and profile.get("fcm_token"):
                    success = await fcm_service.send_sos_update(
                        token=profile["fcm_token"],
                        sos_event_id=sos_event_id,
                        update_type="resolved",
                        message=message
                    )
                    if success:
                        sent += 1
            
            return sent
            
        except Exception as e:
            logger.error(f"Error notifying SOS resolved: {e}")
            return 0
    
    async def notify_victim_help_offered(
        self,
        sos_event_id: str,
        responder_id: str,
        responder_name: str,
        distance_meters: int
    ) -> bool:
        """Notify the victim that someone is coming to help"""
        try:
            # Get SOS event to find victim
            sos_event = await supabase_service.get_sos_event(sos_event_id)
            if not sos_event:
                return False
            
            victim_id = sos_event.get("victim_id")
            if not victim_id:
                return False
            
            # Get victim's FCM token
            victim_profile = await supabase_service.get_profile(victim_id)
            if not victim_profile or not victim_profile.get("fcm_token"):
                return False
            
            return await fcm_service.send_help_offered_notification(
                victim_token=victim_profile["fcm_token"],
                sos_event_id=sos_event_id,
                responder_name=responder_name,
                distance_meters=distance_meters
            )
            
        except Exception as e:
            logger.error(f"Error notifying victim of help: {e}")
            return False


# Singleton instance
community_broadcast_service = CommunityBroadcastService()
