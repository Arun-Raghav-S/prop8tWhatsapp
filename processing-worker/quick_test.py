#!/usr/bin/env python3
"""
Quick Test Script - Fast agent testing
Run specific questions or all 10 common questions quickly
"""

import os
import sys
import asyncio
import time
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import agent components
from agents.agent_system import WhatsAppAgentSystem
from utils.session_manager import SessionManager

class QuickTester:
    """Quick testing utility"""
    
    def __init__(self):
        self.agent_system = WhatsAppAgentSystem()
        self.session_manager = SessionManager()
        self.test_user_number = "+918281840462"
        self.session = None
        
        # 10 Common Questions (easily editable)
        self.questions = [
            "i am looking for some properties to buy",
            "what all apartments do u have", 
            "show me some villas or apartments to rent",
            "what is the cheapest property to buy",
            "which property have the most easy amenities",
            "which property have a burj khalifa view", 
            "i am looking for a quiet neighborhood to rent property can u show some",
            "can u share some market insights of the property u have",
            "how can i schedule visit bro?",
            "what is the most premium property u have and why?"
        ]
    
    async def test_single(self, question_num: int):
        """Test a single question by number (1-10)"""
        if question_num < 1 or question_num > len(self.questions):
            print(f"❌ Invalid question number. Use 1-{len(self.questions)}")
            return
        
        question = self.questions[question_num - 1]
        await self.run_question(question_num, question)
    
    async def test_all(self):
        """Test all 10 questions quickly"""
        print("🚀 Running all 10 common questions...")
        print("=" * 50)
        
        for i, question in enumerate(self.questions, 1):
            await self.run_question(i, question)
            await asyncio.sleep(0.2)  # Small delay
    
    async def test_custom(self, custom_question: str):
        """Test a custom question"""
        await self.run_question("Custom", custom_question)
    
    async def run_question(self, num, question: str):
        """Run a single question and show result"""
        self.session = self.session_manager.get_session(self.test_user_number)
        
        print(f"\n🧪 Test {num}: {question}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            response = await self.agent_system.process_message(
                message=question,
                session=self.session
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            print(f"⏱️  Response Time: {response_time}ms")
            print(f"🤖 Agent Response:")
            print(f"{response}")
            
            # Quick checks
            issues = []
            if len(response) < 30:
                issues.append("Response too short")
            if '**' in response:
                issues.append("Wrong bold formatting (**)")
            if 'ref:' in response.lower() or 'id:' in response.lower():
                issues.append("Technical jargon visible")
            
            if issues:
                print(f"⚠️  Issues: {', '.join(issues)}")
            else:
                print("✅ Looks good!")
                
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            print(f"❌ Error ({response_time}ms): {str(e)}")

async def main():
    """Main entry point with argument handling"""
    tester = QuickTester()
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == "all":
            await tester.test_all()
        elif arg.isdigit():
            await tester.test_single(int(arg))
        else:
            # Custom question
            await tester.test_custom(" ".join(sys.argv[1:]))
    else:
        # Interactive mode
        print("🔧 Quick Test Script")
        print("=" * 30)
        print("Usage:")
        print("  python quick_test.py all           # Test all 10 questions")
        print("  python quick_test.py 1             # Test question 1")
        print("  python quick_test.py 5             # Test question 5")
        print("  python quick_test.py custom query  # Test custom question")
        print()
        print("Available questions:")
        for i, q in enumerate(tester.questions, 1):
            print(f"  {i}. {q}")
        print()
        
        while True:
            try:
                choice = input("Enter test (1-10, 'all', 'quit', or custom question): ").strip()
                
                if choice.lower() == 'quit':
                    break
                elif choice.lower() == 'all':
                    await tester.test_all()
                elif choice.isdigit():
                    await tester.test_single(int(choice))
                else:
                    await tester.test_custom(choice)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)