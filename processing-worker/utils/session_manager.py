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
    # Name collection tracking
    user_question_count: int = 0
    customer_name: str = ""
    name_collection_asked: bool = False
    awaiting_name_response: bool = False
    pending_question: str = ""  # Store the question asked before name collection
    # Organization metadata
    org_id: str = ""
    org_name: str = ""
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.context is None:
            self.context = {}
        if self.metadata is None:
            self.metadata = {}
    
    def add_message(self, role: str, content: str, agent_name: str, metadata: Dict[str, Any] = None, message_type: str = "text"):
        """Add a message to the conversation history"""
        import time
        
        message = {
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "agent_name": agent_name,
            "type": message_type,  # Adding type field as requested
            "metadata": metadata or {}
        }
        
        self.conversation_history.append(message)
        self.last_updated = time.time()


class SessionManager:
    """
    Manages conversation sessions with in-memory storage
    """
    _instance = None
    _sessions = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.sessions: Dict[str, ConversationSession] = SessionManager._sessions
            self.session_timeout = int(os.getenv("SESSION_TIMEOUT_HOURS", "24")) * 3600  # 24 hours default
            self.initialized = True
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
    
    async def initialize_session_with_user_data(
        self, 
        user_id: str, 
        whatsapp_business_account: str
    ) -> ConversationSession:
        """
        Get or create a session and initialize with existing user data from database
        """
        # Get the session first
        session = self.get_session(user_id)
        
        # If session already has a name, don't fetch again (unless it's a new session)
        if session.customer_name:
            return session
        
        # Fetch organization metadata (primary source for user data)
        try:
            from src.services.messaging import fetch_org_metadata_internal
            
            # Fetch organization metadata - now includes customer_name, properties, etc.
            org_metadata = await fetch_org_metadata_internal(user_id, whatsapp_business_account)
            
            if org_metadata and not org_metadata.get("error"):
                # Set organization info
                session.org_id = org_metadata.get("org_id", "")
                session.org_name = org_metadata.get("org_name", "")
                logger.info(f"🏢 [SESSION_INIT] Loaded org metadata for {user_id}: {session.org_name} (ID: {session.org_id})")
                
                # Set customer name from org metadata
                org_customer_name = org_metadata.get("customer_name")
                if org_customer_name:
                    session.customer_name = org_customer_name
                    session.name_collection_asked = True  # Don't ask again if we have it
                    logger.info(f"✅ [SESSION_INIT] Loaded customer name from org metadata: {org_customer_name}")
                
                # Set user properties if available
                user_properties = org_metadata.get("properties")
                if user_properties:
                    session.context['user_properties'] = user_properties
                    logger.info(f"🏠 [SESSION_INIT] Loaded user properties: {len(user_properties) if isinstance(user_properties, list) else 'N/A'}")
                
            else:
                logger.warning(f"⚠️ [SESSION_INIT] Failed to fetch org metadata for {user_id}: {org_metadata.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ [SESSION_INIT] Failed to fetch user/org data for {user_id}: {e}")
        
        # Update session after potential data loading
        self.update_session(user_id, session)
        
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
        metadata: Dict[str, Any] = None,
        message_type: str = "text"
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
            "type": message_type,  # Adding type field as requested
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
    
    def increment_question_count(self, user_id: str) -> None:
        """
        Increment the question count for a user
        """
        session = self.get_session(user_id)
        session.user_question_count += 1
        self.update_session(user_id, session)
        logger.info(f"User {user_id} question count: {session.user_question_count}")
    
    def should_ask_for_name(self, user_id: str, threshold: int = 2) -> bool:
        """
        Check if we should ask for the user's name
        """
        session = self.get_session(user_id)
        should_ask = (
            session.user_question_count >= threshold and
            not session.customer_name and
            not session.name_collection_asked
        )
        logger.info(f"🤔 [NAME_CHECK] User {user_id}: count={session.user_question_count}, threshold={threshold}, has_name={bool(session.customer_name)}, already_asked={session.name_collection_asked}, should_ask={should_ask}")
        return should_ask
    
    def mark_name_collection_asked(self, user_id: str, pending_question: str = "") -> None:
        """
        Mark that we've asked for the user's name
        """
        session = self.get_session(user_id)
        session.name_collection_asked = True
        session.awaiting_name_response = True
        session.pending_question = pending_question  # Store what they were asking before
        self.update_session(user_id, session)
    
    def save_customer_name(self, user_id: str, name: str) -> None:
        """
        Save the customer's name
        """
        session = self.get_session(user_id)
        session.customer_name = name.strip()
        session.awaiting_name_response = False
        self.update_session(user_id, session)
        logger.info(f"Saved customer name for {user_id}: {name}")
    
    def get_pending_question(self, user_id: str) -> Optional[str]:
        """
        Get the pending question that was asked before name collection
        """
        session = self.get_session(user_id)
        return session.pending_question if session.pending_question else None
    
    def clear_pending_question(self, user_id: str) -> None:
        """
        Clear the pending question after it's been answered
        """
        session = self.get_session(user_id)
        session.pending_question = ""
        self.update_session(user_id, session)
    
    def get_customer_name(self, user_id: str) -> Optional[str]:
        """
        Get the customer's name if available
        """
        session = self.get_session(user_id)
        return session.customer_name if session.customer_name else None
    
    def is_awaiting_name_response(self, user_id: str) -> bool:
        """
        Check if we're waiting for a name response from the user
        """
        session = self.get_session(user_id)
        return session.awaiting_name_response
    
    def get_org_id(self, user_id: str) -> Optional[str]:
        """
        Get the organization ID for a user
        """
        session = self.get_session(user_id)
        return session.org_id if session.org_id else None 