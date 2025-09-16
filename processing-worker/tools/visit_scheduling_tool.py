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
from openai import AsyncOpenAI

logger = setup_logger(__name__)


class VisitSchedulingTool:
    """Tool for scheduling property visits"""
    
    def __init__(self):
        self.api_url = "https://auth.propzing.com/functions/v1/visit_user_manager"
        self.api_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjUyOTI3ODYsImV4cCI6MjA0MDg2ODc4Nn0.11GJjOlgPf4RocdFjMnWGJpBqFVk1wmbW27OmV0YAzs")
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
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
    
    async def parse_date_time(self, date_time_text: str) -> Optional[str]:
        """
        Parse user input date/time into API format using LLM intelligence
        
        Args:
            date_time_text: User's date/time input
            
        Returns:
            Formatted date/time string or None if invalid
        """
        try:
            logger.info(f"🤖 LLM_DATE_PARSER: Processing '{date_time_text}'")
            
            # Get current date and time for context
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            current_day = now.strftime("%A")
            
            # Create LLM prompt for date/time parsing
            prompt = f"""You are a strict date/time parser. Parse the user's natural language date/time input and return a structured JSON response.

Current Context:
- Today is {current_day}, {current_date}
- Current time is {current_time}

User Input: "{date_time_text}"

Parse this input and return ONLY a JSON object with this exact format:
{{
    "success": true/false,
    "datetime": "YYYY-MM-DD HH:MM",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

STRICT Rules:
1. ONLY parse if BOTH date AND time are clearly specified or can be reasonably inferred
2. Do NOT make assumptions about missing information
3. If only date is given (no time), set success to false
4. If only time is given (no date), set success to false
5. Handle relative dates like "tomorrow", "next Friday", "in 2 days" ONLY if time is also specified
6. Handle time formats like "3pm", "15:30" ONLY if date is also specified
7. General time periods like "morning", "afternoon", "evening" without specific times should fail
8. If the input is ambiguous, incomplete, or invalid, set success to false
9. Confidence should be high (0.8+) only for complete and clear inputs

Examples:
- "tomorrow at 3pm" → {{"success": true, "datetime": "{(now + timedelta(days=1)).strftime('%Y-%m-%d')} 15:00", "confidence": 0.9}}
- "next Friday 10am" → {{"success": true, "datetime": "2024-01-19 10:00", "confidence": 0.8}}
- "tomorrow" → {{"success": false, "datetime": null, "confidence": 0.0, "reasoning": "No time specified"}}
- "3pm" → {{"success": false, "datetime": null, "confidence": 0.0, "reasoning": "No date specified"}}
- "tomorrow morning" → {{"success": false, "datetime": null, "confidence": 0.0, "reasoning": "Time too vague"}}
- "blah blah" → {{"success": false, "datetime": null, "confidence": 0.0, "reasoning": "Invalid input"}}"""

            # Make LLM call
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            # Parse LLM response
            llm_response = response.choices[0].message.content.strip()
            logger.info(f"🤖 LLM_DATE_RESPONSE: {llm_response}")
            
            # Extract JSON from response
            try:
                # Handle potential markdown formatting
                if "```json" in llm_response:
                    llm_response = llm_response.split("```json")[1].split("```")[0].strip()
                elif "```" in llm_response:
                    llm_response = llm_response.split("```")[1].strip()
                
                parsed_result = json.loads(llm_response)
                
                if parsed_result.get("success") and parsed_result.get("datetime"):
                    # Validate the datetime format
                    try:
                        parsed_dt = datetime.strptime(parsed_result["datetime"], "%Y-%m-%d %H:%M")
                        
                        # Ensure the date is not in the past (except for today if time is future)
                        if parsed_dt < now:
                            if parsed_dt.date() == now.date():
                                # Same day but time is past, move to tomorrow
                                parsed_dt = parsed_dt + timedelta(days=1)
                            elif parsed_dt.date() < now.date():
                                # Past date, invalid
                                logger.warning(f"⚠️ LLM_DATE_PARSER: Parsed date is in the past: {parsed_result['datetime']}")
                                return None
                        
                        formatted_datetime = parsed_dt.strftime("%Y-%m-%d %H:%M")
                        logger.info(f"✅ LLM_DATE_PARSER: Successfully parsed '{date_time_text}' → '{formatted_datetime}' (confidence: {parsed_result.get('confidence', 0)})")
                        return formatted_datetime
                        
                    except ValueError as ve:
                        logger.error(f"❌ LLM_DATE_PARSER: Invalid datetime format from LLM: {parsed_result['datetime']} - {str(ve)}")
                        return None
                else:
                    logger.warning(f"⚠️ LLM_DATE_PARSER: LLM could not parse '{date_time_text}' - {parsed_result.get('reasoning', 'No reason provided')}")
                    return None
                    
            except json.JSONDecodeError as je:
                logger.error(f"❌ LLM_DATE_PARSER: Failed to parse LLM JSON response: {str(je)} - Response: {llm_response}")
                return None
            
        except Exception as e:
            logger.error(f"❌ LLM_DATE_PARSER: Unexpected error: {str(e)}")
            # Fallback to simple regex parsing for critical errors
            return self._fallback_parse_date_time(date_time_text)
    
    def _fallback_parse_date_time(self, date_time_text: str) -> Optional[str]:
        """
        Fallback date/time parser using simple regex (used when LLM fails)
        Only parses if both date and time can be clearly identified
        """
        try:
            logger.info(f"🔄 FALLBACK_PARSER: Using fallback parsing for '{date_time_text}'")
            text_lower = date_time_text.lower().strip()
            
            # Return None for empty or whitespace-only input
            if not text_lower:
                return None
            
            import re
            
            # Look for time patterns (must have both date and time)
            time_patterns = [
                r'(\d{1,2}):(\d{2})',  # HH:MM
                r'(\d{1,2})\s*pm',     # 3pm
                r'(\d{1,2})\s*am',     # 10am
            ]
            
            time_match = None
            hour = None
            minute = 0
            
            for pattern in time_patterns:
                time_match = re.search(pattern, text_lower)
                if time_match:
                    if ':' in pattern:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                    else:
                        hour = int(time_match.group(1))
                        if 'pm' in text_lower and hour != 12:
                            hour += 12
                        elif 'am' in text_lower and hour == 12:
                            hour = 0
                    break
            
            # Only proceed if we found a time
            if time_match and hour is not None:
                # Now look for date patterns
                if "tomorrow" in text_lower:
                    tomorrow = datetime.now() + timedelta(days=1)
                    result_dt = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    return result_dt.strftime("%Y-%m-%d %H:%M")
                
                elif "today" in text_lower:
                    today = datetime.now()
                    result_dt = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    return result_dt.strftime("%Y-%m-%d %H:%M")
                
                # Look for day names
                days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                for i, day in enumerate(days):
                    if day in text_lower:
                        # Find next occurrence of this day
                        today = datetime.now()
                        days_ahead = (i - today.weekday()) % 7
                        if days_ahead == 0:  # Today
                            days_ahead = 7  # Next week
                        target_date = today + timedelta(days=days_ahead)
                        result_dt = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        return result_dt.strftime("%Y-%m-%d %H:%M")
            
            # If we can't find both date and time, return None
            logger.warning(f"⚠️ FALLBACK_PARSER: Could not parse both date and time from '{date_time_text}'")
            return None
            
        except Exception as e:
            logger.error(f"❌ FALLBACK_PARSER: Error: {str(e)}")
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
