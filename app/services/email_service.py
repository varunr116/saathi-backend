"""
Email Service - SendGrid Integration for Emergency Alerts
"""
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Dict, Any, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email alerts via SendGrid"""
    
    def __init__(self):
        """Initialize SendGrid client"""
        if settings.SENDGRID_API_KEY:
            self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            self.from_email = settings.SENDGRID_FROM_EMAIL
            self.enabled = True
            logger.info("[Email] SendGrid initialized successfully")
        else:
            self.client = None
            self.enabled = False
            logger.warning("[Email] SendGrid not configured - Email disabled")
    
    async def send_emergency_alert(
        self,
        to_email: str,
        contact_name: str,
        user_name: str,
        location_link: str,
        coordinates: Dict[str, float],
        timestamp: str,
        user_phone: str = None,
        medical_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Send detailed emergency email alert
        
        Args:
            to_email: Recipient email address
            contact_name: Name of emergency contact
            user_name: Name of person in emergency
            location_link: Google Maps link
            coordinates: GPS coordinates
            timestamp: ISO timestamp
            user_phone: User's phone number (optional)
            medical_info: Dict with blood_type, allergies, conditions (optional)
        
        Returns:
            Dict with success status
        """
        if not self.enabled:
            logger.warning("[Email] Email service not enabled")
            return {"success": False, "error": "Email not configured"}
        
        try:
            # Build medical info section
            medical_section = ""
            if medical_info:
                medical_section = f"""
<h3>⚕️ Medical Information</h3>
<ul>
    <li><strong>Blood Type:</strong> {medical_info.get('blood_type', 'Not specified')}</li>
    <li><strong>Allergies:</strong> {medical_info.get('allergies', 'None specified')}</li>
    <li><strong>Medical Conditions:</strong> {medical_info.get('conditions', 'None specified')}</li>
</ul>
"""
            
            # Build HTML email
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .alert {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .location {{ background-color: #e3f2fd; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .button {{ display: inline-block; background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        ul {{ padding-left: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ EMERGENCY ALERT</h1>
        </div>
        
        <div class="content">
            <h2>Dear {contact_name},</h2>
            
            <div class="alert">
                <p><strong>{user_name} has triggered an emergency SOS alert and needs immediate help.</strong></p>
                <p><strong>Time:</strong> {timestamp}</p>
                {f'<p><strong>Contact:</strong> {user_phone}</p>' if user_phone else ''}
            </div>
            
            <div class="location">
                <h3>📍 Current Location</h3>
                <p><strong>GPS Coordinates:</strong><br>
                Latitude: {coordinates['latitude']}<br>
                Longitude: {coordinates['longitude']}</p>
                
                <p><a href="{location_link}" class="button">📍 Open in Google Maps</a></p>
                
                <p style="font-size: 12px; color: #666;">
                    <strong>Direct link:</strong><br>
                    <a href="{location_link}">{location_link}</a>
                </p>
            </div>
            
            {medical_section}
            
            <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin-top: 20px;">
                <h3>🚨 What to do:</h3>
                <ol>
                    <li>Check the location immediately using the map link above</li>
                    <li>Try calling {user_name} at {user_phone if user_phone else 'their phone'}</li>
                    <li>If you cannot reach them, consider calling local emergency services</li>
                    <li>Share this location with other emergency contacts if needed</li>
                </ol>
            </div>
            
            <p style="margin-top: 20px; padding: 15px; background-color: #fff; border-left: 4px solid #2196F3;">
                <strong>ℹ️ About this alert:</strong><br>
                This is an automated emergency alert from Saathi AI. {user_name} has designated you as an emergency contact.
                You are receiving this because they triggered an SOS alert using their mobile device.
            </p>
        </div>
        
        <div class="footer">
            <p>This email was sent by Saathi AI Emergency System<br>
            Do not reply to this email - contact {user_name} directly</p>
        </div>
    </div>
</body>
</html>
"""
            
            # Create email
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=f"🚨 EMERGENCY ALERT - {user_name} needs help",
                html_content=Content("text/html", html_content)
            )
            
            # Send email
            response = self.client.send(message)
            
            logger.info(f"[Email] Emergency alert sent to {to_email} - Status: {response.status_code}")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "to": to_email
            }
            
        except Exception as e:
            logger.error(f"[Email] Failed to send to {to_email}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "to": to_email
            }
    
    async def send_bulk_alerts(
        self,
        contacts: List[Dict[str, str]],
        user_name: str,
        location_link: str,
        coordinates: Dict[str, float],
        timestamp: str,
        user_phone: str = None,
        medical_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send emergency emails to multiple contacts"""
        results = []
        success_count = 0
        
        for contact in contacts:
            if contact.get('email'):
                result = await self.send_emergency_alert(
                    to_email=contact['email'],
                    contact_name=contact.get('name', 'Emergency Contact'),
                    user_name=user_name,
                    location_link=location_link,
                    coordinates=coordinates,
                    timestamp=timestamp,
                    user_phone=user_phone,
                    medical_info=medical_info
                )
                
                result['contact_name'] = contact.get('name', 'Unknown')
                results.append(result)
                
                if result['success']:
                    success_count += 1
        
        logger.info(f"[Email] Sent {success_count}/{len([c for c in contacts if c.get('email')])} emergency emails")
        
        return {
            "success": success_count > 0,
            "total_contacts": len([c for c in contacts if c.get('email')]),
            "successful": success_count,
            "failed": len([c for c in contacts if c.get('email')]) - success_count,
            "results": results
        }
    
    async def send_cancellation_alert(
        self,
        to_email: str,
        contact_name: str,
        user_name: str,
        reason: str = "False alarm"
    ) -> Dict[str, Any]:
        """Send SOS cancellation email"""
        if not self.enabled:
            return {"success": False, "error": "Email not configured"}
        
        try:
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Emergency Alert Cancelled</h1>
        </div>
        <div class="content">
            <h2>Dear {contact_name},</h2>
            <p><strong>{user_name} is safe.</strong></p>
            <p>The previous emergency alert has been cancelled. Reason: {reason}</p>
            <p>{user_name} has confirmed they are safe and no longer need assistance.</p>
            <p style="margin-top: 20px; color: #666;">
                - Saathi AI Emergency System
            </p>
        </div>
    </div>
</body>
</html>
"""
            
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=f"✅ FALSE ALARM - {user_name} is safe",
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            logger.info(f"[Email] Cancellation sent to {to_email}")
            
            return {
                "success": True,
                "status_code": response.status_code
            }
            
        except Exception as e:
            logger.error(f"[Email] Cancellation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
email_service = EmailService()
