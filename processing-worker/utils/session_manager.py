"""
Session management for WhatsApp conversations
"""

import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import os

from .logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ConversationSession:
    """
    Represents a conversation session for a WhatsApp user
    """
    user_id: str
    created_at: float
    last_updated: float
    current_agent: Optional[str] = None
    conversation_history: list = None
    context: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.context is None:
            self.context = {}
        if self.metadata is None:
            self.metadata = {}
    
    def add_message(self, role: str, content: str, agent_name: str, metadata: Dict[str, Any] = None):
        """Add a message to the conversation history"""
        import time
        
        message = {
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "agent_name": agent_name,
            "metadata": metadata or {}
        }
        
        self.conversation_history.append(message)
        self.last_updated = time.time()


class SessionManager:
    """
    Manages conversation sessions with in-memory storage
    """
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.session_timeout = int(os.getenv("SESSION_TIMEOUT_HOURS", "24")) * 3600  # 24 hours default
        logger.info("Session manager initialized with in-memory storage")
    
    def get_session(self, user_id: str) -> ConversationSession:
        """
        Get or create a session for a user
        """
        # Check if session exists in memory
        if user_id in self.sessions:
            session = self.sessions[user_id]
            # Check if session is still valid
            if time.time() - session.last_updated < self.session_timeout:
                return session
            else:
                # Session expired, remove it
                del self.sessions[user_id]
        
        # No persistent storage, so continue with new session creation
        
        # Create new session
        session = ConversationSession(
            user_id=user_id,
            created_at=time.time(),
            last_updated=time.time()
        )
        
        self.sessions[user_id] = session
        logger.info(f"Created new session for user: {user_id}")
        
        return session
    
    def update_session(self, user_id: str, session: ConversationSession) -> None:
        """
        Update session data in memory
        """
        session.last_updated = time.time()
        self.sessions[user_id] = session
        
    def add_message_to_history(
        self, 
        user_id: str, 
        role: str, 
        content: str, 
        agent_name: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Add a message to the conversation history
        """
        session = self.get_session(user_id)
        
        message = {
            "timestamp": time.time(),
            "role": role,  # "user" or "assistant"
            "content": content,
            "agent_name": agent_name,
            "metadata": metadata or {}
        }
        
        session.conversation_history.append(message)
        
        # Keep only last 50 messages to prevent memory issues
        if len(session.conversation_history) > 50:
            session.conversation_history = session.conversation_history[-50:]
        
        self.update_session(user_id, session)
    
    def set_current_agent(self, user_id: str, agent_name: str) -> None:
        """
        Set the current agent for a user session
        """
        session = self.get_session(user_id)
        session.current_agent = agent_name
        self.update_session(user_id, session)
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> list:
        """
        Get recent conversation history
        """
        session = self.get_session(user_id)
        return session.conversation_history[-limit:] if session.conversation_history else []
    
    def update_context(self, user_id: str, context_update: Dict[str, Any]) -> None:
        """
        Update session context
        """
        session = self.get_session(user_id)
        session.context.update(context_update)
        self.update_session(user_id, session)
    
    def set_active_properties(self, user_id: str, properties: list) -> None:
        """
        Set the active properties from a search result
        """
        session = self.get_session(user_id)
        session.context['active_properties'] = properties
        session.context['active_properties_updated'] = time.time()
        self.update_session(user_id, session)
        logger.info(f"Set {len(properties)} active properties for user {user_id}")
    
    def get_active_properties(self, user_id: str) -> list:
        """
        Get the active properties for a user
        """
        session = self.get_session(user_id)
        return session.context.get('active_properties', [])
    
    def get_property_by_reference(self, user_id: str, reference: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific property by reference (name, first, second, etc.)
        """
        properties = self.get_active_properties(user_id)
        if not properties:
            return None
        
        reference = reference.lower().strip()
        
        # Handle ordinal references
        ordinal_map = {
            'first': 0, '1st': 0, 'one': 0,
            'second': 1, '2nd': 1, 'two': 1, 
            'third': 2, '3rd': 2, 'three': 2,
            'fourth': 3, '4th': 3, 'four': 3,
            'fifth': 4, '5th': 4, 'five': 4
        }
        
        if reference in ordinal_map:
            index = ordinal_map[reference]
            if index < len(properties):
                return properties[index]
        
        # Handle numeric references
        try:
            index = int(reference) - 1  # Convert to 0-based index
            if 0 <= index < len(properties):
                return properties[index]
        except ValueError:
            pass
        
        # Handle property name matching
        for prop in properties:
            building_name = prop.get('building_name', '').lower()
            property_type = prop.get('property_type', '').lower()
            locality = prop.get('address', {}).get('locality', '').lower()
            
            if (reference in building_name or 
                reference in property_type or 
                reference in locality):
                return prop
        
        # Default to first property if no specific match
        return properties[0] if properties else None
    
    def clear_session(self, user_id: str) -> None:
        """
        Clear a user's session from memory
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"Cleared session for user: {user_id}")
    
    def cleanup_expired_sessions(self) -> None:
        """
        Clean up expired sessions from memory
        """
        current_time = time.time()
        expired_users = []
        
        for user_id, session in self.sessions.items():
            if current_time - session.last_updated > self.session_timeout:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.clear_session(user_id)
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired sessions") 