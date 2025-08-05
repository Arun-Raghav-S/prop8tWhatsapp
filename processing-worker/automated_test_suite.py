#!/usr/bin/env python3
"""
Automated Test Suite for WhatsApp Agent
Tests 10 common user questions and validates responses
"""

import os
import sys
import asyncio
import logging
import time
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import agent components
from agents.agent_system import WhatsAppAgentSystem
from utils.session_manager import SessionManager

# Set up logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise for clean test output
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentTestSuite:
    """Automated test suite for WhatsApp agent"""
    
    def __init__(self):
        self.agent_system = WhatsAppAgentSystem()
        self.session_manager = SessionManager()
        self.test_user_number = "+918281840462"
        self.session = None
        
        # Test questions (easily editable)
        self.test_questions = [
            {
                "id": 1,
                "question": "i am looking for some properties to buy",
                "expected_type": "property_search",
                "expected_features": ["properties found", "carousel or list"],
                "min_response_length": 50
            },
            {
                "id": 2,
                "question": "what all apartments do u have",
                "expected_type": "property_search",
                "expected_features": ["apartments", "properties"],
                "min_response_length": 50
            },
            {
                "id": 3,
                "question": "show me some villas or apartments to rent",
                "expected_type": "property_search",
                "expected_features": ["villas", "apartments", "rent"],
                "min_response_length": 50
            },
            {
                "id": 4,
                "question": "what is the cheapest property to buy",
                "expected_type": "statistical_or_search",
                "expected_features": ["cheapest", "AED", "price"],
                "min_response_length": 30
            },
            {
                "id": 5,
                "question": "which property have the most easy amenities",
                "expected_type": "property_search",
                "expected_features": ["amenities", "properties"],
                "min_response_length": 40
            },
            {
                "id": 6,
                "question": "which property have a burj khalifa view",
                "expected_type": "property_search",
                "expected_features": ["burj khalifa", "view", "properties"],
                "min_response_length": 40
            },
            {
                "id": 7,
                "question": "i am looking for a quiet neighborhood to rent property can u show some",
                "expected_type": "property_search",
                "expected_features": ["quiet", "neighborhood", "rent"],
                "min_response_length": 40
            },
            {
                "id": 8,
                "question": "can u share some market insights of the property u have",
                "expected_type": "conversation_or_insights",
                "expected_features": ["market", "insights", "properties"],
                "min_response_length": 50
            },
            {
                "id": 9,
                "question": "how can i schedule visit bro?",
                "expected_type": "followup_or_conversation",
                "expected_features": ["schedule", "visit", "book"],
                "min_response_length": 30
            },
            {
                "id": 10,
                "question": "what is the most premium property u have and why?",
                "expected_type": "property_search",
                "expected_features": ["premium", "luxury", "property"],
                "min_response_length": 40
            }
        ]
        
        self.results = []
        
    async def run_all_tests(self):
        """Run all test questions and generate report"""
        print("🚀 WhatsApp Agent Automated Test Suite")
        print("=" * 60)
        print(f"📱 Test User: {self.test_user_number}")
        print(f"📝 Total Questions: {len(self.test_questions)}")
        print("=" * 60)
        
        # Initialize session
        self.session = self.session_manager.get_session(self.test_user_number)
        
        # Run each test
        for i, test_case in enumerate(self.test_questions, 1):
            print(f"\n🧪 Test {i}/{len(self.test_questions)}: Running...")
            result = await self.run_single_test(test_case)
            self.results.append(result)
            
            # Show quick result
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"   {status} - {result['response_time']}ms")
            
            # Small delay between tests
            await asyncio.sleep(0.5)
        
        # Generate final report
        self.generate_report()
    
    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case"""
        start_time = time.time()
        
        try:
            # Send question to agent
            response = await self.agent_system.process_message(
                message=test_case["question"],
                session=self.session
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Validate response
            validation_result = self.validate_response(test_case, response)
            
            return {
                "test_id": test_case["id"],
                "question": test_case["question"],
                "response": response,
                "response_time": response_time,
                "passed": validation_result["passed"],
                "issues": validation_result["issues"],
                "score": validation_result["score"]
            }
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return {
                "test_id": test_case["id"],
                "question": test_case["question"],
                "response": f"ERROR: {str(e)}",
                "response_time": response_time,
                "passed": False,
                "issues": [f"Exception occurred: {str(e)}"],
                "score": 0
            }
    
    def validate_response(self, test_case: Dict[str, Any], response: str) -> Dict[str, Any]:
        """Validate if response meets expectations"""
        issues = []
        score = 0
        max_score = 10
        
        response_lower = response.lower()
        
        # Check 1: Response length (2 points)
        if len(response) >= test_case["min_response_length"]:
            score += 2
        else:
            issues.append(f"Response too short: {len(response)} chars (min: {test_case['min_response_length']})")
        
        # Check 2: Expected features present (4 points)
        features_found = 0
        for feature in test_case["expected_features"]:
            if feature.lower() in response_lower:
                features_found += 1
        
        feature_score = int((features_found / len(test_case["expected_features"])) * 4)
        score += feature_score
        
        if feature_score < 4:
            missing_features = [f for f in test_case["expected_features"] if f.lower() not in response_lower]
            issues.append(f"Missing expected features: {missing_features}")
        
        # Check 3: WhatsApp formatting (2 points)
        formatting_score = 0
        if '*' in response and '**' not in response:  # Correct WhatsApp bold
            formatting_score += 1
        if any(emoji in response for emoji in ['🏠', '💰', '📍', '✨', '🔍']):  # Has emojis
            formatting_score += 1
        
        score += formatting_score
        if formatting_score < 2:
            format_issues = []
            if '**' in response:
                format_issues.append("Using **bold** instead of *bold*")
            if not any(emoji in response for emoji in ['🏠', '💰', '📍', '✨', '🔍']):
                format_issues.append("Missing emojis")
            if format_issues:
                issues.append(f"Formatting issues: {format_issues}")
        
        # Check 4: No technical jargon (1 point)
        technical_terms = ['ref:', 'id:', 'error:', 'exception:', 'null']
        has_technical = any(term in response_lower for term in technical_terms)
        if not has_technical:
            score += 1
        else:
            issues.append("Contains technical jargon")
        
        # Check 5: Appropriate response type (1 point)
        if self.check_response_type(test_case, response):
            score += 1
        else:
            issues.append(f"Unexpected response type for {test_case['expected_type']}")
        
        passed = score >= 7  # 70% pass threshold
        
        return {
            "passed": passed,
            "score": score,
            "max_score": max_score,
            "issues": issues
        }
    
    def check_response_type(self, test_case: Dict[str, Any], response: str) -> bool:
        """Check if response type matches expectations"""
        response_lower = response.lower()
        expected_type = test_case["expected_type"]
        
        if expected_type == "property_search":
            return any(keyword in response_lower for keyword in [
                "found", "properties", "property", "here are", "search", "results"
            ])
        elif expected_type == "statistical_or_search":
            return any(keyword in response_lower for keyword in [
                "cheapest", "most affordable", "aed", "price", "property"
            ])
        elif expected_type == "conversation_or_insights":
            return any(keyword in response_lower for keyword in [
                "market", "insights", "data", "trends", "analysis", "can help"
            ])
        elif expected_type == "followup_or_conversation":
            return any(keyword in response_lower for keyword in [
                "schedule", "visit", "book", "contact", "arrange", "how to"
            ])
        
        return True  # Default to pass for unknown types
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # Overall stats
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["passed"])
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests) * 100
        
        avg_response_time = sum(r["response_time"] for r in self.results) / total_tests
        avg_score = sum(r["score"] for r in self.results) / total_tests
        
        print(f"✅ Passed: {passed_tests}/{total_tests} ({pass_rate:.1f}%)")
        print(f"❌ Failed: {failed_tests}/{total_tests}")
        print(f"⏱️  Avg Response Time: {avg_response_time:.0f}ms")
        print(f"📈 Avg Score: {avg_score:.1f}/10")
        
        # Detailed results
        print(f"\n📝 DETAILED RESULTS:")
        print("-" * 60)
        
        for result in self.results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"\n{result['test_id']}. {status} ({result['score']}/10) - {result['response_time']}ms")
            print(f"   Q: {result['question']}")
            
            if result["issues"]:
                print(f"   Issues: {'; '.join(result['issues'])}")
            
            # Show response preview (first 100 chars)
            response_preview = result["response"][:100]
            if len(result["response"]) > 100:
                response_preview += "..."
            print(f"   Response: {response_preview}")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        print("-" * 60)
        
        if failed_tests == 0:
            print("🎉 All tests passed! Agent is working great!")
        else:
            # Analyze common issues
            all_issues = []
            for result in self.results:
                all_issues.extend(result["issues"])
            
            # Count issue types
            issue_counts = {}
            for issue in all_issues:
                key = issue.split(':')[0]  # Get the main issue type
                issue_counts[key] = issue_counts.get(key, 0) + 1
            
            print("Common issues to fix:")
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {issue} ({count} times)")
            
            if pass_rate < 70:
                print(f"\n⚠️  Pass rate is low ({pass_rate:.1f}%). Consider:")
                print("  • Checking agent configuration")
                print("  • Updating response templates")
                print("  • Reviewing formatting logic")
        
        print("\n" + "=" * 60)

async def main():
    """Main entry point"""
    print("🔧 Initializing Automated Test Suite...")
    
    test_suite = AgentTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Test suite interrupted!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)