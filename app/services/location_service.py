"""
Location Service - GPS tracking and location utilities
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LocationService:
    """Service for handling location data and tracking"""
    
    def __init__(self):
        """Initialize location service"""
        # In-memory storage for active SOS location tracking
        # In production, use Redis or database
        self.active_sos_locations: Dict[str, List[Dict]] = {}
        logger.info("[Location] Location service initialized")
    
    def create_google_maps_link(
        self,
        latitude: float,
        longitude: float
    ) -> str:
        """
        Create Google Maps link from coordinates
        
        Args:
            latitude: GPS latitude
            longitude: GPS longitude
        
        Returns:
            Google Maps URL
        """
        return f"https://www.google.com/maps?q={latitude},{longitude}"
    
    def validate_coordinates(
        self,
        latitude: float,
        longitude: float
    ) -> bool:
        """
        Validate GPS coordinates
        
        Args:
            latitude: Must be between -90 and 90
            longitude: Must be between -180 and 180
        
        Returns:
            True if valid, False otherwise
        """
        try:
            lat = float(latitude)
            lon = float(longitude)
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return True
            else:
                logger.warning(f"[Location] Invalid coordinates: {lat}, {lon}")
                return False
        except (ValueError, TypeError):
            logger.error(f"[Location] Invalid coordinate format: {latitude}, {longitude}")
            return False
    
    def start_sos_tracking(
        self,
        sos_id: str,
        user_id: str,
        initial_location: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Start tracking location for an active SOS
        
        Args:
            sos_id: Unique SOS alert ID
            user_id: User ID
            initial_location: Dict with 'latitude' and 'longitude'
        
        Returns:
            Tracking session info
        """
        if not self.validate_coordinates(
            initial_location['latitude'],
            initial_location['longitude']
        ):
            return {
                "success": False,
                "error": "Invalid coordinates"
            }
        
        # Initialize tracking for this SOS
        self.active_sos_locations[sos_id] = [{
            "latitude": initial_location['latitude'],
            "longitude": initial_location['longitude'],
            "timestamp": datetime.utcnow().isoformat(),
            "accuracy": initial_location.get('accuracy', None)
        }]
        
        logger.info(f"[Location] Started tracking SOS: {sos_id}")
        
        return {
            "success": True,
            "sos_id": sos_id,
            "tracking_started": True,
            "location_count": 1
        }
    
    def update_sos_location(
        self,
        sos_id: str,
        new_location: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Update location for an active SOS
        
        Args:
            sos_id: SOS alert ID
            new_location: Dict with 'latitude', 'longitude', optional 'accuracy'
        
        Returns:
            Update status
        """
        if sos_id not in self.active_sos_locations:
            logger.warning(f"[Location] SOS not found: {sos_id}")
            return {
                "success": False,
                "error": "SOS tracking not active"
            }
        
        if not self.validate_coordinates(
            new_location['latitude'],
            new_location['longitude']
        ):
            return {
                "success": False,
                "error": "Invalid coordinates"
            }
        
        # Add new location to tracking history
        self.active_sos_locations[sos_id].append({
            "latitude": new_location['latitude'],
            "longitude": new_location['longitude'],
            "timestamp": datetime.utcnow().isoformat(),
            "accuracy": new_location.get('accuracy', None)
        })
        
        location_count = len(self.active_sos_locations[sos_id])
        
        logger.info(f"[Location] Updated SOS {sos_id} location (total: {location_count})")
        
        return {
            "success": True,
            "sos_id": sos_id,
            "location_count": location_count,
            "latest_location": self.active_sos_locations[sos_id][-1]
        }
    
    def get_sos_location_history(
        self,
        sos_id: str
    ) -> Dict[str, Any]:
        """
        Get full location history for an SOS
        
        Args:
            sos_id: SOS alert ID
        
        Returns:
            Location history
        """
        if sos_id not in self.active_sos_locations:
            return {
                "success": False,
                "error": "SOS not found"
            }
        
        locations = self.active_sos_locations[sos_id]
        
        return {
            "success": True,
            "sos_id": sos_id,
            "location_count": len(locations),
            "locations": locations,
            "current_location": locations[-1] if locations else None
        }
    
    def stop_sos_tracking(
        self,
        sos_id: str
    ) -> Dict[str, Any]:
        """
        Stop tracking and archive location history
        
        Args:
            sos_id: SOS alert ID
        
        Returns:
            Final tracking summary
        """
        if sos_id not in self.active_sos_locations:
            return {
                "success": False,
                "error": "SOS not found"
            }
        
        locations = self.active_sos_locations[sos_id]
        location_count = len(locations)
        
        # Archive (in production, save to database)
        # For now, just remove from active tracking
        del self.active_sos_locations[sos_id]
        
        logger.info(f"[Location] Stopped tracking SOS: {sos_id} ({location_count} locations)")
        
        return {
            "success": True,
            "sos_id": sos_id,
            "tracking_stopped": True,
            "total_locations": location_count,
            "final_location": locations[-1] if locations else None
        }
    
    def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates in meters
        Using Haversine formula
        
        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate
        
        Returns:
            Distance in meters
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Earth radius in meters
        R = 6371000
        
        # Convert to radians
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        # Haversine formula
        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c
        
        return distance
    
    def format_location_update(
        self,
        location: Dict[str, Any]
    ) -> str:
        """
        Format location update for SMS/notification
        
        Args:
            location: Location dict with latitude, longitude, timestamp
        
        Returns:
            Formatted string
        """
        maps_link = self.create_google_maps_link(
            location['latitude'],
            location['longitude']
        )
        
        return f"""📍 Location Update
GPS: {location['latitude']}, {location['longitude']}
Time: {location['timestamp']}
Maps: {maps_link}"""


# Singleton instance
location_service = LocationService()
