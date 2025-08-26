#!/usr/bin/env python3
"""
Full Conversation Flow Emulator
Emulates the exact flow from extracted_payloads.log to test the entire system
"""

import asyncio
import json
import time
import httpx
import random
import string
import base64
from typing import Dict, Any
from datetime import datetime
import sys
import os

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

class ConversationFlowEmulator:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.business_account = "543107385407043"  # From logs
        self.user_phone = "918281840462"  # From logs (without +)
        self.user_phone_full = "+918281840462"  # With +
        self.message_counter = 1
        
    def generate_message_id(self) -> str:
        """Generate a WhatsApp-like message ID"""
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
        return f"wamid.HBgMOTE4MjgxODQwNDYyFQIAEhgg{random_part}A"
    
    def create_envelope(self, messages: list) -> Dict[str, Any]:
        """Create the Pub/Sub message envelope like AiSensy sends"""
        return {
            "message": {
                "data": None,  # Will be filled by process_message
                "messageId": f"test-message-{self.message_counter}",
                "publishTime": datetime.now().isoformat(),
            },
            "subscription": "projects/test/subscriptions/test"
        }
    
    def create_text_message(self, text: str) -> Dict[str, Any]:
        """Create a text message like from AiSensy webhook"""
        timestamp = str(int(time.time()))
        message_id = self.generate_message_id()
        
        return {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": self.business_account,
                "changes": [{
                    "field": "messages",
                    "value": {
                        "messages": [{
                            "from": self.user_phone,
                            "id": message_id,
                            "timestamp": timestamp,
                            "text": {
                                "body": text
                            },
                            "type": "text"
                        }]
                    }
                }]
            }]
        }
    
    def create_button_message(self, property_id: str, action: str, button_text: str) -> Dict[str, Any]:
        """Create a button click message like from AiSensy webhook"""
        timestamp = str(int(time.time()))
        message_id = self.generate_message_id()
        
        return {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": self.business_account,
                "changes": [{
                    "field": "messages",
                    "value": {
                        "messages": [{
                            "context": {
                                "from": "919345007934",  # Bot number from logs
                                "id": self.generate_message_id()
                            },
                            "from": self.user_phone,
                            "id": message_id,
                            "timestamp": timestamp,
                            "type": "button",
                            "button": {
                                "payload": f"{property_id}_{action}",
                                "text": button_text
                            }
                        }]
                    }
                }]
            }]
        }
    
    async def send_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to the processing worker in Pub/Sub format"""
        print(f"\n🚀 SENDING MESSAGE #{self.message_counter}")
        print(f"📱 From: {self.user_phone_full}")
        
        # Print message content based on type
        message = message_data["entry"][0]["changes"][0]["value"]["messages"][0]
        if message["type"] == "text":
            text = message["text"]["body"]
            print(f"💬 Text: '{text}'")
        elif message["type"] == "button":
            button = message["button"]
            print(f"🔘 Button: '{button['text']}' (payload: {button['payload']})")
        
        print(f"🔧 Business Account: {self.business_account}")
        print("-" * 60)
        
        try:
            # Encode message_data as base64 for Pub/Sub format
            data_str = json.dumps(message_data)
            encoded_data = base64.b64encode(data_str.encode('utf-8')).decode('utf-8')
            
            # Create Pub/Sub envelope
            pubsub_envelope = {
                "message": {
                    "data": encoded_data,
                    "messageId": f"test-message-{self.message_counter}",
                    "publishTime": datetime.now().isoformat(),
                    "attributes": {}
                },
                "subscription": "projects/test/subscriptions/test"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/",
                    json=pubsub_envelope,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"✅ Response Status: {response.status_code}")
                if response.status_code != 200:
                    print(f"❌ Response Body: {response.text}")
                    
                self.message_counter += 1
                return {
                    "status_code": response.status_code,
                    "response": response.text
                }
                
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return {"error": str(e)}
    
    async def wait_for_processing(self, seconds: int = 3):
        """Wait for message processing with countdown"""
        print(f"⏳ Waiting {seconds} seconds for processing...")
        for i in range(seconds, 0, -1):
            print(f"   {i}...", end='\r')
            await asyncio.sleep(1)
        print("   ✅ Ready!")
    
    async def run_full_conversation_flow(self):
        """Run the exact conversation flow from the logs"""
        print("🎬 STARTING FULL CONVERSATION FLOW EMULATION")
        print("=" * 70)
        print(f"📞 Testing with phone: {self.user_phone_full}")
        print(f"🏢 Business Account: {self.business_account}")
        print(f"🎯 Target URL: {self.base_url}")
        print("=" * 70)
        
        # Step 1: Initial "Hi" message
        print("\n🎬 STEP 1: Initial greeting")
        message1 = self.create_text_message("Hi")
        await self.send_message(message1)
        await self.wait_for_processing(5)
        
        # Step 2: Property search request
        print("\n🎬 STEP 2: Property search request")
        message2 = self.create_text_message("Show me some apartments anywhere and any price bro")
        await self.send_message(message2)
        await self.wait_for_processing(5)
        
        # Step 3: Specify "Buy"
        print("\n🎬 STEP 3: Specify transaction type")
        message3 = self.create_text_message("Buy")
        await self.send_message(message3)
        await self.wait_for_processing(8)  # Property search takes longer
        
        # Step 4: Test "Know More" button (using property ID from logs)
        print("\n🎬 STEP 4: Test 'Know More' button")
        property_id_1 = "4900fde3-eaf4-4bf5-ab3f-241248f512e5"  # From logs
        button_message1 = self.create_button_message(property_id_1, "knowMore", "Know More")
        await self.send_message(button_message1)
        await self.wait_for_processing(5)
        
        # Step 5: Test "Schedule Visit" button (using different property ID from logs)
        print("\n🎬 STEP 5: Test 'Schedule Visit' button")
        property_id_2 = "a839d7a9-4035-4c3f-accd-b71286ee0aad"  # From logs
        button_message2 = self.create_button_message(property_id_2, "scheduleVisit", "Schedule Visit")
        await self.send_message(button_message2)
        await self.wait_for_processing(5)
        
        # Step 6: Provide date/time for scheduling
        print("\n🎬 STEP 6: Provide visit date/time")
        message4 = self.create_text_message("Tomorrow at 3 PM")
        await self.send_message(message4)
        await self.wait_for_processing(5)
        
        print("\n🎉 CONVERSATION FLOW COMPLETED!")
        print("=" * 70)
        print("📋 Check the following to verify everything worked:")
        print("   1. Your WhatsApp messages from the bot")
        print("   2. logs/extracted_payloads.log for new entries")
        print("   3. Server console for processing details")
        print("=" * 70)

async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WhatsApp Agent Flow Emulator')
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Base URL of the processing worker (default: http://localhost:8080)')
    parser.add_argument('--test-connection', action='store_true',
                       help='Test connection to the server first')
    
    args = parser.parse_args()
    
    emulator = ConversationFlowEmulator(args.url)
    
    if args.test_connection:
        print("🔍 Testing connection to server...")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{args.url}/")
                if response.status_code == 200:
                    print("✅ Server is reachable!")
                    print(f"📄 Response: {response.text[:200]}...")
                else:
                    print(f"⚠️ Server returned status {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot reach server: {e}")
            print("💡 Make sure the processing worker is running on the specified URL")
            return
        
        print("\n" + "="*50)
    
    try:
        await emulator.run_full_conversation_flow()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
