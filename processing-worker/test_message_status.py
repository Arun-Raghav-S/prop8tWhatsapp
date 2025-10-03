#!/usr/bin/env python3
"""
Test script for message status tracking implementation
Run this to verify the status tracking is working correctly
"""

import asyncio
import httpx
import json
import base64
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8080"  # Change to your deployment URL
BUSINESS_ACCOUNT_ID = "your_business_account_id"  # Replace with your actual ID

async def test_status_webhook(status_type: str, message_id: str):
    """
    Send a test status webhook to your endpoint
    
    Args:
        status_type: One of 'sent', 'delivered', 'read'
        message_id: Test message ID
    """
    print(f"\n{'='*60}")
    print(f"🧪 Testing {status_type.upper()} status webhook")
    print(f"{'='*60}")
    
    # Create the webhook payload matching AiSensy format
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": BUSINESS_ACCOUNT_ID,
            "changes": [{
                "field": "messages",
                "value": {
                    "statuses": [{
                        "id": message_id,
                        "status": status_type,
                        "timestamp": str(int(datetime.now().timestamp())),
                        "recipient_id": "919876543210"
                    }]
                }
            }]
        }]
    }
    
    # Encode the payload in Pub/Sub format (base64 encoded)
    payload_json = json.dumps(webhook_payload)
    payload_base64 = base64.b64encode(payload_json.encode()).decode()
    
    # Create Pub/Sub message envelope
    pubsub_envelope = {
        "message": {
            "data": payload_base64,
            "attributes": {
                "test": "true"
            }
        }
    }
    
    print(f"📤 Sending webhook to {BASE_URL}/")
    print(f"📦 Payload: {json.dumps(webhook_payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/",
                json=pubsub_envelope
            )
            
            print(f"\n📊 Response Status: {response.status_code}")
            print(f"📊 Response Body: {response.text}")
            
            if response.status_code == 200:
                print(f"✅ {status_type.upper()} status webhook sent successfully!")
                return True
            else:
                print(f"❌ Failed to send {status_type} status webhook")
                return False
                
    except Exception as e:
        print(f"❌ Error sending webhook: {e}")
        return False


async def run_full_test():
    """Run a complete test of the message status lifecycle"""
    print("\n" + "="*60)
    print("🚀 Starting Message Status Tracking Test")
    print("="*60)
    
    # Use a unique message ID for this test
    test_message_id = f"test_msg_{int(datetime.now().timestamp())}"
    print(f"\n🆔 Test Message ID: {test_message_id}")
    
    # Test 1: Send "sent" status
    await asyncio.sleep(1)
    result1 = await test_status_webhook("sent", test_message_id)
    
    # Test 2: Send "delivered" status
    await asyncio.sleep(2)
    result2 = await test_status_webhook("delivered", test_message_id)
    
    # Test 3: Send "read" status
    await asyncio.sleep(2)
    result3 = await test_status_webhook("read", test_message_id)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"✅ Sent Status:      {'PASS' if result1 else 'FAIL'}")
    print(f"✅ Delivered Status: {'PASS' if result2 else 'FAIL'}")
    print(f"✅ Read Status:      {'PASS' if result3 else 'FAIL'}")
    
    if all([result1, result2, result3]):
        print("\n✅ All tests passed!")
        print("\n🔍 Verify in Database:")
        print(f"SELECT bsp_msg_id, whatsapp_status FROM message_logs WHERE bsp_msg_id = '{test_message_id}';")
        print("\n📊 Expected whatsapp_status:")
        print(json.dumps({
            "sent": "2024-10-03T...",
            "delivered": "2024-10-03T...",
            "read": "2024-10-03T..."
        }, indent=2))
    else:
        print("\n❌ Some tests failed. Check your logs and configuration.")
    
    print("\n" + "="*60)


async def test_out_of_order():
    """Test out-of-order status delivery (read before delivered)"""
    print("\n" + "="*60)
    print("🧪 Testing Out-of-Order Status Delivery")
    print("="*60)
    
    test_message_id = f"test_ooo_{int(datetime.now().timestamp())}"
    print(f"\n🆔 Test Message ID: {test_message_id}")
    
    # Send "sent" first
    await test_status_webhook("sent", test_message_id)
    await asyncio.sleep(1)
    
    # Send "read" before "delivered" (simulating out-of-order delivery)
    await test_status_webhook("read", test_message_id)
    
    print("\n🔍 Verify in Database:")
    print(f"SELECT bsp_msg_id, whatsapp_status FROM message_logs WHERE bsp_msg_id = '{test_message_id}';")
    print("\n📊 Should have both 'delivered' and 'read' with same timestamp!")


def print_help():
    """Print help information"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║         Message Status Tracking - Test Script                  ║
╚════════════════════════════════════════════════════════════════╝

SETUP:
1. Make sure your server is running (locally or deployed)
2. Update BASE_URL in this script to point to your server
3. Update BUSINESS_ACCOUNT_ID with your actual WhatsApp business account ID

USAGE:
    python test_message_status.py

WHAT IT TESTS:
✅ Sent status webhook
✅ Delivered status webhook  
✅ Read status webhook
✅ Out-of-order delivery handling

AFTER RUNNING:
Check your database with:
    SELECT bsp_msg_id, whatsapp_status FROM message_logs 
    WHERE whatsapp_status IS NOT NULL 
    ORDER BY created_at DESC LIMIT 5;

Check your logs for:
    📊 [STATUS_WEBHOOK] Received status updates
    🚀 [STATUS] Launched background task
    ✅ [STATUS] Successfully updated status

Need help? See MESSAGE_STATUS_IMPLEMENTATION.md
    """)


if __name__ == "__main__":
    print_help()
    
    # Run the tests
    asyncio.run(run_full_test())
    
    # Run out-of-order test
    asyncio.run(test_out_of_order())

