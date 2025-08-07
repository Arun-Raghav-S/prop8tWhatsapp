#!/usr/bin/env python3
"""
Local Terminal Client for WhatsApp Agent Testing

This client allows you to test the agent locally without pub/sub services.
You can interact directly with the agent through the terminal.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import agent components
from agents.agent_system import WhatsAppAgentSystem
from utils.session_manager import SessionManager
from src.services.messaging import fetch_org_metadata_internal

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LocalTestClient:
    """Local test client for the WhatsApp agent"""
    
    def __init__(self):
        self.agent_system = WhatsAppAgentSystem()
        self.session_manager = SessionManager()
        self.test_user_number = "+918281840462"  # Default test user
        self.test_business_account = "543107385407043"  # Default test business account
        self.session = None
        
    async def start(self):
        """Start the local test client"""
        print("🚀 WhatsApp Agent Local Test Client")
        print("=" * 50)
        print(f"Test User: {self.test_user_number}")
        print(f"Business Account: {self.test_business_account}")
        print("=" * 50)
        print("Commands:")
        print("  /help         - Show this help")
        print("  /user <phone> - Change test user number")
        print("  /account <id> - Change business account ID")
        print("  /session      - Show current session info")
        print("  /org          - Fetch organization metadata")
        print("  /quit         - Exit the client")
        print("  <message>     - Send message to agent")
        print("=" * 50)
        
        # Initialize session with user data (fetch from database)
        self.session = await self.session_manager.initialize_session_with_user_data(
            self.test_user_number, 
            self.test_business_account
        )
        
        # Main interaction loop
        while True:
            try:
                user_input = input(f"\n[{self.test_user_number}] > ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.startswith('/'):
                    await self.handle_command(user_input)
                else:
                    await self.send_message(user_input)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"Client error: {e}")
    
    async def handle_command(self, command: str):
        """Handle special commands"""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/help':
            print("\nAvailable commands:")
            print("  /help         - Show this help")
            print("  /user <phone> - Change test user number (e.g., /user +1987654321)")
            print("  /account <id> - Change business account ID")
            print("  /session      - Show current session info")
            print("  /org          - Fetch organization metadata")
            print("  /quit         - Exit the client")
            print("  <message>     - Send any message to test the agent")
            
        elif cmd == '/user':
            if len(parts) > 1:
                old_user = self.test_user_number
                self.test_user_number = parts[1]
                # Initialize session with user data for the new user
                self.session = await self.session_manager.initialize_session_with_user_data(
                    self.test_user_number, 
                    self.test_business_account
                )
                print(f"✅ Changed user from {old_user} to {self.test_user_number}")
                # Show if name was found
                if self.session.customer_name:
                    print(f"📋 Found existing user: {self.session.customer_name}")
            else:
                print("❌ Usage: /user <phone_number>")
                
        elif cmd == '/account':
            if len(parts) > 1:
                old_account = self.test_business_account
                self.test_business_account = parts[1]
                print(f"✅ Changed business account from {old_account} to {self.test_business_account}")
            else:
                print("❌ Usage: /account <business_account_id>")
                
        elif cmd == '/session':
            print(f"\n📱 Current Session Info:")
            print(f"  User: {self.test_user_number}")
            print(f"  Business Account: {self.test_business_account}")
            print(f"  Session Active: {self.session is not None}")
            if self.session:
                print(f"  User Name: {self.session.customer_name or 'Not found'}")
                print(f"  Organization: {getattr(self.session, 'org_name', 'Not found')}")
                print(f"  Question Count: {getattr(self.session, 'user_question_count', 0)}")
                print(f"  Full Session Data: {vars(self.session)}")
                
        elif cmd == '/org':
            print("🏢 Fetching organization metadata...")
            try:
                org_data = await fetch_org_metadata_internal(
                    self.test_user_number,
                    self.test_business_account
                )
                print(f"✅ Organization Data:")
                print(f"  {org_data}")
            except Exception as e:
                print(f"❌ Error fetching org data: {e}")
                
        elif cmd == '/quit':
            print("👋 Goodbye!")
            sys.exit(0)
            
        else:
            print(f"❌ Unknown command: {cmd}")
            print("Type /help for available commands")
    
    async def send_message(self, message: str):
        """Send a message to the agent and display the response"""
        try:
            print(f"💬 Sending: {message}")
            print("🤖 Agent thinking...")
            
            # Process message through agent system
            response = await self.agent_system.process_message(
                message=message,
                session=self.session
            )
            
            print(f"🤖 Agent Response:")
            print(f"   {response}")
            
            # Update session
            self.session_manager.update_session(self.test_user_number, self.session)
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            logger.error(f"Message processing error: {e}")
    
    def check_config(self):
        """Check if required configuration is available"""
        print("🔍 Checking configuration...")
        
        required_env_vars = [
            "NEXT_PUBLIC_SUPABASE_URL",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY",
            "AISENSY_BASE_URL",
            "AISENSY_ACCESS_TOKEN"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print("⚠️  Warning: Missing environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
            print("\nThe client may not work properly without these.")
            return False
        else:
            print("✅ All required environment variables are set")
            return True

async def main():
    """Main entry point"""
    print("🔧 Initializing Local Test Client...")
    
    client = LocalTestClient()
    
    # Check configuration
    client.check_config()
    
    # Start the client
    await client.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)