"""
Visit Scheduling Tool
Handles property visit scheduling through API integration
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger(__name__)


class VisitSchedulingTool:
    """Tool for scheduling property visits"""
    
    def __init__(self):
        self.api_url = "https://auth.propzing.com/functions/v1/visit_user_manager"
        self.api_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjUyOTI3ODYsImV4cCI6MjA0MDg2ODc4Nn0.11GJjOlgPf4RocdFjMnWGJpBqFVk1wmbW27OmV0YAzs")
    
    async def schedule_visit(self, 
                           user_name: str, 
                           user_number: str, 
                           date_and_time: str, 
                           property_id: str) -> Dict[str, Any]:
        """
        Schedule a property visit
        
        Args:
            user_name: Customer's name
            user_number: Customer's phone number (with +)
            date_and_time: Visit date and time (format: "2023-12-25 14:00")
            property_id: Property UUID
            
        Returns:
            Dict with success status and message
        """
        try:
            logger.info(f"📅 Scheduling visit for {user_name} ({user_number}) - Property: {property_id}")
            
            # Prepare payload
            payload = {
                "user_name": user_name,
                "user_number": user_number,
                "date_and_time": date_and_time,
                "record_id": property_id,
                "isProperty": True
            }
            
            # Headers with AiSensy auth token (using Supabase key as fallback)
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            logger.info(f"📤 Sending visit scheduling request: {json.dumps(payload, indent=2)}")
            
            # Make actual API call to visit user manager
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Visit scheduled successfully for {user_name}")
                return {
                    'success': True,
                    'message': f"Visit scheduled successfully for {date_and_time}",
                    'response_data': response.json()
                }
            else:
                logger.error(f"❌ Visit scheduling failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f"Failed to schedule visit: {response.status_code}",
                    'error': response.text
                }
                
        except Exception as e:
            logger.error(f"❌ Error scheduling visit: {str(e)}")
            return {
                'success': False,
                'message': f"Error scheduling visit: {str(e)}",
                'error': str(e)
            }
    
    def parse_date_time(self, date_time_text: str) -> Optional[str]:
        """
        Parse user input date/time into API format
        
        Args:
            date_time_text: User's date/time input
            
        Returns:
            Formatted date/time string or None if invalid
        """
        try:
            # Common formats to try
            formats = [
                "%Y-%m-%d %H:%M",  # 2023-12-25 14:00
                "%d/%m/%Y %H:%M",  # 25/12/2023 14:00
                "%d-%m-%Y %H:%M",  # 25-12-2023 14:00
                "%B %d %H:%M",     # December 25 14:00
                "%d %B %H:%M",     # 25 December 14:00
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_time_text, fmt)
                    # If no year specified, assume current year
                    if dt.year == 1900:
                        dt = dt.replace(year=datetime.now().year)
                    return dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    continue
            
            # Try to extract partial information
            text_lower = date_time_text.lower()
            
            # Handle "tomorrow" and "today"
            if "tomorrow" in text_lower:
                tomorrow = datetime.now() + timedelta(days=1)
                # Try to extract time
                import re
                time_match = re.search(r'(\d{1,2}):(\d{2})', date_time_text)
                if time_match:
                    hour, minute = int(time_match.group(1)), int(time_match.group(2))
                    tomorrow = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    tomorrow = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)  # Default 2 PM
                return tomorrow.strftime("%Y-%m-%d %H:%M")
            
            if "today" in text_lower:
                today = datetime.now()
                # Try to extract time
                import re
                time_match = re.search(r'(\d{1,2}):(\d{2})', date_time_text)
                if time_match:
                    hour, minute = int(time_match.group(1)), int(time_match.group(2))
                    today = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    today = today.replace(hour=14, minute=0, second=0, microsecond=0)  # Default 2 PM
                return today.strftime("%Y-%m-%d %H:%M")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error parsing date/time: {str(e)}")
            return None
    
    def format_scheduling_response(self, success: bool, user_name: str, date_time: str = None, error: str = None) -> str:
        """
        Format the scheduling response message
        
        Args:
            success: Whether scheduling was successful
            user_name: Customer's name
            date_time: Scheduled date/time
            error: Error message if failed
            
        Returns:
            Formatted response message
        """
        if success and date_time:
            return f"""✅ *Visit Scheduled Successfully!*

👤 *Name:* {user_name}
📅 *Date & Time:* {date_time}

📞 *What's Next:*
• You'll receive a confirmation call/message
• Our representative will contact you before the visit
• Please keep your phone accessible

🏠 *Looking forward to showing you this amazing property!*"""
        else:
            # Use user-friendly message instead of technical error details
            return f"""❌ *Unable to Schedule Visit*

We're sorry, but we couldn't schedule your visit at this time.

📞 *Please contact us directly:*
Call us to schedule your property visit, and we'll arrange it for you right away.

💬 *Need Help?*
Let me know if you'd like to try a different date or need assistance with anything else."""


# Global instance
visit_scheduling_tool = VisitSchedulingTool()
