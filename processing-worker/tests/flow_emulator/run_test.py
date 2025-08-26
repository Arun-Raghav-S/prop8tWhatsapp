#!/usr/bin/env python3
"""
Simple test runner for WhatsApp Agent flow testing
"""

import asyncio
import sys
import os
from config import TEST_CONFIG, CONVERSATION_FLOWS

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from test_full_conversation_flow import ConversationFlowEmulator

async def run_quick_test():
    """Run a quick test to verify the system is working"""
    print("🚀 QUICK TEST - Basic Property Search")
    print("=" * 50)
    
    emulator = ConversationFlowEmulator()
    
    # Test basic flow
    messages = [
        "Hi",
        "Show me apartments for sale",
        "Buy"
    ]
    
    for i, text in enumerate(messages, 1):
        print(f"\n📤 Message {i}: {text}")
        message = emulator.create_text_message(text)
        result = await emulator.send_message(message)
        
        if result.get("status_code") == 200:
            print("✅ Message sent successfully")
        else:
            print(f"❌ Failed: {result}")
            return False
        
        await emulator.wait_for_processing(4)
    
    print("\n🎉 Quick test completed!")
    return True

async def run_button_test():
    """Test button interactions specifically"""
    print("🔘 BUTTON TEST - Know More & Schedule Visit")
    print("=" * 50)
    
    emulator = ConversationFlowEmulator()
    
    # First get properties
    setup_messages = [
        "Hi",
        "Show me apartments  anywhere and any budget i want to buy", 
    ]
    
    for text in setup_messages:
        message = emulator.create_text_message(text)
        await emulator.send_message(message)
        await emulator.wait_for_processing(4)
    
    print("\n🔘 Testing Know More button...")
    property_id = TEST_CONFIG["property_ids"][3]  # Use the same as in logs
    know_more_msg = emulator.create_button_message(property_id, "knowMore", "Know More")
    await emulator.send_message(know_more_msg)
    await emulator.wait_for_processing(5)
    
    print("\n🔘 Testing Schedule Visit button...")
    property_id = TEST_CONFIG["property_ids"][1]  # Use different property
    schedule_msg = emulator.create_button_message(property_id, "scheduleVisit", "Schedule Visit")
    await emulator.send_message(schedule_msg)
    await emulator.wait_for_processing(5)
    
    print("\n📅 Providing visit time...")
    time_msg = emulator.create_text_message("Tomorrow at 3 PM")
    await emulator.send_message(time_msg)
    await emulator.wait_for_processing(4)
    
    print("\n🎉 Button test completed!")

async def run_flow_test(flow_name: str):
    """Run a specific conversation flow"""
    if flow_name not in CONVERSATION_FLOWS:
        print(f"❌ Unknown flow: {flow_name}")
        print(f"Available flows: {list(CONVERSATION_FLOWS.keys())}")
        return
    
    print(f"🎬 RUNNING FLOW: {flow_name.upper()}")
    print("=" * 50)
    
    emulator = ConversationFlowEmulator()
    flow = CONVERSATION_FLOWS[flow_name]
    
    for i, step in enumerate(flow, 1):
        print(f"\n📤 Step {i}: {step['type'].upper()}")
        
        if step["type"] == "text":
            print(f"💬 Text: '{step['content']}'")
            message = emulator.create_text_message(step["content"])
            
        elif step["type"] == "button":
            print(f"🔘 Button: '{step['text']}' (Property: {step['property_id'][:8]}...)")
            message = emulator.create_button_message(
                step["property_id"], 
                step["action"], 
                step["text"]
            )
        
        result = await emulator.send_message(message)
        
        if result.get("status_code") == 200:
            print("✅ Sent successfully")
        else:
            print(f"❌ Failed: {result}")
            break
        
        # Wait longer for property searches
        wait_time = 8 if "show me" in step.get("content", "").lower() else 4
        await emulator.wait_for_processing(wait_time)
    
    print(f"\n🎉 Flow '{flow_name}' completed!")

def print_usage():
    """Print usage instructions"""
    print("🧪 WhatsApp Agent Flow Emulator")
    print("=" * 40)
    print("Usage:")
    print("  python run_test.py quick          # Quick basic test")
    print("  python run_test.py buttons        # Test button interactions")
    print("  python run_test.py full           # Full conversation journey")
    print("  python run_test.py flow <name>    # Run specific flow")
    print("\nAvailable flows:")
    for flow_name in CONVERSATION_FLOWS.keys():
        print(f"  - {flow_name}")
    print("\nMake sure the processing worker is running on localhost:8080")
    print("Check your WhatsApp and logs/extracted_payloads.log for results!")

async def main():
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "quick":
            await run_quick_test()
        elif command == "buttons":
            await run_button_test()
        elif command == "full":
            await run_flow_test("full_journey")
        elif command == "flow":
            if len(sys.argv) < 3:
                print("❌ Please specify flow name")
                print(f"Available: {list(CONVERSATION_FLOWS.keys())}")
                return
            await run_flow_test(sys.argv[2])
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
