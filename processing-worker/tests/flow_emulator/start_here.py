#!/usr/bin/env python3
"""
WhatsApp Agent Testing - START HERE
Quick guide to test your WhatsApp Agent system
"""

def print_banner():
    print("🧪 WhatsApp Agent Flow Emulator")
    print("=" * 50)
    print("Test your entire WhatsApp Agent system end-to-end!")
    print("Uses your real business account and phone number")
    print("=" * 50)

def print_quick_start():
    print("\n🚀 QUICK START")
    print("-" * 20)
    print("1. Make sure your processing worker is running:")
    print("   cd ../../")
    print("   python main.py")
    print()
    print("2. Test connection:")
    print("   python test_connection.py")
    print()
    print("3. Run a quick test:")
    print("   python run_test.py quick")
    print()
    print("4. Monitor logs in another terminal:")
    print("   python monitor_logs.py")

def print_available_tests():
    print("\n🧪 AVAILABLE TESTS")
    print("-" * 20)
    print("📋 python run_test.py quick        # Basic property search")
    print("🔘 python run_test.py buttons      # Button interactions")
    print("🎬 python run_test.py full         # Complete journey")
    print("🔍 python test_connection.py       # Test server connection")
    print("📊 python monitor_logs.py          # Watch logs live")

def print_what_youll_see():
    print("\n👀 WHAT YOU'LL SEE")
    print("-" * 20)
    print("📱 WhatsApp messages on +918281840462")
    print("🎠 Property carousels with clickable buttons")
    print("📋 Property details when clicking 'Know More'")
    print("📅 Scheduling flow when clicking 'Schedule Visit'")
    print("📄 New entries in logs/extracted_payloads.log")

def print_test_config():
    print("\n⚙️  TEST CONFIGURATION")
    print("-" * 20)
    print("🏢 Business Account: 543107385407043")
    print("📞 Phone Number: +918281840462")
    print("🌐 Server URL: http://localhost:8080")
    print("🏠 Property IDs: From your actual logs")

def print_troubleshooting():
    print("\n🛠️  TROUBLESHOOTING")
    print("-" * 20)
    print("❌ 'Cannot reach server' → Run processing worker first")
    print("❌ 'No valid access token' → Check environment variables")
    print("❌ 'Property not found' → Property IDs from logs might be old")
    print("❌ 'Button clicks fail' → This is what we just fixed!")

def main():
    print_banner()
    print_quick_start()
    print_available_tests()
    print_what_youll_see()
    print_test_config()
    print_troubleshooting()
    
    print("\n🎯 RECOMMENDED TESTING ORDER")
    print("-" * 30)
    print("1. python test_connection.py")
    print("2. python monitor_logs.py     # In another terminal") 
    print("3. python run_test.py quick   # In first terminal")
    print("4. python run_test.py buttons # Test the fixes!")
    print("5. Check your WhatsApp for messages!")
    
    print("\n📖 For detailed info, see README.md")
    print("🎉 Happy testing!")

if __name__ == "__main__":
    main()
