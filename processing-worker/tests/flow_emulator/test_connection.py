#!/usr/bin/env python3
"""
Simple connection test for the WhatsApp Agent processing worker
"""

import asyncio
import httpx
import sys

async def test_connection(url: str = "http://localhost:8080"):
    """Test if the processing worker is reachable"""
    print(f"🔍 Testing connection to {url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                print("✅ Server is running and reachable!")
                print(f"📄 Response preview: {response.text[:100]}...")
                return True
            else:
                print(f"⚠️ Server responded with status: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False
                
    except httpx.ConnectError:
        print("❌ Cannot connect to server")
        print("💡 Make sure the processing worker is running:")
        print("   python main.py")
        return False
    except httpx.TimeoutException:
        print("❌ Connection timeout")
        print("💡 Server might be overloaded or not responding")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    
    print("🧪 WhatsApp Agent Connection Test")
    print("=" * 40)
    
    success = await test_connection(url)
    
    if success:
        print("\n🎉 Ready to run tests!")
        print("Run: python run_test.py quick")
    else:
        print("\n🛑 Fix connection issues before running tests")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
