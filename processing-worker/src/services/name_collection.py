"""
Name Collection Service
Handles collecting user names using LLM-based extraction
"""

import os
import logging
from typing import Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class NameCollectionService:
    """Service for handling user name collection using LLM"""
    
    def __init__(self):
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def extract_name_from_message(self, message: str) -> Optional[str]:
        """
        Extract a name from a user message using LLM
        
        Args:
            message: The user's message
            
        Returns:
            Extracted name if found, None otherwise
        """
        try:
            logger.info(f"🤖 [NAME_EXTRACTION] Using LLM to extract name from: '{message[:50]}...'")
            
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a name extraction assistant. Extract the person's name from their message.

Rules:
- Only extract actual human names (first name, last name, or both)
- Return just the name in proper case (e.g., "John", "Sarah Johnson", "Mike")
- If no name is provided, return "NONE"
- Do not include titles, greetings, or other words
- Names should be 1-3 words maximum

Examples:
"My name is John" → "John"
"I'm Sarah Johnson" → "Sarah Johnson"
"Call me Mike" → "Mike"
"It's Alex" → "Alex"
"Hello" → "NONE"
"Yes" → "NONE"
"I want properties" → "NONE"
"""
                    },
                    {
                        "role": "user",
                        "content": f"Extract the name from this message: {message}"
                    }
                ],
                max_tokens=20,
                temperature=0
            )
            
            extracted_name = response.choices[0].message.content.strip()
            
            if extracted_name and extracted_name != "NONE":
                logger.info(f"✅ [NAME_EXTRACTION] LLM extracted name: '{extracted_name}'")
                return extracted_name
            else:
                logger.info(f"❌ [NAME_EXTRACTION] LLM found no name in message")
                return None
                
        except Exception as e:
            logger.error(f"❌ [NAME_EXTRACTION] Error using LLM: {e}")
            return None
    
    def generate_name_request_message(self, context: str = "") -> str:
        """
        Generate a message asking for the user's name
        
        Args:
            context: Optional context about what they were asking
            
        Returns:
            Formatted message asking for name
        """
        if context:
            return f"Hi there! 👋 Before I help you with {context}, may I know your name please? 😊"
        else:
            return "Hi there! 👋 May I know your name so I can assist you better? 😊"
    
    def generate_name_confirmation_message(self, name: str) -> str:
        """
        Generate a message confirming the name was saved
        
        Args:
            name: The saved name
            
        Returns:
            Confirmation message
        """
        return f"Great! Nice to meet you, {name}! 😊 How can I help you today?"
    
    async def is_likely_name_response(self, message: str, awaiting_name: bool = False) -> bool:
        """
        Check if a message is likely a name response using LLM
        
        Args:
            message: The user's message
            awaiting_name: Whether we're currently waiting for a name
            
        Returns:
            True if this looks like a name response
        """
        if not awaiting_name:
            return False
        
        # Use the extract_name_from_message method to check if there's a name
        extracted_name = await self.extract_name_from_message(message)
        return extracted_name is not None

# Global instance
name_collection_service = NameCollectionService()