"""
Quick Test Script for Voice Agent Framework Demo
Run this to quickly test all functionality
"""

import requests
import json
import time
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

BASE_URL = "http://localhost:5000"

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"{Fore.CYAN}{Style.BRIGHT}{text}")
    print("="*60 + "\n")

def print_success(text):
    """Print success message"""
    print(f"{Fore.GREEN}✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"{Fore.RED}❌ {text}")

def print_info(text):
    """Print info message"""
    print(f"{Fore.YELLOW}ℹ️  {text}")

def test_health_check():
    """Test if server is running"""
    print_header("Test 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print_success("Server is running!")
            print_info(f"Version: {response.json().get('version', 'N/A')}")
            return True
        else:
            print_error("Server returned non-200 status")
            return False
    except Exception as e:
        print_error(f"Could not connect to server: {e}")
        print_info("Make sure to run 'python main.py' first!")
        return False

def test_simple_chat():
    """Test basic chat functionality"""
    print_header("Test 2: Simple Chat Conversation")
    
    test_messages = [
        "Hello, I need help",
        "I want to book an appointment",
        "I have a headache, what medicine should I take?"
    ]
    
    for msg in test_messages:
        print(f"\n{Fore.BLUE}👤 User: {msg}")
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={"text": msg},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"{Fore.GREEN}🤖 Agent: {data['response']}")
                print(f"{Fore.MAGENTA}   Intent: {data['intent']} (confidence: {data['confidence']:.2%})")
                time.sleep(1)
            else:
                print_error(f"Chat failed: {response.status_code}")
        except Exception as e:
            print_error(f"Error: {e}")
    
    print_success("Chat test completed!")

def test_persona_frustrated():
    """Test frustrated user persona"""
    print_header("Test 3: Frustrated Customer Persona")
    
    test_prompt = "I've been waiting FOREVER! I need to see a doctor NOW! This is ridiculous!"
    
    print(f"{Fore.BLUE}👤 Frustrated User: {test_prompt}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/test-single",
            json={
                "persona_type": "frustrated",
                "test_prompt": test_prompt
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n{Fore.GREEN}🤖 Agent Response: {data['agent_response']}")
            print(f"\n{Fore.CYAN}📊 Test Scores:")
            
            for metric, score in data['scores'].items():
                bar = "█" * int(score * 20)
                print(f"   {metric:25s}: {bar} {score:.2%}")
            
            overall = data['overall_score']
            status = "PASSED ✅" if data['passed'] else "FAILED ❌"
            print(f"\n{Fore.YELLOW}   Overall Score: {overall:.2%} - {status}")
            
        else:
            print_error(f"Test failed: {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")

def test_persona_elderly():
    """Test elderly user persona"""
    print_header("Test 4: Elderly/Slow Speaker Persona")
    
    test_prompt = "Hello... I need... um... I need to book... an appointment... please"
    
    print(f"{Fore.BLUE}👤 Elderly User: {test_prompt}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/test-single",
            json={
                "persona_type": "elderly",
                "test_prompt": test_prompt
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n{Fore.GREEN}🤖 Agent Response: {data['agent_response']}")
            print(f"\n{Fore.CYAN}📊 Test Scores:")
            
            for metric, score in data['scores'].items():
                bar = "█" * int(score * 20)
                print(f"   {metric:25s}: {bar} {score:.2%}")
            
            overall = data['overall_score']
            status = "PASSED ✅" if data['passed'] else "FAILED ❌"
            print(f"\n{Fore.YELLOW}   Overall Score: {overall:.2%} - {status}")
            
        else:
            print_error(f"Test failed: {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")

def test_full_suite():
    """Test full test suite"""
    print_header("Test 5: Full Test Suite (All Personas)")
    
    print_info("Running comprehensive test suite... This may take a minute.")
    print_info("Testing: frustrated, non_native, fast_speaker, elderly, vague personas")
    
    try:
        response = requests.post(
            f"{BASE_URL}/test-suite",
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n{Fore.CYAN}📊 Test Suite Results:")
            print(f"   Total Tests: {data['total_tests']}")
            print(f"   Passed: {data['passed']}")
            print(f"   Failed: {data['total_tests'] - data['passed']}")
            print(f"   Pass Rate: {data['passed']/data['total_tests']*100:.1f}%")
            print(f"   Average Score: {data['average_score']:.2%}")
            
            if data['average_score'] >= 0.80:
                print_success("Test suite PASSED! Voice agent is performing well! 🎉")
            else:
                print_error("Test suite needs improvement. Review individual test results.")
            
        else:
            print_error(f"Test suite failed: {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")

def view_results():
    """View stored test results"""
    print_header("Test 6: View Stored Results from DynamoDB")
    
    try:
        response = requests.get(f"{BASE_URL}/results", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            count = data['count']
            
            print(f"{Fore.CYAN}Found {count} test results in database")
            
            if count > 0:
                print(f"\n{Fore.YELLOW}Recent Test Results:")
                for i, result in enumerate(data['results'][:5], 1):
                    status = "✅" if result.get('passed') else "❌"
                    print(f"\n{i}. Test ID: {result['test_id']}")
                    print(f"   Persona: {result.get('persona_type', 'N/A')}")
                    print(f"   Score: {result.get('overall_score', 0):.2%} {status}")
                    print(f"   Time: {result.get('timestamp', 'N/A')}")
            else:
                print_info("No results yet. Run some tests first!")
                
        else:
            print_error(f"Could not retrieve results: {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")

def main():
    """Run all tests"""
    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   🎤 AI VOICE AGENT TESTING FRAMEWORK - DEMO SUITE      ║")
    print("║                  KeyReply Project                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Style.RESET_ALL)
    
    # Run tests
    if not test_health_check():
        print_error("\nServer is not running. Please start it with: python main.py")
        return
    
    time.sleep(1)
    test_simple_chat()
    
    time.sleep(2)
    test_persona_frustrated()
    
    time.sleep(2)
    test_persona_elderly()
    
    time.sleep(2)
    test_full_suite()
    
    time.sleep(2)
    view_results()
    
    # Final summary
    print_header("Demo Complete! 🎉")
    print(f"{Fore.GREEN}All tests completed successfully!")
    print(f"\n{Fore.CYAN}Next Steps:")
    print("1. Check the test results in DynamoDB")
    print("2. Review the generated audio files (response_*.mp3)")
    print("3. Access the dashboard at http://localhost:5000/")
    print("4. Export results for your report")
    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Demo interrupted. Goodbye!")
    except Exception as e:
        print_error(f"Unexpected error: {e}")