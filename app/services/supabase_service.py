"""
Supabase Service - Database operations for Community Safety Network
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)


class SupabaseService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.url or not self.service_key:
            logger.warning("Supabase credentials not configured")
            self.client = None
        else:
            # Use service role key for backend operations (bypasses RLS)
            self.client: Client = create_client(self.url, self.service_key)
    
    def is_configured(self) -> bool:
        return self.client is not None
    
    # ============================================
    # User/Profile Operations
    # ============================================
    
    async def get_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile by ID"""
        try:
            result = self.client.table("profiles").select("*").eq("id", user_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None
    
    async def get_profile_by_email(self, email: str) -> Optional[Dict]:
        """Get user profile by email (via auth.users join)"""
        try:
            # Query auth.users to get user_id, then get profile
            result = self.client.auth.admin.list_users()
            for user in result:
                if user.email == email:
                    return await self.get_profile(user.id)
            return None
        except Exception as e:
            logger.error(f"Error getting profile by email: {e}")
            return None
    
    async def update_profile(self, user_id: str, data: Dict) -> Optional[Dict]:
        """Update user profile"""
        try:
            result = self.client.table("profiles").update(data).eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return None
    
    async def update_user_location(self, user_id: str, latitude: float, longitude: float) -> bool:
        """Update user's current location using PostGIS"""
        try:
            # Call the database function we created
            self.client.rpc(
                "update_user_location",
                {"user_id": user_id, "lat": latitude, "lng": longitude}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating location: {e}")
            return False
    
    async def update_fcm_token(self, user_id: str, fcm_token: str) -> bool:
        """Update user's FCM token for push notifications"""
        try:
            self.client.table("profiles").update({
                "fcm_token": fcm_token
            }).eq("id", user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating FCM token: {e}")
            return False
    
    async def set_responder_settings(
        self, 
        user_id: str, 
        is_enabled: bool, 
        radius_meters: int = 500
    ) -> bool:
        """Enable/disable responder mode"""
        try:
            self.client.table("profiles").update({
                "is_responder_enabled": is_enabled,
                "responder_radius_meters": radius_meters
            }).eq("id", user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error setting responder settings: {e}")
            return False
    
    # ============================================
    # SOS Event Operations
    # ============================================
    
    async def create_sos_event(
        self,
        victim_id: Optional[str],
        victim_name: str,
        victim_phone: str,
        latitude: float,
        longitude: float,
        street_address: Optional[str] = None,
        community_broadcast: bool = True,
        broadcast_radius: int = 500
    ) -> Optional[Dict]:
        """Create a new SOS event"""
        try:
            data = {
                "victim_id": victim_id,
                "victim_name": victim_name,
                "victim_phone": victim_phone,
                "latitude": latitude,
                "longitude": longitude,
                "street_address": street_address,
                "community_broadcast_enabled": community_broadcast,
                "broadcast_radius_meters": broadcast_radius,
                "status": "active"
            }
            
            # Set the PostGIS point
            result = self.client.rpc(
                "create_sos_with_location",
                {
                    "p_victim_id": victim_id,
                    "p_victim_name": victim_name,
                    "p_victim_phone": victim_phone,
                    "p_lat": latitude,
                    "p_lng": longitude,
                    "p_street_address": street_address,
                    "p_broadcast_enabled": community_broadcast,
                    "p_broadcast_radius": broadcast_radius
                }
            ).execute()
            
            if result.data:
                return result.data
            
            # Fallback: direct insert (without PostGIS point, will need manual update)
            result = self.client.table("sos_events").insert(data).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating SOS event: {e}")
            # Try simpler insert
            try:
                result = self.client.table("sos_events").insert({
                    "victim_id": victim_id,
                    "victim_name": victim_name,
                    "victim_phone": victim_phone,
                    "latitude": latitude,
                    "longitude": longitude,
                    "street_address": street_address,
                    "community_broadcast_enabled": community_broadcast,
                    "broadcast_radius_meters": broadcast_radius,
                    "status": "active"
                }).execute()
                return result.data[0] if result.data else None
            except Exception as e2:
                logger.error(f"Fallback insert also failed: {e2}")
                return None
    
    async def get_sos_event(self, event_id: str) -> Optional[Dict]:
        """Get SOS event by ID"""
        try:
            result = self.client.table("sos_events").select("*").eq("id", event_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting SOS event: {e}")
            return None
    
    async def update_sos_event(self, event_id: str, data: Dict) -> Optional[Dict]:
        """Update SOS event"""
        try:
            result = self.client.table("sos_events").update(data).eq("id", event_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating SOS event: {e}")
            return None
    
    async def resolve_sos_event(
        self,
        event_id: str,
        resolved_by: Optional[str],
        resolution_type: str,
        notes: Optional[str] = None
    ) -> bool:
        """Mark SOS event as resolved"""
        try:
            self.client.table("sos_events").update({
                "status": "resolved",
                "resolved_at": datetime.utcnow().isoformat(),
                "resolved_by": resolved_by,
                "resolution_type": resolution_type,
                "resolution_notes": notes
            }).eq("id", event_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error resolving SOS event: {e}")
            return False
    
    async def get_active_sos_for_user(self, user_id: str) -> List[Dict]:
        """Get active SOS events where user is victim"""
        try:
            result = self.client.table("sos_events").select("*").eq(
                "victim_id", user_id
            ).eq("status", "active").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting active SOS: {e}")
            return []
    
    # ============================================
    # Responder Operations
    # ============================================
    
    async def find_nearby_responders(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 500,
        exclude_user_id: Optional[str] = None
    ) -> List[Dict]:
        """Find responders within radius using PostGIS"""
        try:
            result = self.client.rpc(
                "find_nearby_responders",
                {
                    "victim_lat": latitude,
                    "victim_lng": longitude,
                    "radius_meters": radius_meters,
                    "exclude_user_id": exclude_user_id
                }
            ).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error finding nearby responders: {e}")
            return []
    
    async def create_responder_action(
        self,
        sos_event_id: str,
        responder_id: str,
        action_type: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        distance_meters: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict]:
        """Log a responder action"""
        try:
            data = {
                "sos_event_id": sos_event_id,
                "responder_id": responder_id,
                "action_type": action_type,
                "distance_meters": distance_meters,
                "notes": notes
            }
            
            result = self.client.table("responder_actions").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating responder action: {e}")
            return None
    
    async def get_responder_actions(self, sos_event_id: str) -> List[Dict]:
        """Get all actions for an SOS event"""
        try:
            result = self.client.table("responder_actions").select(
                "*, profiles(name)"
            ).eq("sos_event_id", sos_event_id).order("created_at").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting responder actions: {e}")
            return []
    
    async def get_user_active_responses(self, user_id: str) -> List[Dict]:
        """Get SOS events where user has offered help and event is still active"""
        try:
            # Get events where user has 'offered_help' action
            result = self.client.table("responder_actions").select(
                "sos_event_id, sos_events(*)"
            ).eq("responder_id", user_id).eq(
                "action_type", "offered_help"
            ).execute()
            
            # Filter to active events only
            active = []
            for action in result.data or []:
                event = action.get("sos_events")
                if event and event.get("status") == "active":
                    active.append(event)
            
            return active
        except Exception as e:
            logger.error(f"Error getting user active responses: {e}")
            return []
    
    async def has_user_responded(self, sos_event_id: str, user_id: str, action_type: str) -> bool:
        """Check if user has already taken a specific action on an SOS"""
        try:
            result = self.client.table("responder_actions").select("id").eq(
                "sos_event_id", sos_event_id
            ).eq("responder_id", user_id).eq("action_type", action_type).execute()
            return len(result.data or []) > 0
        except Exception as e:
            logger.error(f"Error checking user response: {e}")
            return False
    
    async def update_responders_notified_count(self, sos_event_id: str, count: int) -> bool:
        """Update the count of responders notified"""
        try:
            self.client.table("sos_events").update({
                "responders_notified": count
            }).eq("id", sos_event_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating notified count: {e}")
            return False


# Singleton instance
supabase_service = SupabaseService()
