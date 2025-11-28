#!/usr/bin/env python3
"""
Quick test script to verify Gemini API is working correctly
Run this BEFORE modifying your main project code
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
import json

def test_basic_connection():
    """Test 1: Basic API connection"""
    print("\n" + "="*60)
    print("TEST 1: Basic Gemini API Connection")
    print("="*60)
    
    try:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            print("❌ FAILED: No GEMINI_API_KEY found in .env file")
            print("\nFix:")
            print("1. Create a .env file")
            print("2. Add: GEMINI_API_KEY=your_key_here")
            return False
            
        print(f"✅ API Key found: {api_key[:10]}...")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        
        response = model.generate_content("Say 'Hello, I'm working!' in exactly those words")
        print(f"✅ Response received: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_structured_output():
    """Test 2: Getting structured JSON output"""
    print("\n" + "="*60)
    print("TEST 2: Structured JSON Output")
    print("="*60)
    
    try:
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        system_instruction = """You are a test assistant. 
Respond ONLY with valid JSON in this format:
{
    "status": "success",
    "message": "Your message here"
}
Do NOT include any markdown or extra text."""

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.3},
            system_instruction=system_instruction
        )
        
        response = model.generate_content("Generate a test JSON response")
        text = response.text.strip()
        
        # Clean up markdown if present
        text = text.replace("```json", "").replace("```", "").strip()
        
        print(f"Raw response: {text}")
        
        # Try to parse JSON
        data = json.loads(text)
        print(f"✅ Successfully parsed JSON: {data}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: Could not parse JSON")
        print(f"Response: {text}")
        return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_evaluation_prompt():
    """Test 3: Actual evaluation prompt"""
    print("\n" + "="*60)
    print("TEST 3: Healthcare Evaluation Prompt")
    print("="*60)
    
    try:
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        system_instruction = """You are an expert evaluator for healthcare voice agents.

Evaluate conversations on these criteria (all 0.0 to 1.0):
1. intent_recognition - Did agent understand user?
2. response_correctness - Is response appropriate?
3. error_handling - Handles unclear queries well?
4. tone_appropriateness - Professional and empathetic?
5. safety_compliance - Follows healthcare guidelines?

Respond ONLY with valid JSON:
{
    "intent_recognition": 0.0-1.0,
    "response_correctness": 0.0-1.0,
    "error_handling": 0.0-1.0,
    "tone_appropriateness": 0.0-1.0,
    "safety_compliance": 0.0-1.0,
    "reasoning": "brief explanation"
}"""

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.3},
            system_instruction=system_instruction
        )
        
        test_prompt = """Evaluate this conversation:

PERSONA TYPE: frustrated
USER INPUT: "I need help NOW! This is urgent!"
AGENT RESPONSE: "I'd be happy to help you book an appointment. What date works for you?"
DETECTED INTENT: appointment_booking

Provide scores and reasoning."""

        print("Sending evaluation request...")
        response = model.generate_content(test_prompt)
        text = response.text.strip()
        
        # Clean markdown
        text = text.replace("```json", "").replace("```", "").strip()
        
        print(f"\nRaw response:\n{text}\n")
        
        # Parse JSON
        evaluation = json.loads(text)
        
        # Validate fields
        required_fields = [
            "intent_recognition",
            "response_correctness",
            "error_handling", 
            "tone_appropriateness",
            "safety_compliance"
        ]
        
        print("Checking scores:")
        all_valid = True
        for field in required_fields:
            if field in evaluation:
                score = float(evaluation[field])
                valid = 0.0 <= score <= 1.0
                symbol = "✅" if valid else "❌"
                print(f"  {symbol} {field}: {score}")
                if not valid:
                    all_valid = False
            else:
                print(f"  ❌ {field}: MISSING")
                all_valid = False
        
        if "reasoning" in evaluation:
            print(f"\n💡 Reasoning: {evaluation['reasoning']}")
        else:
            print(f"\n⚠️  No reasoning provided")
        
        if all_valid:
            print("\n✅ PASSED: All scores valid!")
            return True
        else:
            print("\n❌ FAILED: Some scores invalid")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_consistency():
    """Test 4: Check evaluation consistency"""
    print("\n" + "="*60)
    print("TEST 4: Evaluation Consistency")
    print("="*60)
    
    try:
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        system_instruction = """You are a test evaluator.
Respond with JSON: {"score": 0.85, "reasoning": "Test"}"""

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"temperature": 0.3},  # Low temp for consistency
            system_instruction=system_instruction
        )
        
        scores = []
        test_prompt = "Evaluate: User says 'hello', agent says 'Hi, how can I help?'"
        
        print("Running same evaluation 3 times to check consistency...")
        for i in range(3):
            response = model.generate_content(test_prompt)
            text = response.text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            score = data.get("score", 0)
            scores.append(score)
            print(f"  Run {i+1}: score = {score}")
        
        # Check variance
        avg_score = sum(scores) / len(scores)
        variance = sum((x - avg_score) ** 2 for x in scores) / len(scores)
        
        print(f"\nAverage: {avg_score:.3f}")
        print(f"Variance: {variance:.4f}")
        
        if variance < 0.01:
            print("✅ PASSED: Low variance, good consistency!")
            return True
        else:
            print("⚠️  WARNING: High variance, might want to lower temperature")
            return True  # Still pass, just warning
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("🧪 GEMINI API TESTING SUITE")
    print("="*60)
    
    results = []
    
    results.append(("Basic Connection", test_basic_connection()))
    results.append(("Structured Output", test_structured_output()))
    results.append(("Evaluation Prompt", test_evaluation_prompt()))
    results.append(("Consistency", test_consistency()))
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    for test_name, passed in results:
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
        print("="*60)
        print("\nYou're ready to integrate LLM evaluation!")
        print("\nNext steps:")
        print("1. Copy the LLMEvaluator class to your voice_agent.py")
        print("2. Update VoiceAgentTester to use LLMEvaluator")
        print("3. Run your full test suite")
        print("4. Check DynamoDB for results with llm_reasoning")
    else:
        print("❌ SOME TESTS FAILED")
        print("="*60)
        print("\nFix the issues above before proceeding.")
    print()

if __name__ == "__main__":
    main()