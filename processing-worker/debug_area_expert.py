"""
Debug script to check if area expert will trigger for a given session
Useful for troubleshooting why area expert might not be firing
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from utils.session_manager import SessionManager
from utils.logger import setup_logger

logger = setup_logger(__name__)


def check_session_requirements(user_number: str):
    """
    Check what requirements are stored for a user and if area expert would trigger
    
    Args:
        user_number: Phone number like +971501234567
    """
    session_manager = SessionManager()
    
    print("\n" + "="*80)
    print(f"🔍 DEBUGGING AREA EXPERT FOR USER: {user_number}")
    print("="*80)
    
    # Get session
    session = session_manager.get_session(user_number)
    
    print(f"\n📊 Session Info:")
    print(f"   User ID: {session.user_id}")
    print(f"   Customer Name: {session.customer_name or 'Not set'}")
    print(f"   Org ID: {session.org_id or 'Not set'}")
    print(f"   Created: {session.created_at}")
    print(f"   Last Updated: {session.last_updated}")
    
    print(f"\n📋 Session Context Keys:")
    for key in session.context.keys():
        print(f"   - {key}")
    
    # Check for requirements in different locations
    print(f"\n🔍 Checking Requirements Storage:")
    
    # user_requirements (unified conversation engine)
    user_reqs = session.context.get('user_requirements', {})
    if user_reqs:
        print(f"\n   ✅ Found 'user_requirements':")
        print(f"      Location: {user_reqs.get('location')}")
        print(f"      Transaction Type: {user_reqs.get('transaction_type')}")
        print(f"      Property Type: {user_reqs.get('property_type')}")
        print(f"      Budget: {user_reqs.get('budget_min')} - {user_reqs.get('budget_max')}")
    else:
        print(f"   ❌ No 'user_requirements' found")
    
    # ai_requirements (agent system)
    ai_reqs = session.context.get('ai_requirements', {})
    if ai_reqs:
        print(f"\n   ✅ Found 'ai_requirements':")
        print(f"      Location: {ai_reqs.get('location')}")
        print(f"      Transaction Type: {ai_reqs.get('transaction_type')}")
        print(f"      Property Type: {ai_reqs.get('property_type')}")
        print(f"      Budget: {ai_reqs.get('budget_min')} - {ai_reqs.get('budget_max')}")
    else:
        print(f"   ❌ No 'ai_requirements' found")
    
    # requirements (legacy/test)
    reqs = session.context.get('requirements', {})
    if reqs:
        print(f"\n   ✅ Found 'requirements':")
        print(f"      Location: {reqs.get('location')}")
        print(f"      Transaction Type: {reqs.get('transaction_type')}")
        print(f"      Property Type: {reqs.get('property_type')}")
        print(f"      Budget: {reqs.get('budget_min')} - {reqs.get('budget_max')}")
    else:
        print(f"   ❌ No 'requirements' found")
    
    # Determine which requirements to use (same logic as main.py)
    requirements = user_reqs or ai_reqs or reqs
    
    print(f"\n🎯 Area Expert Trigger Check:")
    
    if not requirements:
        print(f"   ❌ NO REQUIREMENTS FOUND")
        print(f"   → Area expert will NOT trigger")
        print(f"   → User needs to provide location and buy/rent preference")
        return
    
    area = requirements.get('location')
    transaction_type = requirements.get('transaction_type')
    
    print(f"   Area: {area or 'NOT SET'}")
    print(f"   Transaction Type: {transaction_type or 'NOT SET'}")
    
    if area and transaction_type:
        print(f"\n   ✅ WILL TRIGGER AREA EXPERT")
        print(f"   → Area: {area}")
        print(f"   → Type: {transaction_type}")
        print(f"   → Org ID: {session.org_id}")
        print(f"   → WhatsApp Business Account: {session.context.get('whatsapp_business_account', 'Not set')}")
    else:
        print(f"\n   ❌ WILL NOT TRIGGER")
        if not area:
            print(f"   → Missing: Location/Area")
        if not transaction_type:
            print(f"   → Missing: Transaction Type (buy/rent)")
    
    # Check conversation history
    print(f"\n💬 Recent Conversation ({len(session.conversation_history)} messages):")
    for msg in session.conversation_history[-5:]:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')[:100]
        print(f"   {role}: {content}...")
    
    print("\n" + "="*80)
    print("✅ Debug complete!")
    print("="*80 + "\n")


def list_all_sessions():
    """List all active sessions"""
    session_manager = SessionManager()
    
    print("\n" + "="*80)
    print("📋 ALL ACTIVE SESSIONS")
    print("="*80 + "\n")
    
    if not session_manager.sessions:
        print("No active sessions found.\n")
        return
    
    for user_id, session in session_manager.sessions.items():
        print(f"User: {user_id}")
        print(f"  Name: {session.customer_name or 'Not set'}")
        print(f"  Org: {session.org_id or 'Not set'}")
        print(f"  Messages: {len(session.conversation_history)}")
        
        # Check if has requirements
        has_user_reqs = bool(session.context.get('user_requirements'))
        has_ai_reqs = bool(session.context.get('ai_requirements'))
        has_reqs = bool(session.context.get('requirements'))
        
        if has_user_reqs or has_ai_reqs or has_reqs:
            print(f"  ✅ Has requirements")
        else:
            print(f"  ❌ No requirements")
        print()
    
    print("="*80 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_all_sessions()
        else:
            user_number = sys.argv[1]
            check_session_requirements(user_number)
    else:
        print("\nUsage:")
        print("  python debug_area_expert.py <phone_number>")
        print("  python debug_area_expert.py list")
        print("\nExample:")
        print("  python debug_area_expert.py +971501234567")
        print("  python debug_area_expert.py list")
        print()

